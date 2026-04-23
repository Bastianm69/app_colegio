def crear_token_db(id_usuario, conn):
    """
    Llama al procedimiento almacenado 'fn_generar_token_seguridad' en la base de datos.
    Este procedimiento genera el código de 6 dígitos, lo guarda en 'tokens_sesion' 
    con 10 minutos de validez y lo devuelve para ser enviado por correo.
    """
    try:
        cur = conn.cursor()
        
        # Invocamos la función de la base de datos (Stored Procedure)
        cur.execute("SELECT fn_generar_token_seguridad(%s)", (id_usuario,))
        
        resultado = cur.fetchone()
        # Capturamos el token generado por el SP
        token_generado = resultado[0] if resultado else None
        
        conn.commit()
        cur.close()
        
        return token_generado
    except Exception as e:
        # Registro de error en consola para depuración
        print(f"Error al invocar SP fn_generar_token_seguridad: {e}")
        return None

def verificar_token_db(id_usuario, token_ingresado, conn):
    """
    Llama al procedimiento almacenado 'fn_verificar_token_seguridad' en la base de datos.
    Este procedimiento valida si el token es correcto, si no ha expirado y si no ha sido 
    usado. Si es válido, lo marca como usado automáticamente.
    """
    try:
        cur = conn.cursor()
        
        # Invocamos la función de verificación de la base de datos
        cur.execute("SELECT fn_verificar_token_seguridad(%s, %s)", (id_usuario, token_ingresado))
        
        resultado = cur.fetchone()
        # El SP de PostgreSQL devuelve un booleano (True/False) directamente
        es_valido = resultado[0] if resultado else False
        
        conn.commit()
        cur.close()
        
        return es_valido
    except Exception as e:
        # Registro de error en consola para depuración
        print(f"Error al invocar SP fn_verificar_token_seguridad: {e}")
        return False