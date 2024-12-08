import unittest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from ult import LoginWindow  

class TestLoginWindow(unittest.TestCase):
    def setUp(self):
        """Configuración inicial para cada prueba."""
        print("Setting up the test...")
        self.app = QApplication([])  # Necesario para las pruebas con PyQt
        self.window = LoginWindow()  # Creamos una instancia de la ventana de inicio de sesión

    def test_window_title(self):
        """Verifica el título de la ventana."""
        print("Verifying window title...")
        self.assertEqual(self.window.windowTitle(), "Inicio de Sesión")

    def test_login_successful(self):
        """Verifica que al ingresar un usuario y contraseña correctos se muestre el mensaje de bienvenida."""
        print("Testing login with valid credentials...")
        self.window.user_input.setText("testuser")  # Usuario simulado
        self.window.pass_input.setText("password")  # Contraseña simulada

        # Llamamos a la función para intentar iniciar sesión
        self.window.attempt_login()

        # Usamos QTimer para esperar el tiempo necesario para que la interfaz se actualice
        QTimer.singleShot(200, self.verify_login_successful)

    def verify_login_successful(self):
        """Verifica que el mensaje de bienvenida esté visible después de un inicio de sesión exitoso."""
        # Verifica que el mensaje de bienvenida sea visible
        self.assertTrue(self.window.welcome_message_label.isVisible())
        self.assertEqual(self.window.welcome_message_label.text(), "Bienvenido(a), testuser!")

    def test_login_failure(self):
        """Verifica que si las credenciales son incorrectas, se muestre un mensaje de error."""
        print("Testing login with invalid credentials...")
        self.window.user_input.setText("wronguser")
        self.window.pass_input.setText("wrongpassword")

        # Llamamos a la función para intentar iniciar sesión con credenciales incorrectas
        self.window.attempt_login()

        # Usamos QTimer para esperar el tiempo necesario para que la interfaz se actualice
        QTimer.singleShot(200, self.verify_login_failure)

    def verify_login_failure(self):
        """Verifica que el mensaje de error esté visible después de un intento fallido de inicio de sesión."""
        # Verificamos que el mensaje de error esté visible
        self.assertTrue(self.window.error_label.isVisible())
        self.assertEqual(self.window.error_label.text(), "Usuario y/o contraseña incorrecto(s)")

if __name__ == '__main__':
    unittest.main()
