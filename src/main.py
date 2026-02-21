"""
Interfaz principal para el flujo de boletas (placeholder: visita Google).
Base para luego integrar boleta de honorarios del SII.
"""
import sys
import os

def get_base_path():
    """Ruta base: desarrollo o ejecutable congelado."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_resource_path(*relative_path):
    """Ruta de recursos (desarrollo o ejecutable)."""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.dirname(sys.executable)
        return os.path.join(base, "src", *relative_path)
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *relative_path)

SCRIPT_DIR = get_base_path()
if getattr(sys, "frozen", False):
    PROJECT_ROOT = os.path.dirname(sys.executable)
    SRC_DIR = os.path.join(SCRIPT_DIR, "src")
else:
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
    SRC_DIR = SCRIPT_DIR

if getattr(sys, "frozen", False):
    sys.path.insert(0, SRC_DIR)
else:
    sys.path.insert(0, SCRIPT_DIR)

# Verificar core
CORE_DIR = get_resource_path("core")
if not os.path.exists(CORE_DIR):
    print(f"❌ ERROR: No existe la carpeta 'core' en {CORE_DIR}")
    sys.exit(1)

# Verificar boleta_automator
AUTOMATOR_FILE = os.path.join(CORE_DIR, "boleta_automator.py")
if not os.path.exists(AUTOMATOR_FILE):
    print(f"❌ ERROR: No existe boleta_automator.py en {CORE_DIR}")
    sys.exit(1)

# Dependencias
try:
    import selenium
    print(f"✅ Selenium {selenium.__version__}")
except ImportError:
    print("❌ Selenium no instalado. Ejecuta: pip install selenium webdriver-manager PyQt5")
    sys.exit(1)
try:
    import PyQt5
    print("✅ PyQt5 instalado")
except ImportError:
    print("❌ PyQt5 no instalado. Ejecuta: pip install PyQt5")
    sys.exit(1)

try:
    from core.boleta_automator import BoletaAutomator
    print("✅ BoletaAutomator importado")
except Exception as e:
    print(f"❌ Error importando BoletaAutomator: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QPushButton, QTextEdit, QCheckBox, QGroupBox,
        QMessageBox, QProgressBar, QSplitter,
    )
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont, QPalette, QColor
    print("✅ Componentes PyQt5 importados")
except ImportError as e:
    print(f"❌ Error PyQt5: {e}")
    sys.exit(1)


class BoletaGUI(QMainWindow):
    """Ventana principal: panel RUT/clave + logs + headless."""

    def __init__(self):
        super().__init__()
        self.automator = BoletaAutomator()
        self.worker = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("APP Boletas - Flujo SII (placeholder)")
        self.setGeometry(100, 100, 900, 600)
        self.set_custom_theme()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Título
        title = QLabel("APP Boletas")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #365ca3; margin: 10px 0;")
        main_layout.addWidget(title)

        # Cuerpo: splitter izquierda (credenciales) / derecha (logs)
        splitter = QSplitter(Qt.Horizontal)

        # Panel izquierdo: credenciales y opciones
        left = QWidget()
        left_layout = QVBoxLayout(left)

        cred = QGroupBox("🔑 Credenciales")
        cred_layout = QVBoxLayout()
        cred_layout.addWidget(QLabel("RUT:*"))
        self.rut_input = QLineEdit()
        self.rut_input.setPlaceholderText("Ej: 76.123.456-7")
        cred_layout.addWidget(self.rut_input)
        cred_layout.addWidget(QLabel("Clave:*"))
        self.clave_input = QLineEdit()
        self.clave_input.setEchoMode(QLineEdit.Password)
        self.clave_input.setPlaceholderText("Clave SII")
        cred_layout.addWidget(self.clave_input)
        cred.setLayout(cred_layout)
        left_layout.addWidget(cred)

        opts = QGroupBox("⚙️ Opciones")
        opts_layout = QVBoxLayout()
        self.headless_check = QCheckBox("Modo sin interfaz (Headless)")
        opts_layout.addWidget(self.headless_check)
        opts.setLayout(opts_layout)
        left_layout.addWidget(opts)

        self.start_btn = QPushButton("🚀 Iniciar proceso")
        self.start_btn.clicked.connect(self.iniciar_proceso)
        self.start_btn.setMinimumHeight(50)
        self.stop_btn = QPushButton("⏹️ Detener")
        self.stop_btn.clicked.connect(self.detener_proceso)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumHeight(40)
        left_layout.addWidget(self.start_btn)
        left_layout.addWidget(self.stop_btn)
        left_layout.addStretch()

        # Panel derecho: progreso y logs
        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.progress_bar = QProgressBar()
        right_layout.addWidget(self.progress_bar)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        right_layout.addWidget(self.log_text)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([280, 580])
        main_layout.addWidget(splitter)

        self.status_label = QLabel("Flujo: por ahora visita Google (placeholder para SII boletas).")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #365ca3; padding: 8px; border-top: 1px solid #a3b4cb;")
        main_layout.addWidget(self.status_label)

    def set_custom_theme(self):
        COLOR_FONDO = "#d4dce4"
        COLOR_LETRAS = "#365ca3"
        COLOR_DETALLES = "#a3b4cb"
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(COLOR_FONDO))
        palette.setColor(QPalette.WindowText, QColor(COLOR_LETRAS))
        palette.setColor(QPalette.Base, Qt.white)
        palette.setColor(QPalette.Text, QColor(COLOR_LETRAS))
        palette.setColor(QPalette.Button, QColor(COLOR_DETALLES))
        palette.setColor(QPalette.ButtonText, QColor(COLOR_LETRAS))
        palette.setColor(QPalette.Highlight, QColor(COLOR_LETRAS))
        palette.setColor(QPalette.HighlightedText, Qt.white)
        self.setPalette(palette)
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {COLOR_FONDO}; }}
            QGroupBox {{
                border: 2px solid {COLOR_DETALLES};
                border-radius: 8px;
                margin-top: 15px;
                font-weight: bold;
                color: {COLOR_LETRAS};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}
            QLineEdit {{
                padding: 8px;
                border: 1px solid {COLOR_DETALLES};
                border-radius: 4px;
                background-color: white;
                color: {COLOR_LETRAS};
            }}
            QPushButton {{
                background-color: {COLOR_DETALLES};
                color: {COLOR_LETRAS};
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #c0cedf; }}
            QPushButton:disabled {{ background-color: #ccc; color: #666; }}
            QTextEdit {{
                background-color: white;
                color: {COLOR_LETRAS};
                border: 1px solid {COLOR_DETALLES};
                border-radius: 4px;
            }}
            QProgressBar {{
                border: 1px solid {COLOR_DETALLES};
                border-radius: 5px;
                text-align: center;
                background-color: white;
            }}
            QProgressBar::chunk {{ background-color: #4CAF50; }}
            QCheckBox {{ color: {COLOR_LETRAS}; }}
        """)

    def _actualizar_log(self, mensaje):
        self.log_text.append(mensaje)
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)

    def iniciar_proceso(self):
        rut = self.rut_input.text().strip()
        clave = self.clave_input.text().strip()
        if not rut:
            QMessageBox.warning(self, "Advertencia", "Ingresa el RUT.")
            return
        if not clave:
            QMessageBox.warning(self, "Advertencia", "Ingresa la clave.")
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log_text.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("🚀 Iniciando proceso...")

        headless = self.headless_check.isChecked()
        self.worker = self.automator.iniciar_proceso(rut, clave, headless)

        if self.worker:
            self.worker.log_signal.connect(self._actualizar_log)
            self.worker.progress_signal.connect(self.progress_bar.setValue)
            self.worker.finished_signal.connect(self.proceso_finalizado)
            self.worker.start()
        else:
            QMessageBox.warning(self, "Advertencia", "Ya hay un proceso en ejecución.")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def detener_proceso(self):
        if self.worker and self.worker.isRunning():
            if self.automator.detener_proceso():
                self._actualizar_log("🛑 Proceso detenido por el usuario.")
                self.status_label.setText("⏹️ Proceso detenido.")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def proceso_finalizado(self, exito, mensaje):
        if exito:
            self._actualizar_log(f"✅ {mensaje}")
            self.status_label.setText("🎉 Proceso completado.")
        else:
            self._actualizar_log(f"❌ {mensaje}")
            self.status_label.setText("❌ Proceso falló.")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Confirmar salida",
                "Hay un proceso en ejecución. ¿Salir de todas formas?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.detener_proceso()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    app = None
    try:
        from PyQt5.QtWidgets import QApplication as QtApp
        app = QtApp.instance()
        if app is None:
            app = QtApp(sys.argv)
        app.setStyle("Fusion")
        window = BoletaGUI()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        error_msg = f"Error al iniciar:\n{str(e)}\n\n"
        import traceback
        error_msg += traceback.format_exc()
        try:
            from PyQt5.QtWidgets import QApplication as QtApp, QMessageBox
            err_app = QtApp.instance() or QtApp(sys.argv)
            QMessageBox.critical(None, "Error", error_msg)
        except Exception:
            log_path = os.path.join(PROJECT_ROOT, "error_log.txt")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(error_msg)
            print(f"Error guardado en: {log_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
