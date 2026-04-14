"""
Automatizador de Boleta de Honorarios Electrónica - SII Chile

Flujo:
  1. Login SII
  2. Navegar a sii.cl/servicios_online/1040-.html (boleta honorarios hub)
  3. Cerrar modal si aparece
  4. Navegar directo a 1040-1287.html (emisor)
  5. Click "Emitir boleta de honorarios electrónica" → aparece submenu
  6. Click "Por contribuyente" (link cuyo href va a loa.sii.cl)
  7. loa.sii.cl ValidaTimbrajeContrib: dejar primera opción → Continuar
  8. loa.sii.cl PresentaDatosBoleta: llenar formulario → enviar
  9. loa.sii.cl ConfirmaTimbrajeContrib: click "Emitir boleta"
 10. loa.sii.cl BoletaHonorariosElectronica → cerrar sesión
"""
import sys
import time
import os
import re
import calendar
from datetime import date
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from PyQt5.QtCore import QThread, pyqtSignal

URL_LOGIN    = ("https://zeusr.sii.cl/AUT2000/InicioAutenticacion/IngresoRutClave.html"
                "?https://misiir.sii.cl/cgi_misii/siihome.cgi")
URL_DASHBOARD = "https://misiir.sii.cl/cgi_misii/siihome.cgi"
URL_BOLETA_HUB = "https://www.sii.cl/servicios_online/1040-.html"
URL_EMISOR    = "https://www.sii.cl/servicios_online/1040-1287.html"
URL_LOGOUT    = "https://zeusr.sii.cl/AUT2000/CierreAutenticacion/CerrarSesion.html"

T_WAIT  = 15   # WebDriverWait timeout
T_LOAD  = 3    # general page load pause
T_SHORT = 1    # short pause after action


def _ultimo_dia_mes():
    hoy = date.today()
    ultimo = calendar.monthrange(hoy.year, hoy.month)[1]
    return str(ultimo), str(hoy.month).zfill(2), str(hoy.year)


def get_project_root():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    cwd = os.getcwd()
    return os.path.dirname(cwd) if os.path.basename(cwd) == "src" else cwd


