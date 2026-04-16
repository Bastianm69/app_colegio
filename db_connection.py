import psycopg2
import os

# Obligamos a PostgreSQL a hablar en inglés básico para evitar 
# las comillas especiales del idioma español que rompen Windows.
os.environ['LC_MESSAGES'] = 'C'

def obtener_conexion():
    try:
        conexion = psycopg2.connect(
            host="localhost",
            database="colegio_bd",
            user="postgres",
            password="Bastymatta12",
            port="5432"
        )
        print("✅ ¡CONECTADO DIRECTAMENTE A POSTGRESQL!")
        return conexion
    except Exception as e:
        # Usamos repr(e) para imprimir el error en su formato crudo.
        # Esto GARANTIZA que Python no colapse al leer caracteres raros.
        print(f"❌ Error real devuelto: {repr(e)}")
        return None