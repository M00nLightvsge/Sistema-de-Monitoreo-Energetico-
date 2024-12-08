from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QGraphicsOpacityEffect
from PyQt5.QtCore import QTimer
from datetime import datetime
import hashlib
import pyotp
import pyodbc
import sys
import pyqtgraph as pg
import time
import serial
import csv
import joblib
import numpy as np
import matplotlib.pyplot as plt

# Función para conectar a la base de datos
def get_connection():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};' 
        'SERVER=DESKTOP-D5VHBMM\\MSSQLSERVER1;'#Cambiar por el servidor que tiene
        'DATABASE=DataBaseProject;'
        'Trusted_Connection=yes;'#Si su servidor tiene contraseña agregar la linea 'UID=tu_usuario' y en otra linea 'PWD=tu_contraseña'
    )

# Función para verificar las credenciales desde SQL Server
def verify_credentials(username, password):
    connection = get_connection()

    if connection:
        print("Conexión exitosa")
    else:
        print("Error en la conexión")

    cursor = connection.cursor()
    cursor.execute("SELECT role, password_hash, totp_secret FROM users WHERE username = ?", username)
    user = cursor.fetchone()
    connection.close()

    if user:
        role, stored_password, totp_secret = user
        # Convertir tanto la contraseña ingresada como la almacenada a minúsculas (o mayúsculas)
        if hashlib.sha256(password.encode()).hexdigest().lower() == stored_password.lower():
            return role, totp_secret

    return None, None

def guardar_lectura(corriente, potencia, artefacto_id):
    """Guarda una lectura en la base de datos con el artefacto asociado."""
    try:
        # Intentar la conexión a la base de datos
        conn = get_connection()
        cursor = conn.cursor()

        # Ejecutar el comando INSERT
        cursor.execute("""
            INSERT INTO Lecturas (fecha_hora, corriente, potencia, artefacto_id)
            VALUES (GETDATE(), ?, ?, ?)
        """, (corriente, potencia, artefacto_id))
        conn.commit()  # Confirmar los cambios
        
    except Exception as e:
        print(f"Error al guardar lectura en la base de datos: {e}")
    finally:
        # Cerrar la conexión
        try:
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error al cerrar la conexión: {e}")


class RealTimeMonitoring(QtWidgets.QWidget):
    def __init__(self, arduino_reader=None, artefacto_id=None, artefacto_nombre=""):
        super().__init__()
        self.arduino_reader = arduino_reader
        self.artefacto_id = artefacto_id
        self.artefacto_nombre = artefacto_nombre
        self.setup_ui()
        self.init_data()

        # Configurar el temporizador para leer datos
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)

    def setup_ui(self):
        """Configura la interfaz de monitoreo en tiempo real."""
        self.layout = QtWidgets.QVBoxLayout(self)

        # Widget de gráficos
        self.plot_widget = pg.GraphicsLayoutWidget()
        self.plot_corriente = self.plot_widget.addPlot(title="Corriente (A)")
        self.plot_potencia = self.plot_widget.addPlot(title="Potencia (W)", row=1, col=0)

        # Configurar fondo blanco
        self.plot_corriente.getViewBox().setBackgroundColor('w')
        self.plot_potencia.getViewBox().setBackgroundColor('w')

        # Etiquetas de los ejes
        self.plot_corriente.setLabel('left', 'Corriente (A)')
        self.plot_corriente.setLabel('bottom', 'Tiempo (s)')
        self.plot_potencia.setLabel('left', 'Potencia (W)')
        self.plot_potencia.setLabel('bottom', 'Tiempo (s)')

        # Agregar el widget de gráficos al diseño
        self.layout.addWidget(self.plot_widget)

        # Etiqueta para mostrar los datos al hacer clic
        self.data_label = QtWidgets.QLabel("")
        self.data_label.setFont(QtGui.QFont("Arial", 12))
        self.data_label.setAlignment(QtCore.Qt.AlignCenter)
        self.data_label.setStyleSheet("background-color: white; border: 1px solid black; padding: 5px;")
        self.layout.addWidget(self.data_label)

        # Conectar el evento de clic
        self.plot_corriente.scene().sigMouseClicked.connect(self.display_clicked_data)
        self.plot_potencia.scene().sigMouseClicked.connect(self.display_clicked_data)

    def init_data(self):
        """Inicializa los datos del monitoreo."""
        self.times = []
        self.corrientes = []
        self.potencias = []
        self.start_time = time.time()

    def start_monitoring(self):
        """Inicia el monitoreo en tiempo real después de seleccionar un artefacto."""
        if self.arduino_reader:
            # Comienza el monitoreo
            print("Monitoreo en tiempo real iniciado.")
            self.timer.start(100)  # Leer datos cada 100 ms
        else:
            QtWidgets.QMessageBox.critical(self, "Error", "No se ha conectado al Arduino.")

    def stop_monitoring(self):
        """Detiene el monitoreo."""
        self.timer.stop()
        if self.arduino_reader:
            try:
                self.arduino_reader.close()
                self.arduino_reader = None
            except Exception as e:
                print(f"Error al cerrar la conexión con el Arduino: {e}")

    def update_plot(self):
        """Actualiza las gráficas con los datos del Arduino y guarda las lecturas en la base de datos."""
        if not self.arduino_reader:
            return

        while self.arduino_reader.in_waiting > 0:
            try:
                line = self.arduino_reader.readline().decode('utf-8').strip()
                if "Irms" in line and "Potencia" in line:
                    parts = line.split(",")
                    corriente = float(parts[0].split(":")[1].strip().replace("A", ""))
                    potencia = float(parts[1].split(":")[1].strip().replace("W", ""))

                    # Eliminar o comentar los prints
                    # print(f"Lectura recibida: Corriente={corriente}, Potencia={potencia}, Artefacto={self.artefacto_id}")

                    elapsed_time = time.time() - self.start_time
                    self.times.append(elapsed_time)
                    self.corrientes.append(corriente)
                    self.potencias.append(potencia)
                    self.plot_corriente.plot(self.times, self.corrientes, clear=True, pen='r')
                    self.plot_potencia.plot(self.times, self.potencias, clear=True, pen='b')

                    # Guardar la lectura en la base de datos
                    if self.artefacto_id:
                        guardar_lectura(corriente, potencia, self.artefacto_id)

            except Exception as e:
                print(f"Error al procesar datos del Arduino: {e}")

    def display_clicked_data(self, event):
        """Muestra los valores del punto más cercano en ambas gráficas al hacer clic."""
        pos = event.scenePos()

        # Detectar clic en cualquier gráfica
        if (self.plot_corriente.sceneBoundingRect().contains(pos) or
                self.plot_potencia.sceneBoundingRect().contains(pos)):
            mouse_point = self.plot_corriente.vb.mapSceneToView(pos)  # Obtener posición en términos de la gráfica
            x = mouse_point.x()  # Tiempo en el eje X

            # Buscar el punto más cercano
            if len(self.times) > 0:
                closest_index = min(range(len(self.times)), key=lambda i: abs(self.times[i] - x))
                tiempo = self.times[closest_index]
                corriente = self.corrientes[closest_index]
                potencia = self.potencias[closest_index]

                # Mostrar los valores de tiempo, corriente y potencia
                self.data_label.setText(
                    f"Tiempo: {tiempo:.3f}s\n"
                    f"Corriente: {corriente:.3f}A\n"
                    f"Potencia: {potencia:.3f}W"
                )

        # Detectar clic en la gráfica de potencia
        elif self.plot_potencia.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_potencia.vb.mapSceneToView(pos)
            x = mouse_point.x()

            # Buscar el punto más cercano
            if len(self.times) > 0:
                closest_index = min(range(len(self.times)), key=lambda i: abs(self.times[i] - x))
                tiempo = self.times[closest_index]
                potencia = self.potencias[closest_index]
                self.data_label.setText(f"Tiempo: {tiempo:.3f}s\nCorriente: -\nPotencia: {potencia:.3f}W")

class LoginWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inicio de Sesión")
        self.setFixedSize(600, 400)
        self.setWindowIcon(QtGui.QIcon("C:/Users/BENJAMIN/OneDrive/Escritorio/icono.ico"))

        # Fondo con imagen o degradado
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    spread:pad, x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(63, 81, 181, 255),
                    stop:1 rgba(156, 39, 176, 255)
                );
            }
        """)

        # Layout principal
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignCenter)

        # Título
        self.platform_title = QtWidgets.QLabel("Plataforma de Monitoreo Energético")
        self.platform_title.setFont(QtGui.QFont("Arial", 20, QtGui.QFont.Bold))
        self.platform_title.setStyleSheet("color: white;")
        self.platform_title.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.addWidget(self.platform_title)

        # Usuario
        self.user_label = QtWidgets.QLabel("Usuario:")
        self.user_label.setFont(QtGui.QFont("Arial", 12))
        self.user_label.setStyleSheet("color: white;")
        self.layout.addWidget(self.user_label)
        self.user_input = QtWidgets.QLineEdit()
        self.user_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid white;
                border-radius: 15px;
                padding: 10px;
                background-color: rgba(255, 255, 255, 0.8);
                font-size: 14px;
                font-family: Arial;
            }
            QLineEdit:focus {
                border: 2px solid #00BCD4;
            }
        """)
        self.layout.addWidget(self.user_input)

        # Contraseña
        self.pass_label = QtWidgets.QLabel("Contraseña:")
        self.pass_label.setFont(QtGui.QFont("Arial", 12))
        self.pass_label.setStyleSheet("color: white;")
        self.layout.addWidget(self.pass_label)

        pass_layout = QtWidgets.QHBoxLayout()
        self.pass_input = QtWidgets.QLineEdit()
        self.pass_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid white;
                border-radius: 15px;
                padding: 10px;
                background-color: rgba(255, 255, 255, 0.8);
                font-size: 14px;
                font-family: Arial;
            }
            QLineEdit:focus {
                border: 2px solid #00BCD4;
            }
        """)
        self.pass_input.setEchoMode(QtWidgets.QLineEdit.Password)
        pass_layout.addWidget(self.pass_input)

        self.show_password_btn = QtWidgets.QPushButton("👁")
        self.show_password_btn.setFixedSize(30, 30)
        self.show_password_btn.clicked.connect(self.toggle_password)
        self.show_password_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
                border-radius: 15px;
            }
        """)
        pass_layout.addWidget(self.show_password_btn)
        self.layout.addLayout(pass_layout)

        # Etiqueta de error
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color: red; font-size: 14px;")
        self.layout.addWidget(self.error_label)

        # Botón de iniciar sesión
        self.login_button = QtWidgets.QPushButton("Iniciar Sesión")
        self.login_button.setFont(QtGui.QFont("Arial", 14))
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                                stop:0 rgba(33, 150, 243, 255), stop:1 rgba(3, 169, 244, 255));
                border-radius: 20px;
                padding: 10px;
                color: white;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                                stop:0 rgba(3, 169, 244, 255), stop:1 rgba(33, 150, 243, 255));
            }
        """)
        self.login_button.clicked.connect(self.attempt_login)
        self.layout.addWidget(self.login_button)

        # Animación de carga (GIF)
        self.loading_label = QtWidgets.QLabel()
        self.loading_gif = QtGui.QMovie("C:/Users/BENJAMIN/OneDrive/Escritorio/rueda.gif")
        self.loading_label.setMovie(self.loading_gif)
        self.loading_label.hide()

        self.welcome_message_label = QtWidgets.QLabel()
        self.welcome_message_label.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))
        self.welcome_message_label.setAlignment(QtCore.Qt.AlignCenter)
        self.welcome_message_label.setStyleSheet("color: white;")
        self.welcome_message_label.hide()

        self.layout.addWidget(self.welcome_message_label, alignment=QtCore.Qt.AlignCenter)
        self.layout.addWidget(self.loading_label, alignment=QtCore.Qt.AlignCenter)

        self.setLayout(self.layout)

        # Permitir presionar "Enter" para iniciar sesión
        self.user_input.returnPressed.connect(self.attempt_login)
        self.pass_input.returnPressed.connect(self.attempt_login)

    def toggle_password(self):
        if self.pass_input.echoMode() == QtWidgets.QLineEdit.Password:
            self.pass_input.setEchoMode(QtWidgets.QLineEdit.Normal)
            self.show_password_btn.setText("🔒")
        else:
            self.pass_input.setEchoMode(QtWidgets.QLineEdit.Password)
            self.show_password_btn.setText("👁")

    def attempt_login(self):
        username = self.user_input.text()
        password = self.pass_input.text()
        role, totp_secret = verify_credentials(username, password)

        if not role:
            self.error_label.setText("Usuario y/o contraseña incorrecto(s)")
            self.error_label.show()
        else:
            self.show_welcome_message(username)

    def show_welcome_message(self, username):
        self.user_label.hide()
        self.user_input.hide()
        self.pass_label.hide()
        self.pass_input.hide()
        self.show_password_btn.hide()
        self.login_button.hide()
        self.error_label.hide()

        self.welcome_message_label.setText(f"Bienvenido(a), {username}!")
        self.welcome_message_label.show()
        self.loading_label.show()
        self.loading_gif.start()
        QtCore.QTimer.singleShot(2000, lambda: self.open_normal_user_window(username))

    def open_normal_user_window(self, username):
        self.normal_user_window = NormalUserWindow(username)
        self.normal_user_window.show()
        self.close()

class NormalUserWindow(QtWidgets.QWidget):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.arduino_reader = None  # Inicializar sin conexión al Arduino
        self.analysis_panel = None
        self.full_name = self.get_user_full_name(username)  # Obtener el nombre completo desde la base de datos
        self.current_theme = "Claro"  # Estado inicial del tema

        self.setWindowTitle(f"Panel de Monitoreo Energético ({self.username})")
        self.setWindowIcon(QtGui.QIcon("C:/Users/BENJAMIN/OneDrive/Escritorio/casco.ico")) #Cambie esta dirección por la nueva que tendrá en su computador)
        self.setGeometry(100, 100, 1400, 900)

        # Fondo inicial (tema claro por defecto)
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    spread:pad, x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(240, 248, 255, 255),
                    stop:1 rgba(224, 255, 255, 255)
                );
            }
        """)

        # Layout principal
        self.layout = QtWidgets.QVBoxLayout(self)

        # Crear el widget principal para contener los elementos
        self.main_widget = QtWidgets.QWidget()

        # Layout principal dentro del widget
        self.main_layout = QtWidgets.QVBoxLayout(self.main_widget)

        # Llamar a la inicialización de la interfaz
        self.init_ui()

    def init_ui(self):
        """Inicializa la interfaz principal del usuario."""
        try:
            self.add_functionality_buttons()  # Asegúrate de que los botones estén configurados correctamente
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Error al configurar los botones: {e}")

        # Crear un widget principal para contener los elementos
        self.main_widget = QtWidgets.QWidget()
        self.main_layout = QtWidgets.QVBoxLayout(self.main_widget)

        # Barra superior
        top_bar = QtWidgets.QHBoxLayout()
        self.user_label = QtWidgets.QLabel(f"Usuario: {self.full_name}")
        self.user_label.setFont(QtGui.QFont("Arial", 16))
        self.user_label.setStyleSheet("color: #333;")
        top_bar.addWidget(self.user_label)

        # Botón de menú
        self.menu_button = QtWidgets.QPushButton()
        self.menu_button.setIcon(QtGui.QIcon("C:/Users/BENJAMIN/OneDrive/Escritorio/menu.png"))
        self.menu_button.setIconSize(QtCore.QSize(60, 60))
        self.menu_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(200, 200, 200, 0.5);
                border-radius: 30px;
            }
        """)
        self.menu_button.clicked.connect(self.show_menu)
        top_bar.addWidget(self.menu_button, alignment=QtCore.Qt.AlignRight)

        self.main_layout.addLayout(top_bar)

        # Añadir botones de funcionalidad
        self.add_functionality_buttons()

        # Añadir el widget principal a la ventana
        self.layout.addWidget(self.main_widget)

    def closeEvent(self, event):
        """Se llama al cerrar la ventana para liberar recursos como el Arduino."""
        if hasattr(self, 'monitoring_widget') and self.monitoring_widget:
            self.monitoring_widget.stop_monitoring()  # Detener monitoreo y cerrar conexión
        event.accept()

    def add_functionality_buttons(self):
        """Añadir botones de funcionalidad como 'Monitoreo en Tiempo Real'."""
        func_layout = QtWidgets.QGridLayout()
        
        # Opciones de funcionalidad
        func_options = {
            "Monitoreo en Tiempo Real": (
                "C:/Users/BENJAMIN/OneDrive/Escritorio/graficotiempo.jpg",
                self.start_real_time_monitoring,
                "Visualiza datos en tiempo real"
            ),
            "Descargar Datos": (
                "C:/Users/BENJAMIN/OneDrive/Escritorio/descargacsv.png",
                self.start_csv_panel,
                "Descarga los datos en formato CSV"
            ),
            "Análisis de Anomalías": (
                "C:/Users/BENJAMIN/OneDrive/Escritorio/anomalias.jpg",
                self.start_analysis_panel,
                "Recibe alertas de anomalías"
            ),
            "Historial de Lecturas": (
                "C:/Users/BENJAMIN/OneDrive/Escritorio/historial.jpg",
                self.open_historial_lecturas,
                "Consulta lecturas históricas"
            ),
        }

        for i, (title, (icon_path, function, description)) in enumerate(func_options.items()):
            button = self.create_function_button(title, icon_path, function, description)
            func_layout.addWidget(button, i // 2, i % 2)

        self.main_layout.addLayout(func_layout)

    def create_function_button(self, title, icon_path, function, description):
        """Crear un botón para cada funcionalidad."""
        button = QtWidgets.QPushButton()
        button.setIcon(QtGui.QIcon(icon_path))
        button.setIconSize(QtCore.QSize(100, 100))
        button.setText(title)
        button.setStyleSheet("""
            QPushButton {
                text-align: center;
                font-size: 14px;
                padding: 10px;
                border-radius: 10px;
                background-color: #f7f7f7;
            }
            QPushButton:hover {
                background-color: rgba(200, 200, 255, 0.8);
            }
        """)
        button.clicked.connect(function)

        # Evento para desvanecer el botón al pasar el ratón
        def on_enter(event):
            button.setStyleSheet("""
                QPushButton {
                    text-align: center;
                    font-size: 14px;
                    padding: 10px;
                    border-radius: 10px;
                    background-color: rgba(180, 180, 255, 0.8);  /* Efecto de desvanecimiento */
                }
            """)
            button.setText(description)  # Mostrar la descripción cuando el ratón pase por encima
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), description)  # Mostrar el tooltip

        def on_leave(event):
            button.setStyleSheet("""
                QPushButton {
                    text-align: center;
                    font-size: 14px;
                    padding: 10px;
                    border-radius: 10px;
                    background-color: #f7f7f7;
                }
            """)
            button.setText(title)  # Restablecer el texto del botón cuando el ratón salga

        # Conectar los eventos de entrar y salir del ratón
        button.enterEvent = on_enter
        button.leaveEvent = on_leave

        return button

    def start_real_time_monitoring(self):
        """Muestra la tabla de artefactos antes de iniciar el monitoreo en tiempo real."""
        # Guardar el widget principal actual para regresar después
        self.previous_widget = self.main_widget

        # Eliminar el contenido actual
        self.layout.removeWidget(self.main_widget)
        self.main_widget.deleteLater()

        # Crear el widget de la tabla de artefactos
        self.main_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.main_widget)

        # Título de la sección
        title = QtWidgets.QLabel("Monitoreo en Tiempo Real - Seleccione un Artefacto")
        title.setFont(QtGui.QFont("Arial", 16, QtGui.QFont.Bold))
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("padding: 10px;")
        layout.addWidget(title)

        # Crear la tabla de artefactos
        self.artifact_table = QtWidgets.QTableWidget()
        self.artifact_table.setColumnCount(3)
        self.artifact_table.setHorizontalHeaderLabels(["Artefacto", "Estado", "Ver"])
        self.artifact_table.horizontalHeader().setStretchLastSection(True)
        self.artifact_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.load_artifacts_to_table()
        layout.addWidget(self.artifact_table)

        # Botón de regresar
        back_button = QtWidgets.QPushButton("Regresar")
        back_button.setFont(QtGui.QFont("Arial", 12))
        back_button.setStyleSheet("""QPushButton {background-color: #f7f7f7; border-radius: 10px; padding: 10px; font-size: 14px;}""")
        back_button.clicked.connect(self.return_to_main)
        layout.addWidget(back_button, alignment=QtCore.Qt.AlignRight)

        self.layout.addWidget(self.main_widget)

        # Verifica si el Arduino está conectado y procede a iniciar el monitoreo
        if not self.arduino_reader:
            try:
                # Intentar conectar con el Arduino
                self.arduino_reader = serial.Serial('COM7', 9600, timeout=1)
            except serial.SerialException as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo conectar al Arduino: {e}")
                return  # Detener el flujo si falla la conexión

        # Aquí puedes empezar el monitoreo después de seleccionar un artefacto
        self.start_monitoring()

    def start_monitoring(self):
        """Inicia el monitoreo en tiempo real después de seleccionar un artefacto."""
        if self.arduino_reader:
            # Aquí puedes agregar la lógica de actualización de gráficos o cualquier otro proceso de monitoreo
            print("Monitoreo en tiempo real iniciado.")
            self.timer.start(100)  # Leer datos cada 100 ms
        else:
            QtWidgets.QMessageBox.critical(self, "Error", "No se ha conectado al Arduino.")

    def load_artifacts_to_table(self):
        """Carga los artefactos desde la base de datos en la tabla."""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT id, nombre FROM artefactos")
            artifacts = cursor.fetchall()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"No se pudieron cargar los artefactos: {e}")
            return
        finally:
            conn.close()

        self.artifact_table.setRowCount(len(artifacts))
        for row, (artifact_id, artifact_name) in enumerate(artifacts):
            # Columna 1: Nombre del artefacto
            self.artifact_table.setItem(row, 0, QtWidgets.QTableWidgetItem(artifact_name))

            # Columna 2: Botón de estado ON/OFF
            state_button = QtWidgets.QPushButton("OFF")
            state_button.setCheckable(True)
            state_button.setStyleSheet("background-color: red; color: white;")
            state_button.clicked.connect(
                lambda _, r=row: self.toggle_artifact_state(r)
            )
            self.artifact_table.setCellWidget(row, 1, state_button)

            # Columna 3: Botón "Ver"
            view_button = QtWidgets.QPushButton("Ver")
            view_button.setEnabled(False)  # Solo habilitado si el artefacto está encendido
            view_button.clicked.connect(
                lambda _, a_id=artifact_id, a_name=artifact_name: self.show_graph(a_id, a_name)
            )
            self.artifact_table.setCellWidget(row, 2, view_button)

    def toggle_artifact_state(self, row):
        """Cambia el estado de un artefacto a ON/OFF y habilita el botón Ver."""
        for i in range(self.artifact_table.rowCount()):
            state_button = self.artifact_table.cellWidget(i, 1)
            view_button = self.artifact_table.cellWidget(i, 2)

            if i == row:
                if state_button.isChecked():
                    state_button.setText("ON")
                    state_button.setStyleSheet("background-color: green; color: white;")
                    view_button.setEnabled(True)
                else:
                    state_button.setText("OFF")
                    state_button.setStyleSheet("background-color: red; color: white;")
                    view_button.setEnabled(False)
            else:
                # Asegurarse de que solo un artefacto pueda estar encendido
                state_button.setChecked(False)
                state_button.setText("OFF")
                state_button.setStyleSheet("background-color: red; color: white;")
                view_button.setEnabled(False)

    def show_graph(self, artifact_id, artifact_name):
        """Muestra la gráfica para el artefacto seleccionado."""
        # Eliminar el contenido actual
        self.layout.removeWidget(self.main_widget)
        self.main_widget.deleteLater()

        # Crear el widget de monitoreo
        self.main_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.main_widget)

        # Título dinámico
        title = QtWidgets.QLabel(f"Monitoreo en Tiempo Real ({artifact_name})")
        title.setFont(QtGui.QFont("Arial", 16, QtGui.QFont.Bold))
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)

        # Agregar el monitoreo
        self.monitoring_widget = RealTimeMonitoring(self.arduino_reader, artifact_id, artifact_name)
        self.monitoring_widget.start_monitoring()
        layout.addWidget(self.monitoring_widget)

        # Botón de regresar
        back_button = QtWidgets.QPushButton("Regresar")
        back_button.setFont(QtGui.QFont("Arial", 12))
        back_button.clicked.connect(self.start_real_time_monitoring)
        layout.addWidget(back_button, alignment=QtCore.Qt.AlignRight)

        self.layout.addWidget(self.main_widget)

    def start_csv_panel(self):
        """Cambia al panel de Descarga de Datos CSV."""
        try:
            # Crear la conexión a la base de datos (solo al hacer clic)
            db_connection = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=DESKTOP-D5VHBMM\\MSSQLSERVER1;'
            'DATABASE=DataBaseProject;'
            'Trusted_Connection=yes;'
            )

            # Crear el panel CSV y pasar la conexión
            self.previous_widget = self.main_widget

            # Eliminar el contenido actual
            self.layout.removeWidget(self.main_widget)
            self.main_widget.deleteLater()

            # Crear el widget del panel CSV
            self.main_widget = CSVPanel(db_connection)
            self.main_widget.back_button.clicked.connect(self.return_to_main)  # Conectar el botón de "Regresar"
            self.layout.addWidget(self.main_widget)

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo conectar a la base de datos: {e}")

    def start_analysis_panel(self):
        """Muestra el panel de análisis de anomalías."""
        try:
            if self.analysis_panel is None:
                self.analysis_panel = AnomalyAnalysisPanel(self)  # Crea el panel si no existe
            self.hide()  # Oculta la ventana principal
            self.analysis_panel.show()  # Muestra el panel de anomalías
        except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo abrir el análisis de anomalías: {e}")

    def get_connection(self):
        """Devuelve una conexión activa a la base de datos."""
        try:
            conn = pyodbc.connect(
                'DRIVER={ODBC Driver 17 for SQL Server};'
                'SERVER=DESKTOP-D5VHBMM\\MSSQLSERVER1;'  # Cambia por tu servidor si es necesario
                'DATABASE=DataBaseProject;'             # Asegúrate de que este sea tu nombre de base de datos
                'Trusted_Connection=yes;'
            )
            return conn
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo conectar a la base de datos: {e}")
            return None

    def return_to_main(self):
        """Returns from the analysis panel to the main interface."""
        if self.analysis_panel:
            self.analysis_panel.setParent(None)
            self.analysis_panel = None

        # Rebuild the main interface
        self.init_ui()

    def open_historial_lecturas(self):
        """Abre la ventana de historial de lecturas."""
        # Asegúrate de que `get_connection` esté bien definido para conectar a tu DB
        db_connection = get_connection()
        self.historial_window = HistorialLecturasWindow(db_connection)
        self.historial_window.show()

    def return_to_main(self):
        """Regresa al contenido principal de la ventana."""
        # Verificar si existe un widget principal dinámico (Monitoreo o CSVPanel)
        if hasattr(self, 'main_widget'):
            self.layout.removeWidget(self.main_widget)
            self.main_widget.deleteLater()

        # Recrear el widget principal
        self.main_widget = QtWidgets.QWidget()
        self.main_layout = QtWidgets.QVBoxLayout(self.main_widget)

        # Llamar a la inicialización de la interfaz principal
        self.init_ui()

        # Añadir de nuevo el widget principal a la ventana
        self.layout.addWidget(self.main_widget)

    def toggle_theme(self):
        """Cambia entre temas claro y oscuro."""
        if self.current_theme == "Claro":
            self.current_theme = "Oscuro"
            
            # Cambiar el tema global a oscuro
            self.setStyleSheet("""
                QWidget {
                    background: #333;
                    color: white;
                }
                QPushButton {
                    background-color: #444;
                    color: white;
                    border-radius: 10px;
                    padding: 10px;
                }
                QPushButton:hover {
                    background-color: #555;
                }
                QTableWidget {
                    background-color: #333;
                    color: white;
                }
                QTableWidget::item {
                    border: 1px solid #444;
                }
                QHeaderView::section {
                    background-color: #444;
                    color: white;
                }
                QTableWidget QTableCornerButton::section {
                    background-color: #444;
                }
            """)

            self.user_label.setStyleSheet("color: white;")
            
        else:
            self.current_theme = "Claro"
            
            # Cambiar el tema global a claro
            self.setStyleSheet("""
                QWidget {
                    background: qlineargradient(
                        spread:pad, x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(240, 248, 255, 255),
                        stop:1 rgba(224, 255, 255, 255)
                    );
                    color: #333;
                }
                QPushButton {
                    background-color: #f7f7f7;
                    color: #333;
                    border-radius: 10px;
                    padding: 10px;
                }
                QPushButton:hover {
                    background-color: rgba(200, 200, 255, 0.8);
                }
                QTableWidget {
                    background-color: #f7f7f7;
                    color: #333;
                }
                QTableWidget::item {
                    border: 1px solid #ddd;
                }
                QHeaderView::section {
                    background-color: #f7f7f7;
                    color: #333;
                }
                QTableWidget QTableCornerButton::section {
                    background-color: #f7f7f7;
                }
            """)

            self.user_label.setStyleSheet("color: #333;")

    def get_user_full_name(self, username):
        """Obtener el nombre completo desde la base de datos."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT nombres, apellidos FROM users WHERE username = ?", username)
            user = cursor.fetchone()
            if user and user[0] and user[1]:
                return f"{user[0]} {user[1]}"
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Error al obtener el nombre: {e}")
        finally:
            conn.close()
        return username

    def show_menu(self):
        """Muestra un menú contextual con opciones."""
        menu = QtWidgets.QMenu(self)

        # Cambiar tema
        theme_action = menu.addAction(f"Cambiar Tema: {self.current_theme}")
        theme_action.triggered.connect(self.toggle_theme)

        # Perfil de usuario
        profile_action = menu.addAction("Perfil de Usuario")
        profile_action.triggered.connect(self.show_profile)

        # Acerca de
        about_action = menu.addAction("Acerca de")
        about_action.triggered.connect(self.show_about)

        # Cerrar sesión
        logout_action = menu.addAction("Cerrar Sesión")
        logout_action.triggered.connect(self.logout)

        menu.exec_(QtGui.QCursor.pos())

    def switch_to_main_panel(self):

        if self.analysis_panel:
            self.analysis_panel.hide()  # Oculta el panel de análisis de anomalías
        self.show()  # Muestra el panel principal

    def show_profile(self):
        QtWidgets.QMessageBox.information(self, "Perfil de Usuario", "Mostrando el perfil de usuario...")

    def show_about(self):
        QtWidgets.QMessageBox.information(self, "Acerca de", "Aplicación de Monitoreo Energético v1.0")

    def logout(self):
        """Cierra sesión y regresa al login."""
        self.close()
        self.login_window = LoginWindow()
        self.login_window.show()


class CSVPanel(QtWidgets.QWidget):
    def __init__(self, db_connection):
        super().__init__()
        self.db_connection = db_connection  # Conexión a la base de datos
        self.setWindowTitle("CSV Panel")
        self.setup_ui()

    def setup_ui(self):
        """Configura la interfaz del panel."""
        self.layout = QtWidgets.QVBoxLayout(self)

        # Título del panel
        title = QtWidgets.QLabel("Descargar Datos CSV")
        title.setFont(QtGui.QFont("Arial", 16, QtGui.QFont.Bold))
        title.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.addWidget(title)

        # Tabla para listar artefactos
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Artefacto", "Descargar"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.layout.addWidget(self.table)

        # Botón de regresar
        self.back_button = QtWidgets.QPushButton("Regresar")
        self.layout.addWidget(self.back_button, alignment=QtCore.Qt.AlignRight)

        self.load_artefacts()

    def load_artefacts(self):
        """Carga los artefactos desde la base de datos."""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT id, nombre FROM artefactos")
            artefacts = cursor.fetchall()

            self.table.setRowCount(len(artefacts))
            for row, (artefact_id, artefact_name) in enumerate(artefacts):
                self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(artefact_name))
                download_button = QtWidgets.QPushButton("Descargar")
                download_button.clicked.connect(lambda _, aid=artefact_id: self.download_csv(aid))
                self.table.setCellWidget(row, 1, download_button)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"No se pudieron cargar los artefactos: {e}")

    def download_csv(self, artefact_id):
        """Inicia la exportación de datos del artefacto a CSV."""
        file_dialog = QtWidgets.QFileDialog.getSaveFileName(self, "Guardar como", "", "CSV Files (*.csv)")
        file_path = file_dialog[0]

        if file_path:
            self.worker = CSVExportWorker(self.db_connection, file_path, artefact_id)
            self.worker.finished.connect(self.on_export_finished)
            self.worker.start()

    def on_export_finished(self, message):
        """Muestra un mensaje al finalizar la exportación."""
        QtWidgets.QMessageBox.information(self, "Exportación CSV", message)

    def closeEvent(self, event):
        """Cerrar la conexión a la base de datos al cerrar el panel."""
        if self.db_connection:
            self.db_connection.close()
        super().closeEvent(event)

class CSVExportWorker(QtCore.QThread):
    finished = QtCore.pyqtSignal(str)  # Señal para indicar que terminó

    def __init__(self, db_connection, file_path, artefact_id):
        super().__init__()
        self.db_connection = db_connection
        self.file_path = file_path
        self.artefact_id = artefact_id

    def run(self):
        """Realiza la exportación en un hilo separado."""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                SELECT fecha_hora, corriente, potencia
                FROM lecturas
                WHERE artefacto_id = ?
                ORDER BY fecha_hora
            """, (self.artefact_id,))
            rows = cursor.fetchall()

            with open(self.file_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["Fecha y Hora", "Corriente (A)", "Potencia (W)"])
                writer.writerows(rows)

            self.finished.emit("Exportación completada con éxito.")
        except Exception as e:
            self.finished.emit(f"Error durante la exportación: {e}")


class AnomalyAnalysisPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent  # Referencia al panel principal
        self.setWindowTitle('Análisis de Anomalías')
        self.setup_ui()

    def setup_ui(self):
        """Configura la interfaz gráfica del panel."""
        layout = QtWidgets.QVBoxLayout(self)

        # Botón para regresar al panel principal
        self.back_button = QtWidgets.QPushButton('Regresar', self)
        self.back_button.clicked.connect(self.return_to_main)
        layout.addWidget(self.back_button)

        # Botón para analizar datos históricos
        self.analyze_button = QtWidgets.QPushButton('Analizar Datos Históricos', self)
        self.analyze_button.clicked.connect(self.analyze_data)
        layout.addWidget(self.analyze_button)

        # Botón para ver gráfico de anomalías
        self.view_graph_button = QtWidgets.QPushButton('Ver Gráfico de Anomalías', self)
        self.view_graph_button.clicked.connect(self.view_anomalies_graph)
        layout.addWidget(self.view_graph_button)

        # Botón para ver tabla de anomalías
        self.view_table_button = QtWidgets.QPushButton('Ver Tabla de Anomalías', self)
        self.view_table_button.clicked.connect(self.view_anomalies_table)
        layout.addWidget(self.view_table_button)

        # Tabla para mostrar resultados
        self.resultados_tabla = QtWidgets.QTableWidget(self)
        self.resultados_tabla.setColumnCount(3)
        self.resultados_tabla.setHorizontalHeaderLabels(["Corriente (A)", "Potencia (W)", "Estado"])
        layout.addWidget(self.resultados_tabla)

        self.setLayout(layout)

    def return_to_main(self):
        """Regresa al panel principal."""
        if self.parent:
            self.parent.switch_to_main_panel()

    def analyze_data(self):
        """Lógica para analizar datos históricos."""
        print("Analizando datos históricos...")
        # Aquí conectas tu modelo y tus datos históricos
        try:
            model = joblib.load("modelo.pkl")  # Cargar el modelo entrenado
            data = self.obtener_datos_historicos()  # Obtener datos históricos
            if not data:
                QtWidgets.QMessageBox.warning(self, "Advertencia", "No hay datos históricos disponibles.")
                return
            predictions = model.predict(data)
            resultados = [
                {
                    "corriente": data[i][0],
                    "potencia": data[i][1],
                    "estado": "Anomalía" if pred == -1 else "Normal"
                }
                for i, pred in enumerate(predictions)
            ]
            self.mostrar_resultados(resultados)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo analizar los datos: {e}")

    def obtener_datos_historicos(self):
        """Obtiene los datos históricos de la base de datos."""
        try:
            conn = self.parent.get_connection()  # Usa el método get_connection del panel principal
            if conn is None:
                return []  # Si no hay conexión, regresa una lista vacía
            cursor = conn.cursor()
            cursor.execute("SELECT corriente, potencia FROM Lecturas WHERE artefacto_id IS NOT NULL")
            rows = cursor.fetchall()
            conn.close()
            return [[row.corriente, row.potencia] for row in rows]
        except Exception as e:
            print(f"Error al obtener datos históricos: {e}")
            return []

    def mostrar_resultados(self, resultados):
        """Muestra los resultados del análisis en la tabla."""
        self.resultados_tabla.setRowCount(len(resultados))
        for row, resultado in enumerate(resultados):
            self.resultados_tabla.setItem(row, 0, QtWidgets.QTableWidgetItem(f"{resultado['corriente']:.3f}"))
            self.resultados_tabla.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{resultado['potencia']:.3f}"))
            self.resultados_tabla.setItem(row, 2, QtWidgets.QTableWidgetItem(resultado['estado']))

    def view_anomalies_graph(self):
        """Muestra un gráfico de las anomalías detectadas."""
        try:
            data = self.obtener_datos_historicos()
            model = joblib.load("modelo.pkl")
            predictions = model.predict(data)

            # Preparar datos para graficar
            normales = [data[i] for i in range(len(data)) if predictions[i] == 1]
            anomalias = [data[i] for i in range(len(data)) if predictions[i] == -1]

            normales_x = [d[0] for d in normales]
            normales_y = [d[1] for d in normales]
            anomalias_x = [d[0] for d in anomalias]
            anomalias_y = [d[1] for d in anomalias]

            # Graficar
            plt.scatter(normales_x, normales_y, label="Normal", color="green")
            plt.scatter(anomalias_x, anomalias_y, label="Anomalía", color="red")
            plt.xlabel("Corriente (A)")
            plt.ylabel("Potencia (W)")
            plt.title("Análisis de Anomalías")
            plt.legend()
            plt.show()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo generar el gráfico: {e}")

    def view_anomalies_table(self):
        """Muestra los resultados del análisis en la tabla."""
        print("Mostrando resultados en tabla...")
        self.analyze_data()  # Llama al análisis de datos y actualiza la tabla