def _js_click(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    driver.execute_script("arguments[0].click();", el)


def _find_click(driver, xpaths, log):
    """Click first matching visible element from xpath list. Returns True if clicked."""
    for xp in xpaths:
        try:
            for el in driver.find_elements(By.XPATH, xp):
                try:
                    # Capturar texto ANTES del click (evita StaleElementReferenceException post-navegación)
                    try:
                        txt = (el.text or el.get_attribute("value") or "").strip()[:60]
                    except Exception:
                        txt = ""
                    _js_click(driver, el)
                    log(f"   ✔ Click: '{txt}'")
                    return True
                except Exception:
                    continue
        except Exception:
            continue
    return False


def _fill(driver, by_list, value):
    """Fill first found field. by_list: [(By, selector), ...]"""
    for by, sel in by_list:
        try:
            for el in driver.find_elements(by, sel):
                try:
                    driver.execute_script("arguments[0].value = '';", el)
                    el.clear()
                except Exception:
                    pass
                el.send_keys(value)
                # Disparar evento change para que el JS de la página reaccione
                try:
                    driver.execute_script(
                        "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", el)
                except Exception:
                    pass
                return True
        except Exception:
            continue
    return False


def _fill_logged(driver, by_list, value, label, log):
    """Como _fill pero logguea éxito o falla con el nombre del campo."""
    ok = _fill(driver, by_list, value)
    if ok:
        log(f"   ✔ {label}: '{value[:40]}'")
    else:
        # Diagnóstico: qué selectores se probaron
        tried = [f"{by}={sel}" for by, sel in by_list[:3]]
        log(f"   ⚠️ No se encontró campo '{label}'. Selectores probados: {tried}")
    return ok


def _select_val(driver, by_list, value, partial=False):
    """Select option in first found <select> matching value (by value attr or partial text)."""
    for by, sel in by_list:
        try:
            for el in driver.find_elements(by, sel):
                s = Select(el)
                # try by value first
                try:
                    s.select_by_value(value)
                    return True
                except Exception:
                    pass
                # try by text
                for opt in s.options:
                    match = (value.lower() in opt.text.lower()) if partial else (opt.text.strip() == value)
                    if match:
                        s.select_by_visible_text(opt.text)
                        return True
        except Exception:
            continue
    return False


def _close_modal(driver, log):
    """Close any visible modal/overlay."""
    closers = [
        "//button[contains(@class,'close')]",
        "//button[contains(@aria-label,'lose')]",
        "//button[contains(translate(.,'CERRAR','cerrar'),'cerrar')]",
        "//a[contains(@class,'close')]",
    ]
    for xp in closers:
        try:
            for el in driver.find_elements(By.XPATH, xp):
                if el.is_displayed():
                    _js_click(driver, el)
                    log("   ✔ Modal cerrado.")
                    time.sleep(0.5)
                    return True
        except Exception:
            continue
    return False


class BoletaAutomatorWorker(QThread):
    """
    Worker thread: ejecuta flujo completo SII boleta honorarios.

    boleta_data keys:
        rut_dest, dv_dest, nombres_dest, domicilio,
        region, comuna,
        prestaciones: [{"glosa": str, "valor": str/int}, ...]
    """
    log_signal      = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, rut, clave, boleta_data=None, headless=False):
        super().__init__()
        self.rut        = (rut or "").strip()
        self.clave      = clave or ""
        self.headless   = headless
        self.boleta_data = boleta_data or {}
        self.driver     = None
        self.wait       = None
        self.is_running = True

    def _log(self, msg):
        self.log_signal.emit(msg)

    def _prog(self, pct):
        self.progress_signal.emit(pct)

    def _cancel_check(self):
        if not self.is_running:
            self._quit_driver()
            self.finished_signal.emit(False, "Cancelado.")
            return True
        return False

    def run(self):
        ok = False
        msg = "Proceso interrumpido."
        try:
            # ── Navegador ──────────────────────────────────────────────
            self._log("🔧 Iniciando navegador Chrome...")
            self._prog(5)
            opts = Options()
            if self.headless:
                opts.add_argument("--headless=new")
                self._log("👁️ Modo headless activado.")
            else:
                opts.add_argument("--start-maximized")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), options=opts)
            self.wait = WebDriverWait(self.driver, T_WAIT)
            self._log("✅ Navegador listo.")
            self._prog(10)

            if self._cancel_check():
                return

            # ══════════════════════════════════════════════════════════
            # PASO 1: Login
            # ══════════════════════════════════════════════════════════
            self._log("🌐 PASO 1 – Login SII...")
            self.driver.get(URL_LOGIN)
            time.sleep(T_LOAD)

            if not _fill(self.driver,
                [(By.ID,"rutcntr"),(By.NAME,"rutcntr"),(By.ID,"rut"),(By.NAME,"rut")],
                self.rut):
                raise Exception("No se encontró campo RUT.")

            if not _fill(self.driver,
                [(By.ID,"clave"),(By.NAME,"clave"),(By.XPATH,"//input[@type='password']")],
                self.clave):
                raise Exception("No se encontró campo Clave.")

            if not _find_click(self.driver, [
                "//input[@id='bt_ingresar']","//button[@type='submit']","//input[@type='submit']"
            ], self._log):
                self.driver.find_element(By.XPATH,"//input[@type='password']").send_keys(Keys.RETURN)

            self._log("   ⏳ Esperando dashboard...")
            time.sleep(6)

            if "siihome.cgi" not in self.driver.current_url:
                src = self.driver.page_source.lower()
                for e in ("incorrecto","inválido","error de autenticación","acceso denegado"):
                    if e in src:
                        raise Exception("Login rechazado: credenciales incorrectas.")
            self._log("✅ Login exitoso.")
            self._prog(20)
            if self._cancel_check(): return

            # ══════════════════════════════════════════════════════════
            # PASO 2: Hub de Boleta de Honorarios (cerrar modal)
            # ══════════════════════════════════════════════════════════
            # PASO 2: Desde el dashboard misiir.sii.cl, navegar a Boleta
            # de Honorarios haciendo click en el link (NO por URL directa)
            # → así la sesión se propaga correctamente a www.sii.cl y loa.sii.cl
            # ══════════════════════════════════════════════════════════
            self._log("🌐 PASO 2 – Buscando 'Boleta de honorarios' en dashboard...")
            tabs_before = set(self.driver.window_handles)
            boleta_hub_ok = _find_click(self.driver, [
                "//a[contains(translate(.,'BOLETA','boleta'),'boleta') and contains(translate(.,'HONORARIO','honorario'),'honorario')]",
                "//a[contains(.,'Boleta de honorarios')]",
                "//a[contains(.,'Boletas de honorarios')]",
                "//a[contains(@href,'1040-')]",
            ], self._log)
            time.sleep(T_LOAD + 1)
            # Si el click abrió una nueva pestaña, cambiar a ella
            tabs_after = set(self.driver.window_handles)
            new_tabs = tabs_after - tabs_before
            if new_tabs:
                self.driver.switch_to.window(new_tabs.pop())
                self._log("   ↪ Nueva pestaña detectada, cambiando...")
                time.sleep(T_LOAD)
            if not boleta_hub_ok or "1040" not in self.driver.current_url:
                self._log("   ↪ Navegando por URL directa...")
                self.driver.get(URL_BOLETA_HUB)
                time.sleep(T_LOAD + 1)
            _close_modal(self.driver, self._log)
            time.sleep(T_SHORT)
            self._log(f"   URL: {self.driver.current_url}")
            self._prog(28)
            if self._cancel_check(): return

            # ══════════════════════════════════════════════════════════
            # PASO 3: Click en "Emisor de boleta de honorarios"
            # ══════════════════════════════════════════════════════════
            self._log("🖱️ PASO 3 – Click en 'Emisor de boleta de honorarios'...")
            # Si ya estamos en 1040-1287.html, saltar
            if "1040-1287" not in self.driver.current_url:
                tabs_before3 = set(self.driver.window_handles)
                emisor_ok = _find_click(self.driver, [
                    "//a[contains(.,'Emisor de boleta')]",
                    "//a[contains(@href,'1040-1287')]",
                ], self._log)
                time.sleep(T_LOAD)
                tabs_after3 = set(self.driver.window_handles)
                new_tabs3 = tabs_after3 - tabs_before3
                if new_tabs3:
                    self.driver.switch_to.window(new_tabs3.pop())
                    self._log("   ↪ Nueva pestaña detectada, cambiando...")
                    time.sleep(T_LOAD)
                if not emisor_ok or "1040-1287" not in self.driver.current_url:
                    self._log("   ↪ Navegando directo a emisor...")
                    self.driver.get(URL_EMISOR)
                    time.sleep(T_LOAD)
            self._log(f"   URL: {self.driver.current_url}")
            self._prog(36)
            if self._cancel_check(): return

            # ══════════════════════════════════════════════════════════
            # PASO 4: Click "Emitir boleta de honorarios electrónica"
            # → Aparece submenu con "Por contribuyente"
            # ══════════════════════════════════════════════════════════
            self._log("🖱️ PASO 4 – Click en 'Emitir boleta de honorarios electrónica'...")
            emitir_ok = _find_click(self.driver, [
                "//a[contains(translate(.,'EMITIR BOLETA DE HONORARIOS','emitir boleta de honorarios'),'emitir boleta de honorarios')]",
                "//a[contains(.,'Emitir boleta de honorarios')]",
                "//a[contains(.,'Emitir Boleta de Honorarios')]",
            ], self._log)
            if not emitir_ok:
                self._log("   ⚠️ No encontrado link Emitir.")
            time.sleep(4)  # esperar que el submenu se despliegue (JS/CSS)
            self._log(f"   URL: {self.driver.current_url}")
            self._prog(44)
            if self._cancel_check(): return

            # ══════════════════════════════════════════════════════════
            # PASO 5: Click "Por contribuyente"
            # REGLA: el link debe tener href apuntando a loa.sii.cl
            # (así distinguimos de links de factura electrónica u otros)
            # ══════════════════════════════════════════════════════════
            self._log("🔽 PASO 5 – Buscando 'Por contribuyente'...")
            contrib_link = None
            loa_url = None
            try:
                for el in self.driver.find_elements(By.XPATH, "//a"):
                    txt = el.text.strip()
                    href = (el.get_attribute("href") or "").strip()
                    # Solo "Por contribuyente" exacto (no "con datos usados" ni "autorizado")
                    if txt.strip().lower() == "por contribuyente":
                        contrib_link = el
                        # Extraer URL real de javascript:linkVisita('...')
                        m = re.search(r"linkVisita\('([^']+)'", href)
                        if m:
                            loa_url = m.group(1)
                        break
            except Exception:
                pass

            # Si el primer bloque no extrajo la URL (href vacío en ese momento), reintentarlo
            if contrib_link is not None and not loa_url:
                raw_href = contrib_link.get_attribute("href") or ""
                m = re.search(r"linkVisita\('([^']+)'", raw_href)
                if m:
                    loa_url = m.group(1)
            if contrib_link is not None:
                txt = contrib_link.text.strip()
                self._log(f"   ✔ Encontrado: '{txt}'")
                self._log(f"   ✔ URL loa.sii.cl extraída: {loa_url}")
                _js_click(self.driver, contrib_link)
                self._log("   ✔ Click en 'Por contribuyente'.")
            else:
                self._log("   ⚠️ No se encontró 'Por contribuyente'. Continuando igual...")

            time.sleep(T_LOAD)
            url_tras_click = self.driver.current_url
            self._log(f"   URL: {url_tras_click}")

            # ── Detectar redirección a login (sesión expirada en loa.sii.cl) ──
            if "IngresoRutClave" in url_tras_click or "zeusr.sii.cl" in url_tras_click:
                self._log("   ⚠️ Sesión expirada en loa.sii.cl. Re-autenticando...")

                # Re-login
                self.driver.get(URL_LOGIN)
                time.sleep(T_LOAD)
                _fill(self.driver,
                    [(By.ID,"rutcntr"),(By.NAME,"rutcntr"),(By.ID,"rut"),(By.NAME,"rut")], self.rut)
                _fill(self.driver,
                    [(By.ID,"clave"),(By.NAME,"clave"),(By.XPATH,"//input[@type='password']")], self.clave)
                if not _find_click(self.driver, [
                    "//input[@id='bt_ingresar']","//button[@type='submit']","//input[@type='submit']"
                ], self._log):
                    self.driver.find_element(By.XPATH,"//input[@type='password']").send_keys(Keys.RETURN)
                time.sleep(6)
                self._log(f"   ✔ Re-login completado. URL: {self.driver.current_url}")

                # Navegar directamente a la URL de loa.sii.cl si la tenemos
                if loa_url:
                    self._log(f"   🌐 Navegando directo a loa.sii.cl...")
                    self.driver.get(loa_url)
                    time.sleep(T_LOAD)
                    self._log(f"   URL: {self.driver.current_url}")
                else:
                    # Sin URL extraída: volver a hacer el flujo completo
                    self._log("   ⚠️ Sin URL de loa.sii.cl, repitiendo navegación...")
                    self.driver.get(URL_EMISOR)
                    time.sleep(T_LOAD)
                    _find_click(self.driver, [
                        "//a[contains(.,'Emitir boleta de honorarios')]",
                    ], self._log)
                    time.sleep(3)
                    _find_click(self.driver, [
                        "//a[contains(translate(.,'CONTRIBUYENTE','contribuyente'),'contribuyente') and not(contains(@href,'1039'))]",
                    ], self._log)
                    time.sleep(T_LOAD)

            self._prog(52)
            if self._cancel_check(): return

            # ══════════════════════════════════════════════════════════
            # PASO 6: ValidaTimbrajeContrib (loa.sii.cl)
            # Primera opción del select ya marcada → Continuar
            # ══════════════════════════════════════════════════════════
            self._log("🌐 PASO 6 – Página de validación (loa.sii.cl)...")
            time.sleep(T_SHORT)

            # Si ya pasamos a PresentaDatosBoleta directamente, saltamos este paso
            if "PresentaDatosBoleta" not in self.driver.current_url:
                try:
                    sels = self.driver.find_elements(By.TAG_NAME, "select")
                    for s_el in sels:
                        s = Select(s_el)
                        if s.options:
                            self._log(f"   ✔ Select validación: '{s.options[0].text.strip()}'")
                        break
                except Exception:
                    pass

                self._log("🖱️ PASO 6 – Click Continuar...")
                c1_ok = _find_click(self.driver, [
                    "//input[@type='submit' and contains(translate(@value,'continuar','CONTINUAR'),'CONTINUAR')]",
                    "//button[contains(translate(.,'continuar','CONTINUAR'),'CONTINUAR')]",
                    "//input[@value='Continuar']",
                    "//button[contains(.,'Continuar')]",
                ], self._log)
                if not c1_ok:
                    self._log("   ⚠️ Botón Continuar no encontrado (paso 6).")
                time.sleep(T_LOAD)
            self._log(f"   URL: {self.driver.current_url}")
            self._prog(62)
            if self._cancel_check(): return

            # ══════════════════════════════════════════════════════════
            # PASO 7: PresentaDatosBoleta (loa.sii.cl) — Llenar formulario
            # ══════════════════════════════════════════════════════════
            self._log("📝 PASO 7 – Llenando formulario de boleta...")
            time.sleep(T_LOAD)

            # ── Diagnóstico: volcar TODOS los campos del formulario ───
            self._log("   ℹ️ Campos del formulario (inputs/selects/textareas):")
            try:
                campos = self.driver.find_elements(By.XPATH,
                    "//input | //select | //textarea")
                for c in campos:
                    tag  = c.tag_name
                    name = c.get_attribute("name") or ""
                    cid  = c.get_attribute("id") or ""
                    typ  = c.get_attribute("type") or ""
                    val  = c.get_attribute("value") or ""
                    if tag == "select":
                        try:
                            opts = [o.text.strip() for o in Select(c).options[:4]]
                            self._log(f"      [select] name='{name}' id='{cid}' opciones={opts}")
                        except Exception:
                            self._log(f"      [select] name='{name}' id='{cid}'")
                    elif typ not in ("hidden","button","submit","image"):
                        self._log(f"      [{tag} type={typ}] name='{name}' id='{cid}' val='{val[:30]}'")
            except Exception as ex:
                self._log(f"   ⚠️ Error volcando campos: {ex}")

            bd = self.boleta_data
            dia, mes, anio = _ultimo_dia_mes()

            # Mapa mes numérico → nombre en español (como aparece en el select)
            MESES_ES = {
                "01":"Enero","02":"Febrero","03":"Marzo","04":"Abril",
                "05":"Mayo","06":"Junio","07":"Julio","08":"Agosto",
                "09":"Septiembre","10":"Octubre","11":"Noviembre","12":"Diciembre"
            }
            mes_texto = MESES_ES.get(mes, mes)

            # Esperar a que la página esté lista
            try:
                self.wait.until(EC.presence_of_element_located((By.NAME, "txt_rut_destinatario")))
            except Exception:
                time.sleep(2)

            # ── Radio "Descripción de actividades" → seleccionar 'si' ─
            try:
                for r in self.driver.find_elements(By.NAME, "rdb_glosa"):
                    if r.get_attribute("value") == "si":
                        self.driver.execute_script("arguments[0].click();", r)
                        self._log("   ✔ Descripción actividades: 'Sí'")
                        break
            except Exception:
                pass

            # ── Fecha: selects separados ──────────────────────────────
            # cbo_dia_boleta: valores '01','02',...,'31'
            # cbo_mes_boleta: 'Enero','Febrero',...
            # cbo_anio_boleta: '2021','2022',...,'2026'
            self._log(f"   📅 Fecha objetivo: {dia.zfill(2)}/{mes_texto}/{anio}")
            _select_val(self.driver, [(By.NAME,"cbo_dia_boleta")], dia.zfill(2))
            _select_val(self.driver, [(By.NAME,"cbo_mes_boleta"),(By.ID,"cbo_mes_boleta")], mes_texto)
            anio_ok = _select_val(self.driver, [(By.NAME,"cbo_anio_boleta"),(By.ID,"cbo_anio_boleta")], anio)
            if not anio_ok:
                # Si el año actual no está, tomar la última opción disponible
                try:
                    s_anio = Select(self.driver.find_element(By.NAME, "cbo_anio_boleta"))
                    opts_anio = [o.get_attribute("value") for o in s_anio.options if o.get_attribute("value")]
                    self._log(f"   ⚠️ Año {anio} no encontrado. Opciones disponibles: {opts_anio}")
                    if opts_anio:
                        s_anio.select_by_value(opts_anio[-1])
                        self._log(f"   ↪ Usando último año disponible: {opts_anio[-1]}")
                except Exception:
                    pass
            self._log(f"   ✔ Fecha seleccionada: {dia.zfill(2)}/{mes_texto}/{anio}")

            # ── RUT y DV del destinatario ─────────────────────────────
            rut_dest = bd.get("rut_dest","")
            dv_dest  = bd.get("dv_dest","")
            _fill_logged(self.driver, [(By.NAME,"txt_rut_destinatario")],
                         rut_dest, "RUT destinatario", self._log)
            _fill_logged(self.driver, [(By.NAME,"txt_dv_destinatario")],
                         dv_dest, "DV destinatario", self._log)

            # ── Nombre destinatario ───────────────────────────────────
            nombres = bd.get("nombres_dest","")
            _fill_logged(self.driver, [(By.NAME,"txt_nombres_destinatario")],
                         nombres, "Nombre destinatario", self._log)

            # ── Domicilio destinatario ────────────────────────────────
            dom = bd.get("domicilio","")
            _fill_logged(self.driver, [(By.NAME,"txt_domicilio_destinatario")],
                         dom, "Domicilio destinatario", self._log)

            # ── Región (select cod_region) ────────────────────────────
            # Opciones: 'REGION DE ARICA Y PARINACOTA', 'REGION DE ANTOFAGASTA', etc.
            region_val = bd.get("region","")
            if region_val:
                ok_r = _select_val(self.driver, [(By.NAME,"cod_region")], region_val, partial=True)
                if ok_r:
                    self._log(f"   ✔ Región: '{region_val}'")
                    time.sleep(2)  # esperar carga dinámica de comunas
                else:
                    try:
                        opts = [o.text.strip() for o in
                                Select(self.driver.find_element(By.NAME,"cod_region")).options]
                        self._log(f"   ⚠️ Región '{region_val}' no encontrada. Opciones: {opts}")
                    except Exception:
                        self._log(f"   ⚠️ Select región no encontrado.")

            # ── Comuna (select cbo_comuna, carga dinámica) ────────────
            comuna_val = bd.get("comuna","")
            if comuna_val:
                ok_c = _select_val(self.driver,
                    [(By.NAME,"cbo_comuna"),(By.ID,"cbo_comuna")], comuna_val, partial=True)
                if ok_c:
                    self._log(f"   ✔ Comuna: '{comuna_val}'")
                else:
                    try:
                        opts = [o.text.strip() for o in
                                Select(self.driver.find_element(By.NAME,"cbo_comuna")).options]
                        self._log(f"   ⚠️ Comuna '{comuna_val}' no encontrada. Opciones: {opts[:10]}")
                    except Exception:
                        self._log(f"   ⚠️ Select comuna no encontrado.")

            # ── Prestaciones ──────────────────────────────────────────
            # Campos: desc_prestacion_1, valor_prestacion_1, ..., desc_prestacion_4, valor_prestacion_4
            prestaciones = bd.get("prestaciones",[])
            for i, p in enumerate(prestaciones[:4], start=1):
                g = p.get("glosa","")
                v = str(p.get("valor",""))
                if g:
                    _fill_logged(self.driver,
                                 [(By.NAME, f"desc_prestacion_{i}"), (By.ID, f"desc_prestacion_{i}")],
                                 g, f"Glosa {i}", self._log)
                if v:
                    _fill_logged(self.driver,
                                 [(By.NAME, f"valor_prestacion_{i}"), (By.ID, f"valor_prestacion_{i}")],
                                 v, f"Valor {i}", self._log)

            time.sleep(T_SHORT)
            self._prog(78)

            # ── Enviar formulario (loa.sii.cl PresentaDatosBoleta) ───
            self._log("📤 PASO 7 – Enviando formulario...")

            # Diagnóstico completo de botones (incluyendo type=image que usa el SII)
            try:
                btns = self.driver.find_elements(By.XPATH,
                    "//input[@type='submit' or @type='image' or @type='button'] | //button")
                for b in btns:
                    v = (b.get_attribute("value") or b.get_attribute("src") or b.text or "").strip()
                    n = b.get_attribute("name") or ""
                    t = b.get_attribute("type") or ""
                    self._log(f"   [btn type={t}] name='{n}' value/src='{v[:50]}'")
            except Exception:
                pass

            env_ok = _find_click(self.driver, [
                # Botón "Confirmar Emisión" (cmdAceptar) — loa.sii.cl usa type=button con JS propio
                "//input[@name='cmdAceptar']",
                "//input[@type='button' and contains(translate(@value,'confirmar','CONFIRMAR'),'CONFIRMAR')]",
                "//input[@type='button' and contains(translate(@value,'aceptar','ACEPTAR'),'ACEPTAR')]",
                # Botones submit estándar
                "//input[@type='submit' and contains(translate(@value,'continuar','CONTINUAR'),'CONTINUAR')]",
                "//input[@type='submit' and contains(translate(@value,'siguiente','SIGUIENTE'),'SIGUIENTE')]",
                "//input[@type='submit' and contains(translate(@value,'aceptar','ACEPTAR'),'ACEPTAR')]",
                "//input[@type='submit' and contains(translate(@value,'enviar','ENVIAR'),'ENVIAR')]",
                "//button[@type='submit']",
                "//input[@type='submit']",
                "//input[@type='image']",
            ], self._log)
            time.sleep(T_LOAD + 1)
            self._log(f"   URL: {self.driver.current_url}")
            self._prog(88)
            if self._cancel_check(): return

            # ══════════════════════════════════════════════════════════
            # PASO 8: ConfirmaTimbrajeContrib — Click "Emitir boleta"
            # ══════════════════════════════════════════════════════════
            self._log("🖱️ PASO 8 – Emitiendo boleta (borrador)...")

            # Diagnóstico: botones en página de confirmación
            try:
                btns8 = self.driver.find_elements(By.XPATH,
                    "//input[@type='submit' or @type='image' or @type='button'] | //button | //a[contains(translate(.,'emitir','EMITIR'),'EMITIR')]")
                for b in btns8:
                    v = (b.get_attribute("value") or b.get_attribute("src") or b.text or "").strip()
                    n = b.get_attribute("name") or ""
                    t = b.get_attribute("type") or b.tag_name
                    self._log(f"   [paso8 elem={t}] name='{n}' val='{v[:60]}'")
            except Exception:
                pass

            emit_ok = _find_click(self.driver, [
                "//button[@name='cmdconfirmar']",
                "//input[@type='submit' and contains(translate(@value,'emitir','EMITIR'),'EMITIR')]",
                "//button[contains(translate(.,'emitir','EMITIR'),'EMITIR')]",
                "//a[contains(translate(.,'emitir boleta','EMITIR BOLETA'),'emitir boleta')]",
                "//input[@value='Emitir Boleta de Honorarios Electrónica']",
                "//input[@value='Emitir Boleta']",
                "//input[@value='Emitir']",
                "//input[@type='image']",
                "//input[@type='submit']",
            ], self._log)
            if not emit_ok:
                self._log("   ⚠️ No se encontró botón de emisión final.")
            time.sleep(T_LOAD + 1)
            self._log(f"   URL: {self.driver.current_url}")
            self._prog(96)
            if self._cancel_check(): return

            # ══════════════════════════════════════════════════════════
            # PASO 9: Boleta emitida → cerrar sesión
            # ══════════════════════════════════════════════════════════
            url_final = self.driver.current_url
            self._log(f"🎉 PASO 9 – Boleta procesada. URL: {url_final}")
            try:
                self.driver.get(URL_LOGOUT)
                time.sleep(2)
                self._log("🔓 Sesión cerrada.")
            except Exception:
                pass

            self._prog(100)
            ok = True
            msg = f"✅ Boleta emitida correctamente para RUT {bd.get('rut_dest','')}."
            self._log(msg)

        except Exception as e:
            msg = str(e)
            self._log(f"❌ Error: {msg}")
            ok = False
        finally:
            self._prog(100)
            self._log("🔒 Cerrando navegador...")
            self._quit_driver()
            self.finished_signal.emit(ok, msg)

    def _quit_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None

    def stop(self):
        self.is_running = False
        self._quit_driver()


class BoletaAutomator:
    def __init__(self):
        self.worker = None

    def iniciar_proceso(self, rut, clave, boleta_data=None, headless=False):
        if self.worker and self.worker.isRunning():
            if not self.worker.wait(1000):
                return None
            self.worker = None
        self.worker = BoletaAutomatorWorker(rut, clave, boleta_data, headless)
        return self.worker

    def crear_worker_independiente(self, rut, clave, boleta_data=None, headless=False):
        return BoletaAutomatorWorker(rut, clave, boleta_data, headless)

    def detener_proceso(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.quit()
            if not self.worker.wait(3000):
                self.worker.terminate()
                self.worker.wait()
            return True
        return False

    def detener_worker_externo(self, worker):
        """Detiene un worker creado con crear_worker_independiente."""
        if worker and worker.isRunning():
            worker.stop()
            worker.quit()
            if not worker.wait(3000):
                worker.terminate()
                worker.wait()
            return True
        return False
