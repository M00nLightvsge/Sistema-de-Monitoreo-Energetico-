# Sistema de Monitoreo Energético en Tiempo Real Usando Arduino

Con sensores de corriente, creamos un sistema que monitoree el consumo eléctrico de diferentes dispositivos en una casa o edificio. Los datos se envían a un sistema SCADA para su análisis y control

## Objetivos

* Medir y registrar en tiempo real variables como la corriente y la potencia.
* Almacenar los datos en una base de datos centralizada.
* Detectar anomalías en el consumo energético con modelos de machine learning.
* Facilitar la descarga y visualización de datos, empoderando al usuario con herramientas intuitivas.
  
## Requisitos

* SQL SERVER MANAGDMENT STUDIO (Descargar la versión Developer aquí: https://www.microsoft.com/es-es/sql-server/sql-server-downloads , o realice una búsqueda en el navegador)
* ODBC Driver for SQL Server (Descargar Microsoft ODBC Driver 18 for SQL Server (x64) aquí: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server?view=sql-server-ver16 o realice una búsqueda en el navegador del drive correspondiente)
* Versión de Python 3.7 o superior

## Instalación de la Base de Datos (DataBase)

Al momento de clonar el repositorio visualice el archivo o descarguelo directamente aquí en GitHub, el nombre del archivo es DataBaseProject.bak

1. Abre SQL Server Management Studio.
2. Conéctate al servidor donde quieres restaurar la base de datos.
3. Haz clic derecho en "Databases" y selecciona "Restore Database".
4. En el cuadro de diálogo, selecciona "Device" y luego "Browse" para localizar el archivo DataBaseProject.bak.
5. Selecciona el archivo de respaldo y haz clic en OK.
6. Asegúrate de elegir la base de datos de destino y haz clic en OK para restaurar.

## Instalación de la Interfaz

Revisar el codigo para realizar los cambios correspondientes en las direcciones de las imágenes y base de datos.

### Crear entorno virtual (Recomendado)

1. **Crear una carpeta donde alojará los archivos**  

2. **Abre tu terminal o línea de comandos**

3. **Crea el entorno virtual**
   
   ```bash
   python -m venv entorno
  
4. **Activa el entorno virtual**
   
   ```bash
   .\entorno\Scripts\activate

5. **Instala las dependencias, previamente activado el entorno**

   ```bash
   pip install PyQt5 pyodbc pyqtgraph matplotlib pyserial joblib numpy

### Pasos de la instalación

Dentro de la carpeta del entorno virtual creado previamente, y en el codigo 

1. **Clona el repositorio:**

   ```bash
   git clone https://github.com/M00nLightvsge/Sistema-de-Monitoreo-Energetico-.git

2. **Navega al directorio del proyecto:**

   ```bash
   cd Sistema-de-Monitoreo-Energetico-  

3. **Ejecuta la aplicación:**

   ```bash
   python Interfaz.py  

Documentación: [Descargar PDF](./DocumentacionFinal.pdf)

