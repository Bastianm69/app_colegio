import secrets
from datetime import datetime, timedelta

def crear_token_db(id_usuario, conexion):
    # Generamos un código de 6 caracteres en mayúsculas
    token_texto = secrets.token_hex(3).upper() 
    ahora = datetime.now()
    expiracion = ahora + timedelta(minutes=10)
    
    with conexion.cursor() as cur:
        try:
            query = """
                INSERT INTO tokens_sesion (id_usuario, token, creado_en, expira_en)
                VALUES (%s, %s, %s, %s)
            """
            cur.execute(query, (id_usuario, token_texto, ahora, expiracion))
            conexion.commit()
            return token_texto
        except Exception as e:
            conexion.rollback()
            print(f"Error DB: {e}")
            return None

def verificar_token_db(id_usuario, token_ingresado, conexion):
    ahora = datetime.now()
    with conexion.cursor() as cur:
        # Buscamos si existe y no ha expirado
        query = """
            SELECT id_token FROM tokens_sesion 
            WHERE id_usuario = %s AND token = %s AND expira_en > %s
        """
        cur.execute(query, (id_usuario, token_ingresado, ahora))
        resultado = cur.fetchone()
        
        if resultado:
            # Limpiamos los tokens usados para ese usuario
            cur.execute("DELETE FROM tokens_sesion WHERE id_usuario = %s", (id_usuario,))
            conexion.commit()
            return True
        return False