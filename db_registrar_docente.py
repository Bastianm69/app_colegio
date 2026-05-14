from flask import session  
from werkzeug.security import generate_password_hash

def registrar_docente_db(datos, conn, asignaturas_seleccionadas):
    try:
        cur = conn.cursor()
        print("   [DB_LOG]: Preparando parámetros para el SP (incluyendo materias)...")
        
        # 1. Sacamos el ID del administrador (Solo para validar seguridad, NO se envía a la BD)
        admin_id = session.get('user_id') 

        # 2. VALIDACIÓN DE SEGURIDAD
        if admin_id is None:
            print("   [DB_LOG]: ❌ ERROR: No hay un administrador en sesión.")
            return False, "Error de sesión: Debe estar logueado como administrador."

        # Generar hash de la contraseña
        hash_pass = generate_password_hash(datos.get('password'))

        # 3. CONVERSIÓN DE ASIGNATURAS A ARRAY DE ENTEROS
        materias_array = [int(id_asig) for id_asig in asignaturas_seleccionadas] if asignaturas_seleccionadas else []
        
        # 4. PARÁMETROS ACTUALIZADOS (¡21 en total, tal como pide la BD!)
        params = (
            datos.get('usuario'),            # 1: p_usuario
            hash_pass,                       # 2: p_password
            datos.get('email'),              # 3: p_email
            3,                               # 4: p_id_rol (Enviamos el NÚMERO 2 que representa al Rol Docente)
            datos.get('rut'),                # 5: p_rut
            datos.get('nombres'),            # 6: p_nombres
            datos.get('apellido_paterno'),   # 7: p_ape_p
            datos.get('apellido_materno'),   # 8: p_ape_m
            datos.get('especialidad_nivel'), # 9: p_especialidad
            datos.get('fono'),               # 10: p_fono
            datos.get('calle_numero'),       # 11: p_calle
            datos.get('comuna'),             # 12: p_comuna
            datos.get('region'),             # 13: p_region
            datos.get('codigo_postal'),      # 14: p_cod_postal
            datos.get('detalles'),           # 15: p_detalles
            datos.get('grupo_sangre'),       # 16: p_grupo_sangre
            datos.get('discapacidad'),       # 17: p_discapacidad
            datos.get('alergias'),           # 18: p_alergias
            datos.get('enfermedades_cronicas'), # 19: p_cronicas
            datos.get('medicamentos'),       # 20: p_medicamentos
            materias_array                   # 21: p_materias (INT[])
        )
        
        # 5. LA LLAMADA SQL (Nombre correcto y exactamente 21 placeholders '%s')
        sql = """
            CALL public.sp_registrar_docente_completo(
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        cur.execute(sql, params)
        conn.commit()
        cur.close()
        
        print(f"   [DB_LOG]: Registro completado. {len(materias_array)} materias vinculadas.")
        return True, "Docente registrado y materias vinculadas con éxito."
        
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