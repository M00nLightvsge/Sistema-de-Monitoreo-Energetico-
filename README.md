# Sistema de Monitoreo Energético en Tiempo Real Usando Arduino

Con sensores de corriente, creamos un sistema que monitoree el consumo eléctrico de diferentes dispositivos en una casa o edificio. Los datos se envían a un sistema SCADA para su análisis y control

## Objetivos

* Medir y registrar en tiempo real variables como la corriente y la potencia.
* Almacenar los datos en una base de datos centralizada.
* Detectar anomalías en el consumo energético con modelos de machine learning.
* Facilitar la descarga y visualización de datos, empoderando al usuario con herramientas intuitivas.
  
## Requisitos

* SQL SERVER MANAGDMENT STUDIO (Descargar la versión Developer aquí: https://www.microsoft.com/es-es/sql-server/sql-server-downloads , o realice una búsqueda en el navegador)
* Versión de Python 3.7 o superior
  
## Instalación

### Crear entorno virtual (Recomendado)

1. **Crear una carpeta donde alojará los archivos**  

2. **Abre tu terminal o línea de comandos**

3. **Crea el entorno virtual**
   
   ```bash
   python -m venv entorno
  
4. **Activa el entorno virtual**
   
   ```bash
   .\entorno\Scripts\activate

5. **Instala las dependencias**
   Una vez activado, instala las bibliotecas necesarias:

   ```bash
   pip install PyQt5 pyodbc pyqtgraph matplotlib pyserial joblib numpy

### Pasos de la instalación

1. **Clona el repositorio:**

   ```bash
   git clone https://github.com/M00nLightvsge/Sistema-de-Monitoreo-Energetico-.git

2. **Navega al directorio del proyecto:**

   ```bash
   cd prediccion-academica  

3. **Instala las dependencias:**

   ```bash
   pip install -r requirements.txt  

4. **Ejecuta la aplicación:**

   ```bash
   python app.py  


