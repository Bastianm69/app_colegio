# Esto es para llamar el sp en la base de datos y validamos el rut #

from db_connection import obtener_conexion  

def validar_rut(rut):
    """
    Valida un RUT chileno llamando a la función fn_validar_rut en PostgreSQL.
    """
    try:
        # Abrimos la conexión a la base de datos
        with obtener_conexion() as conn:
            with conn.cursor() as cur:
                
                # Ejecutamos la función pasando el RUT que llegó como parámetro (%s)
                cur.execute("SELECT fn_validar_rut(%s)", (rut,))
                
                # Rescatamos la respuesta (retornará True o False)
                resultado = cur.fetchone()
                
                if resultado:
                    return resultado[0] # Retorna True si es válido, False si no
                else:
                    return False
                    
    except Exception as e:
        # Si la base de datos falla, imprimimos el error y por seguridad decimos que es inválido
        print(f"Error al validar RUT en la BD: {e}")
        return False