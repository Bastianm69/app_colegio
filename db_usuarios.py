from werkzeug.security import generate_password_hash

def registrar_docente_db(datos, conn):
    try:
        cur = conn.cursor()
        print("   [DB_LOG]: Preparando parámetros para el SP...")
        
        hash_pass = generate_password_hash(datos.get('password'))
        
        params = (
            datos.get('usuario'), hash_pass, datos.get('email'), 'DOCENTE',
            datos.get('rut'), datos.get('nombres'), datos.get('apellidos'), datos.get('especialidad')
        )
        print(f"   [DB_LOG]: Parámetros listos: {params}")
        
        print("   [DB_LOG]: Ejecutando CALL sp_crear_perfil_docente...")
        cur.execute("CALL sp_crear_perfil_docente(%s, %s, %s, %s, %s, %s, %s, %s)", params)
        
        print("   [DB_LOG]: Ejecutando COMMIT...")
        conn.commit()
        
        cur.close()
        print("   [DB_LOG]: Registro completado sin errores.")
        return True, "Docente registrado con éxito."
        
    except Exception as e:
        print(f"   [DB_LOG]: ❌ ERROR dentro de registrar_docente_db: {str(e)}")
        conn.rollback()
        return False, str(e)