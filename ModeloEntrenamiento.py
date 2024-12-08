from sklearn.ensemble import IsolationForest
import numpy as np
import joblib
from Interfaz import get_connection  

# Mensaje de inicio
print("Iniciando el script de entrenamiento del modelo de anomalías...")

try:
    # Conectar a la base de datos
    conn = get_connection()
    print("Conexión a la base de datos exitosa.")
except Exception as e:
    print(f"Error de conexión: {e}")
    exit()

# Crear un cursor para ejecutar las consultas
cursor = conn.cursor()

# Obtener las lecturas de la tabla Lecturas
try:
    cursor.execute("""
        SELECT corriente, potencia 
        FROM Lecturas 
        WHERE artefacto_id IS NOT NULL
    """)
    rows = cursor.fetchall()
    print(f"Datos obtenidos de la tabla Lecturas: {len(rows)} filas.")
except Exception as e:
    print(f"Error al obtener los datos: {e}")
    exit()

# Verificar si se obtuvieron datos
if not rows:
    print("No se encontraron datos en la tabla Lecturas.")
    exit()

# Convertir las lecturas a un formato adecuado para el modelo
try:
    historical_data = np.array([[row.corriente, row.potencia] for row in rows])
    print(f"Datos convertidos para el modelo: {historical_data.shape[0]} lecturas.")
except Exception as e:
    print(f"Error al convertir los datos: {e}")
    exit()

# Entrenar el modelo de Isolation Forest
try:
    model = IsolationForest(contamination=0.1)  # Ajusta el porcentaje de anomalías esperado
    model.fit(historical_data)
    print("Modelo entrenado exitosamente.")
except Exception as e:
    print(f"Error durante el entrenamiento del modelo: {e}")
    exit()

# Guardar el modelo entrenado en un archivo
try:
    # Cambia la ruta si quieres guardar el archivo en una ubicación específica
    filename = 'modelo.pkl'
    joblib.dump(model, filename)
    print(f"Modelo guardado correctamente en '{filename}'.")
except Exception as e:
    print(f"Error al guardar el modelo: {e}")
    exit()

# Cerrar la conexión a la base de datos
cursor.close()
conn.close()
print("Conexión a la base de datos cerrada.")
