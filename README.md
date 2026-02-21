# APP Boletas

Aplicación base para el flujo de **boletas electrónicas** (por ahora con visita a Google como placeholder). Pensada para luego integrar la página de boleta de honorarios del SII.

## Requisitos

- **Python 3.8+**
- **Google Chrome** (última versión estable)
- Windows (probado en 10/11)

## Estructura del proyecto

```
APPBOLETAS/
├── src/
│   ├── main.py              # Punto de entrada (GUI PyQt5)
│   └── core/
│       ├── __init__.py
│       └── boleta_automator.py   # Worker Selenium + flujo (por ahora visita Google)
├── requirements.txt
└── README.md
```

## Instalación

1. Clonar o abrir el proyecto y crear entorno virtual (recomendado):

   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```

2. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

3. Ejecutar desde la raíz del proyecto:

   ```bash
   python src/main.py
   ```

## Uso

1. **RUT** y **Clave**: datos para el flujo (por ahora no se usan en la visita a Google; se usarán cuando se integre el SII).
2. **Modo Headless**: activar para ejecutar Chrome sin ventana visible.
3. **Iniciar proceso**: abre Chrome, visita Google (placeholder) y al terminar cierra el navegador. Los pasos se muestran en el panel de logs.
4. **Detener**: detiene el proceso y cierra el navegador.

El panel derecho muestra en tiempo real los logs del flujo (inicio, navegación, errores, cierre).

## Próximos pasos (boletas SII)

- Sustituir la visita a Google por la página de boleta de honorarios del SII.
- Implementar login con RUT/clave en el SII.
- Añadir los pasos específicos para generación/aceptación de boletas electrónicas.

## Referencia

Estructura y estilo inspirados en [AutomatizadorFacturas](https://github.com/Pauaua/AutomatizadorFacturas) (PyQt5, Selenium, Worker en QThread, tema y disposición de paneles).
