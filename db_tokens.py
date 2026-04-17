import secrets
from datetime import datetime, timedelta

def crear_token_db(id_usuario, conexion):
    # Generamos código de 6 caracteres
    token_texto = secrets.token_hex(3).upper() 
    ahora = datetime.now()
    expiracion = ahora + timedelta(minutes=10)
    
    with conexion.cursor() as cur:
        try:
            # Limpiamos tokens viejos para que no se acumulen
            cur.execute("DELETE FROM tokens_sesion WHERE id_usuario = %s", (id_usuario,))
            
            # Insertamos según las columnas de tu imagen en pgAdmin
            query = """
                INSERT INTO tokens_sesion (id_usuario, token, creado_en, expira_en)
                VALUES (%s, %s, %s, %s)
            """
            cur.execute(query, (id_usuario, token_texto, ahora, expiracion))
            conexion.commit()
            return token_texto
        except Exception as e:
            conexion.rollback()
            print(f"Error DB al crear token: {e}")
            return None

def verificar_token_db(id_usuario, token_ingresado, conexion):
    ahora = datetime.now()
    token_ingresado = token_ingresado.strip().upper()
    
    with conexion.cursor() as cur:
        query = """
            SELECT id_token FROM tokens_sesion 
            WHERE id_usuario = %s AND token = %s AND expira_en > %s
        """
        cur.execute(query, (id_usuario, token_ingresado, ahora))
        resultado = cur.fetchone()
        
        if resultado:
            # Si es correcto, borramos para que sea de un solo uso
            cur.execute("DELETE FROM tokens_sesion WHERE id_usuario = %s", (id_usuario,))
            conexion.commit()
            return True
        return False