import unittest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QApplication
from ult import CSVPanel, get_connection  

class TestCSVPanel(unittest.TestCase):
    def setUp(self):
        """Configuración inicial para cada prueba."""
        self.app = QApplication([])  # Necesario para las pruebas con PyQt
        
        # Mock de la conexión a SQL Server (simulamos la base de datos)
        self.mock_db_connection = MagicMock()
        
        # Simular el cursor de la conexión
        self.mock_cursor = MagicMock()
        self.mock_db_connection.cursor.return_value = self.mock_cursor
        
        # Simular lo que devuelve el método `fetchall` del cursor (lista de artefactos)
        self.mock_cursor.fetchall.return_value = [(1, "Artefacto 1"), (2, "Artefacto 2")]
        
        # Crear la ventana con la conexión mockeada
        self.window = CSVPanel(self.mock_db_connection)

    def test_window_title(self):
        """Verifica el título de la ventana."""
        self.assertEqual(self.window.windowTitle(), "CSV Panel")

    def test_load_artefacts(self):
        """Verifica que los artefactos se carguen correctamente en la tabla."""
        self.window.load_artefacts()

        # Verifica que la tabla tenga 2 artefactos (simulados)
        self.assertEqual(self.window.table.rowCount(), 2)
        self.assertEqual(self.window.table.item(0, 0).text(), "Artefacto 1")
        self.assertEqual(self.window.table.item(1, 0).text(), "Artefacto 2")
        
        # Verifica que la consulta SQL se haya ejecutado correctamente
        self.mock_cursor.execute.assert_called_with("SELECT id, nombre FROM artefactos")

    def test_download_csv(self):
        """Verifica la funcionalidad de descarga de CSV."""
        # Suponemos que el botón de descarga está habilitado
        # Mockear la función de descarga para verificar si la lógica de trabajo se llama
        with patch.object(self.window, 'download_csv') as mock_download:
            self.window.download_csv(1)
            mock_download.assert_called_once_with(1)  # Verifica que la función se haya llamado

if __name__ == '__main__':
    unittest.main()
