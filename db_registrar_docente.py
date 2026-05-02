from flask import session  
from werkzeug.security import generate_password_hash

def registrar_docente_db(datos, conn):
    try:
        cur = conn.cursor()
        print("   [DB_LOG]: Preparando parámetros para el SP...")
        
        # Sacamos el ID del administrador que está logueado desde la sesión de Flask
        admin_id = session.get('user_id') 

        # 2. VALIDACIÓN DE SEGURIDAD
        if admin_id is None:
            print("   [DB_LOG]: ❌ ERROR: No hay un administrador en sesión.")
            return False, "Error de sesión: Debe estar logueado como administrador."

        hash_pass = generate_password_hash(datos.get('password'))
        
        # 3. PARÁMETROS (Ahora admin_id sí existe y Python lo reconoce)
        params = (
            admin_id,                        # 1. p_admin_id (Quién crea)
            datos.get('usuario'),            # 2. p_nombre_usuario
            hash_pass,                       # 3. p_password_hash
            datos.get('email'),              # 4. p_email
            'DOCENTE',                       # 5. p_rol_nombre
            datos.get('rut'),                # 6. p_rut
            datos.get('nombres'),            # 7. p_nombres
            datos.get('apellido_paterno'),   # 8. p_ap_paterno
            datos.get('apellido_materno'),   # 9. p_ap_materno
            datos.get('especialidad_nivel'), # 10. p_especialidad_nivel
            datos.get('fono'),               # 11. p_fono
            datos.get('calle_numero'),       # 12. p_calle_num
            datos.get('comuna'),             # 13. p_comuna
            datos.get('region'),             # 14. p_region
            datos.get('codigo_postal'),      # 15. p_cod_postal
            datos.get('detalles'),           # 16. p_detalles_dir
            datos.get('grupo_sangre'),       # 17. p_sangre
            datos.get('discapacidad'),       # 18. p_discapacidad
            datos.get('alergias'),           # 19. p_alergias
            datos.get('enfermedades_cronicas'), # 20. p_enfermedades
            datos.get('medicamentos')        # 21. p_medicamentos
        )
        
        # 4. LA LLAMADA SQL (Con los 21 %s correspondientes)
        sql = """
            CALL sp_crear_perfil_docente_completo(
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        cur.execute(sql, params)
        conn.commit()
        cur.close()
        
        print("   [DB_LOG]: Registro y Log completados con éxito.")
        return True, "Docente registrado con éxito."
        
    except Exception as e:
        print(f"   [DB_LOG]: ❌ ERROR: {str(e)}")
        conn.rollback()
        return False, str(e)
    

def obtener_todos_los_docentes(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM fn_obtener_todos_los_docentes();")
    docentes = cur.fetchall()
    cur.close()
    return docentes

def obtener_docente_por_rut(conn, rut):
    """Llama a la función SQL para traer los datos del docente"""
    try:
        cur = conn.cursor()
        # Invocamos la función directamente
        cur.execute("SELECT * FROM fn_obtener_perfil_editar_docente(%s);", (rut,))
        docente = cur.fetchone()
        cur.close()
        return docente
    except Exception as e:
        print(f"   [DB_LOG]: ❌ Error al ejecutar fn_obtener_perfil_editar_docente: {str(e)}")
        return None

def dar_de_baja_docente_db(rut, conn):
    """Cambia el estado del docente a inactivo en la DB"""
    try:
        cur = conn.cursor()
        admin_id = session.get('user_id') # ID del admin en sesión
        
        # Ejecutamos el procedimiento de baja lógica
        cur.execute("CALL sp_dar_de_baja_docente(%s, %s)", (admin_id, rut))
        
        conn.commit()
        cur.close()
        return True, "Docente desactivado exitosamente."
    except Exception as e:
        if conn:
            conn.rollback()
        return False, str(e)
    
def actualizar_docente_db(datos, conn):
    """Llama al procedimiento almacenado para guardar los cambios"""
    try:
        cur = conn.cursor()
        admin_id = session.get('user_id') # Quien está editando
        
        # Preparamos los datos en el orden exacto del SP de arriba
        params = (
            admin_id,
            datos.get('rut'),
            datos.get('email'),
            datos.get('nombres'),
            datos.get('apellido_paterno'),
            datos.get('apellido_materno'),
            datos.get('especialidad_nivel'),
            datos.get('fono'),
            datos.get('calle_numero'),
            datos.get('comuna'),
            datos.get('region'),
            datos.get('codigo_postal'),
            datos.get('detalles'),
            datos.get('grupo_sangre'),
            datos.get('discapacidad'),
            datos.get('alergias'),
            datos.get('enfermedades_cronicas'),
            datos.get('medicamentos')
        )
        
        cur.execute("CALL sp_actualizar_perfil_docente_completo(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", params)
        conn.commit()
        cur.close()
        return True, "Cambios guardados con éxito"
    except Exception as e:
        if conn: conn.rollback()
        return False, str(e)