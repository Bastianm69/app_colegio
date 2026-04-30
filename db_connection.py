# esta es la conexion a la base de datos en Neon #

import psycopg2

def obtener_conexion():
    try:
        # Aquí pegas el link largo que copiaste de la web de Neon
        # Debe tener tu usuario, tu contraseña y el host de Neon
        url_neon = "postgresql://neondb_owner:npg_g7mnR8wlOtMj@ep-dawn-scene-am8afuff-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
        
        # Conectamos usando la URL directa
        conn = psycopg2.connect(url_neon)
        return conn
    except Exception as e:
        print(f"🚨 Error al conectar con la base de datos en Neon: {e}")
        return None    
if __name__ == '__main__':
    print("Probando la conexión a Neon en la nube...")
    conexion_prueba = obtener_conexion()
    
    if conexion_prueba:
        print("✅ ¡ÉXITO TOTAL! Tu sistema está conectado a internet.")
        
        # Opcional: Hacemos una mini consulta para ver qué versión de PostgreSQL estamos usando
        cursor = conexion_prueba.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"🔧 Base de datos confirmada: {version[0]}")
        
        cursor.close()
        conexion_prueba.close()
    else:
        print("❌ Falló la conexión. Revisa que el enlace sea correcto y tenga tu contraseña.")
    

def registrar_auditoria_login(nombre_usuario, id_usuario, ip_direccion, exito, conn):
    """
    Llama al procedimiento almacenado para registrar si un intento de login 
    fue exitoso o fallido.
    """
    try:
        cur = conn.cursor()
        
        # Ejecutamos el SP usando CALL
        cur.execute(
            "CALL sp_registrar_intento_login(%s, %s, %s, %s)", 
            (nombre_usuario, id_usuario, ip_direccion, exito)
        )
        
        conn.commit()
        cur.close()
    except Exception as e:
        # Hacemos rollback por si falla, pero NO detenemos la app.
        # El usuario debe poder entrar aunque falle el registro de auditoría.
        conn.rollback()
        print(f"Error crítico en auditoría de login: {e}")