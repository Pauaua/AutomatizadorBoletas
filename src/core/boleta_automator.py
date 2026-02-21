"""
Módulo para automatizar flujo de boletas (placeholder: visita Google).
Pensado para luego integrar la página de boleta de honorarios del SII.
"""
import sys
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from PyQt5.QtCore import QThread, pyqtSignal

# URL de prueba (luego se cambiará por la página de boletas SII)
PLACEHOLDER_URL = "https://www.google.com"


def get_project_root():
    """Directorio raíz del proyecto (logs, reportes)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    cwd = os.getcwd()
    if os.path.basename(cwd) == "src":
        return os.path.dirname(cwd)
    return cwd


class BoletaAutomatorWorker(QThread):
    """Worker que ejecuta el flujo en segundo plano (por ahora: abrir Chrome y visitar Google)."""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, rut, clave, headless=False):
        super().__init__()
        self.rut = rut
        self.clave = clave
        self.headless = headless
        self.driver = None
        self.is_running = True

    def _log(self, msg):
        self.log_signal.emit(msg)

    def run(self):
        try:
            self._log("🔧 Iniciando navegador Chrome...")
            self.progress_signal.emit(10)

            options = Options()
            if self.headless:
                options.add_argument("--headless=new")
                self._log("👁️ Modo headless activado (sin ventana visible).")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            if not self.is_running:
                self._cerrar_driver()
                self.finished_signal.emit(False, "Proceso cancelado.")
                return

            self._log("✅ Navegador iniciado correctamente.")
            self.progress_signal.emit(30)

            # Placeholder: visitar Google (luego será la página de boletas SII)
            self._log(f"🌐 Navegando a {PLACEHOLDER_URL} (placeholder para SII boletas)...")
            self.driver.get(PLACEHOLDER_URL)
            if not self.is_running:
                self._cerrar_driver()
                self.finished_signal.emit(False, "Proceso cancelado.")
                return

            time.sleep(2)
            self._log("✅ Página cargada correctamente.")
            self.progress_signal.emit(70)

            # Aquí irá la lógica de boletas: login SII, ir a boleta de honorarios, etc.
            self._log("📋 Flujo de boletas SII: pendiente de implementar (por ahora solo visita de prueba).")
            self.progress_signal.emit(90)

            self._cerrar_driver()
            self.progress_signal.emit(100)
            self._log("🏁 Proceso finalizado. Navegador cerrado.")
            self.finished_signal.emit(True, "Proceso completado correctamente.")

        except Exception as e:
            self._log(f"❌ Error en el flujo: {str(e)}")
            self._cerrar_driver()
            self.finished_signal.emit(False, str(e))

    def _cerrar_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def stop(self):
        """Detener el proceso y cerrar el navegador."""
        self.is_running = False
        self._cerrar_driver()


class BoletaAutomator:
    """Orquestador del flujo de boletas (un worker por ejecución)."""

    def __init__(self):
        self.worker = None

    def iniciar_proceso(self, rut, clave, headless=False):
        """Inicia el proceso en un worker. Retorna el worker para conectar señales."""
        if self.worker and self.worker.isRunning():
            if self.worker.wait(1000):
                self.worker = None
            else:
                return None
        self.worker = BoletaAutomatorWorker(rut, clave, headless)
        return self.worker

    def detener_proceso(self):
        """Detiene el worker en ejecución."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.quit()
            if not self.worker.wait(3000):
                self.worker.terminate()
                self.worker.wait()
            return True
        return False
