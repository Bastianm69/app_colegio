import secrets
from datetime import datetime, timedelta

def crear_token_db(id_usuario, conexion):
    token_texto = secrets.token_hex(3).upper() 
    ahora = datetime.now()
    expiracion = ahora + timedelta(minutes=10)
    
    with conexion.cursor() as cur:
        try:
            # En vez de borrar, apagamos (marcamos como usados) cualquier token anterior 
            # que el usuario haya dejado abandonado
            cur.execute("UPDATE tokens_sesion SET usado = TRUE WHERE id_usuario = %s", (id_usuario,))
            
            # Insertamos el nuevo token (la BD le pondrá usado = FALSE por defecto)
            query = """
                INSERT INTO tokens_sesion (id_usuario, token, expira_en)
                VALUES (%s, %s, %s)
            """
            cur.execute(query, (id_usuario, token_texto, expiracion))
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
        # Añadimos la regla "AND usado = FALSE" a la búsqueda
        query = """
            SELECT id_token FROM tokens_sesion 
            WHERE id_usuario = %s AND token = %s AND expira_en > %s AND usado = FALSE
        """
        cur.execute(query, (id_usuario, token_ingresado, ahora))
        resultado = cur.fetchone()
        
        if resultado:
            id_token = resultado[0]
            # ¡AQUÍ ESTÁ LA MAGIA! En vez de DELETE, hacemos UPDATE para "quemar" el token
            cur.execute("UPDATE tokens_sesion SET usado = TRUE WHERE id_token = %s", (id_token,))
            conexion.commit()
            return True
            
        return False