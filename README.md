# Automatizador de Boletas Electrónicas

Aplicación de escritorio para emitir **boletas de honorarios electrónicas** en el SII (Servicio de Impuestos Internos de Chile), de forma individual o masiva desde un archivo Excel.

Automatiza el flujo completo: login → hub boleta honorarios → emisor → por contribuyente → ValidaTimbrajeContrib → PresentaDatosBoleta → ConfirmaTimbrajeContrib → cierre de sesión.

---

## Características

- **Modo Individual** — ingreso manual de RUT/clave, datos del destinatario y hasta 4 prestaciones.
- **Modo Masivo** — carga un Excel con múltiples filas y procesa cada boleta de forma secuencial.
- **Vista adaptable** — selector PC / Tablet / Móvil que redimensiona la interfaz.
- **Modo Headless** — ejecuta Chrome sin ventana visible (recomendado para modo masivo).
- **Log en tiempo real** — cada paso del flujo se muestra en el panel de logs.
- **Detener proceso** — interrumpe la automatización en cualquier momento.

---

## Requisitos

- Python 3.10+
- Google Chrome (última versión estable)
- Windows 10 / 11

---

## Estructura del proyecto

```
APPBOLETAS/
├── src/
│   ├── main.py                   # GUI principal (PyQt5)
│   ├── assets/
│   │   ├── logo.png
│   │   └── icon.ico
│   └── core/
│       ├── __init__.py
│       └── boleta_automator.py   # Worker Selenium + flujo SII
├── ModeloBoletasAMasiva.xlsx     # Plantilla Excel para modo masivo
├── INSTRUCCIONES.txt             # Manual de uso
├── installer.iss                 # Script InnoSetup (generación de instalador)
├── build.spec                    # Spec PyInstaller
├── requirements.txt
└── README.md
```

---

## Instalación para desarrollo

1. Crear entorno virtual (recomendado):

   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

2. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

3. Ejecutar:

   ```bash
   python src/main.py
   ```

ChromeDriver se descarga automáticamente vía `webdriver-manager`.

---

## Distribución (instalador)

1. Generar el ejecutable:

   ```bash
   pyinstaller build.spec
   ```

   Resultado: `dist/Automatizador de Boletas.exe`

2. Compilar el instalador con **InnoSetup 6**:

   ```
   Abrir installer.iss → Compilar
   ```

   Resultado: `installer_output/Instalador_AutomatizadorBoletas.exe`

El instalador incluye el `.exe`, `INSTRUCCIONES.txt` y `ModeloBoletasAMasiva.xlsx`.

---

## Formato del Excel (modo masivo)

El archivo debe contener las siguientes columnas (los nombres son flexibles, se detectan automáticamente):

| Columna | Alternativas aceptadas |
|---|---|
| RUT | RUT_EMISOR, RUT_EMPRESA |
| CLAVE | CLAVE_SII, PASSWORD |
| RUT_DEST | RUT-DEST, RUT_DESTINATARIO |
| RUT_CV | DV_DEST, DV |
| NOMBRE_DEST | NOMBRE-DEST, NOMBRE, RAZON_SOCIAL |
| DOMICILIO_DEST | DOMICILIO-DEST, DOMICILIO |
| REGION | REGIÓN, COD_REGION |
| COMUNA | COD_COMUNA |
| PRESTACION | PRESTACION_1, GLOSA_1 |
| VALOR | VALOR_1, MONTO_1 |

Se soportan hasta 4 prestaciones por fila (PRESTACION_1 … PRESTACION_4).

Usar `ModeloBoletasAMasiva.xlsx` como base.

---

## Stack

| Tecnología | Uso |
|---|---|
| PyQt5 | Interfaz gráfica |
| Selenium + webdriver-manager | Automatización Chrome / SII |
| pandas + openpyxl | Lectura de Excel |
| PyInstaller | Empaquetado en .exe |
| InnoSetup 6 | Generación de instalador Windows |



## Extras

Incluye modelo plantilla excel para procesamiento masivo, además de documento con instrucciones de instalación. 


## Licencia

Desarrolladora única. Todos los derechos reservados. 