class HistorialLecturasWindow(QtWidgets.QWidget):
    def __init__(self, db_connection):
        super().__init__()
        self.db_connection = db_connection
        self.setWindowTitle("Historial de Lecturas")
        self.setFixedSize(800, 600)
        self.setup_ui()

    def setup_ui(self):
        """Configura la interfaz de la ventana de historial de lecturas."""
        self.layout = QtWidgets.QVBoxLayout(self)

        # Selector de fecha
        self.date_picker = QtWidgets.QDateEdit(self)
        self.date_picker.setDate(QtCore.QDate.currentDate())  # Por defecto, hoy
        self.date_picker.setDisplayFormat("yyyy-MM-dd")
        self.layout.addWidget(self.date_picker)

        # Botón para cargar lecturas
        self.load_button = QtWidgets.QPushButton("Cargar Lecturas", self)
        print("Conectando botón 'Cargar Lecturas' al método load_lecturas")
        self.load_button.clicked.connect(self.load_lecturas)  # Conexión al método
        self.layout.addWidget(self.load_button)

        # Tabla para mostrar las lecturas
        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Fecha", "Artefacto", "Corriente (A)", "Potencia (W)"])
        self.layout.addWidget(self.table)

    def load_lecturas(self):
        """Cargar lecturas desde la base de datos y mostrar en la tabla."""
        try:
            # Obtener artefacto_id y la fecha seleccionada
            artefacto_id = 1  # Esto debe ser ajustado según el contexto, probablemente lo obtienes de algún lado
            fecha = self.date_picker.date()  # Obtener la fecha del QDateEdit
            print(f"Fecha seleccionada: {fecha.toString('yyyy-MM-dd')}")

            # Conexión a la base de datos
            cursor = self.db_connection.cursor()

            # Asegúrate de que la fecha esté en formato adecuado para SQL
            fecha_str = fecha.toString("yyyy-MM-dd")  # Formato para SQL
            print(f"Fecha en formato SQL: {fecha_str}")

            # Ejecutar la consulta SQL
            cursor.execute("""
                SELECT fecha_hora, corriente, potencia
                FROM lecturas
                WHERE artefacto_id = ? AND CAST(fecha_hora AS DATE) = ?
                ORDER BY fecha_hora
            """, (artefacto_id, fecha_str))

            rows = cursor.fetchall()
            print(f"Lecturas encontradas: {len(rows)}")  # Depuración para ver cuántos registros se obtienen

            if rows:
                # Actualizar la tabla con los datos obtenidos
                self.table.setRowCount(len(rows))
                for row, (fecha_hora, corriente, potencia) in enumerate(rows):
                    self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(fecha_hora)))
                    self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(corriente)))
                    self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(potencia)))
            else:
                print("No se encontraron lecturas para la fecha y artefacto seleccionados")
                # Mostrar un mensaje si no se encuentran lecturas
                QtWidgets.QMessageBox.warning(self, "Advertencia", "No se encontraron lecturas para la fecha seleccionada.")

        except Exception as e:
            print(f"Error al cargar las lecturas: {e}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Error al cargar las lecturas: {e}")

    def closeEvent(self, event):
        """Cerrar la conexión a la base de datos al cerrar el panel."""
        if self.db_connection:
            self.db_connection.close()
            print("Conexión a la base de datos cerrada.")
        super().closeEvent(event)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())
