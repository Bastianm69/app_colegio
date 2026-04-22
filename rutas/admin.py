from flask import Blueprint, render_template, request, redirect, url_for, session
from db_connection import obtener_conexion
from validaciones import validar_rut 

# 1. Definición del Blueprint
admin_bp = Blueprint('admin_bp', __name__)

# ==============================================================================
# PANEL PRINCIPAL DEL ADMINISTRADOR
# ==============================================================================
@admin_bp.route('/admin')
def admin_panel():
    # Seguridad: Verificar que sea un administrador
    if 'user_id' not in session or session.get('rol') != 'ADMIN':
        return redirect(url_for('auth_bp.login'))
    
    nombre_admin = session.get('nombre_usuario', 'nombre_admin')
    
    # ¡Súper limpio! El HTML ya lee el nombre directamente de la memoria de Flask
    return render_template('panel_admin.html', nombre_admin=nombre_admin) # type: ignore

# ==============================================================================
# MÓDULO: REGISTRAR NUEVO DOCENTE
# ==============================================================================
@admin_bp.route('/nuevo-docente', methods=['GET', 'POST'])
def nuevo_docente():
    # Seguridad: Verificar sesión de administrador
    if 'user_id' not in session or session.get('rol') != 'ADMIN':
        return redirect(url_for('auth_bp.login'))

    mensaje = None
    color = "red"
    
    # Creamos un diccionario vacío al inicio por si solo entran a ver la página
    datos = {}

    if request.method == 'POST':
        # Convertimos los datos del formulario en un diccionario modificable
        f = request.form 
        datos = dict(f) 
        
        # Validamos el RUT antes de tocar la base de datos
        if not validar_rut(f.get('rut')):
            datos['rut'] = '' 
            return render_template('nuevo_docente.html', msg="Error: El RUT ingresado es inválido.", color="red", datos=datos)

        conn = obtener_conexion()
        if conn:
            try:
                cur = conn.cursor()
                
                # LA GRAN CONSULTA: 3 inserciones + unión final + RETORNO de ID
                query = """
                    WITH ins_usuario AS (
                        INSERT INTO usuarios (nombre_usuario, password_hash, email, id_rol, activo)
                        VALUES (%s, %s, %s, 2, true) RETURNING id_usuario
                    ),
                    ins_medico AS (
                        INSERT INTO datos_medicos (grupo_sangre, alergias, enfermedades_cronicas, medicamentos, discapacidad)
                        VALUES (%s, %s, %s, %s, %s) RETURNING id_dato_medico
                    ),
                    ins_direccion AS (
                        INSERT INTO direcciones (calle_numero, comuna, region, codigo_postal, detalles)
                        VALUES (%s, %s, %s, %s, %s) RETURNING id_direccion
                    )
                    INSERT INTO docentes (
                        id_usuario, id_dato_medico, id_direccion, 
                        rut, nombres, apellido_paterno, apellido_materno, 
                        especialidad_nivel, fono
                    )
                    SELECT 
                        u.id_usuario, m.id_dato_medico, d.id_direccion, 
                        %s, %s, %s, %s, %s, %s
                    FROM ins_usuario u, ins_medico m, ins_direccion d
                    RETURNING id_docente;  
                """
                
                cur.execute(query, (
                    # Datos para ins_usuario
                    f.get('nombre_usuario'), f.get('password'), f.get('email'),
                    
                    # Datos para ins_medico
                    f.get('grupo_sangre'), f.get('alergias'), f.get('enfermedades_cronicas'), 
                    f.get('medicamentos'), f.get('discapacidad'),
                    
                    # Datos para ins_direccion
                    f.get('calle_numero'), f.get('comuna'), f.get('region'), 
                    f.get('codigo_postal'), f.get('detalles'),
                    
                    # Datos personales para docentes
                    f.get('rut'), f.get('nombres'), f.get('apellido_paterno'), 
                    f.get('apellido_materno'), f.get('especialidad_nivel'), f.get('fono')
                ))
                
                # REGISTRO DE AUDITORÍA (LOG)
                id_nuevo_docente = cur.fetchone()[0]
                id_admin_actual = session['user_id'] 
                detalles_log = f"Se registró al docente {f.get('nombres')} {f.get('apellido_paterno')} (RUT: {f.get('rut')})"
                
                query_log = """
                    INSERT INTO logs_actividad (id_usuario, accion, tabla_afectada, registro_id, detalles)
                    VALUES (%s, 'CREAR', 'docentes', %s, %s)
                """
                cur.execute(query_log, (id_admin_actual, id_nuevo_docente, detalles_log))
                
                # Confirmamos que TODO se guarde
                conn.commit()
                mensaje = "¡Docente registrado con éxito (Historial de actividad guardado)!"
                color = "green"
                
                # Vaciamos los datos tras el éxito para limpiar el formulario
                datos = {}
            
            except Exception as e:
                conn.rollback()
                error_msg = str(e)
                
                # Manejo de errores para vaciar solo el campo incorrecto
                if "docentes_rut_key" in error_msg:
                    mensaje = "Error: Este RUT ya pertenece a otro profesor en el sistema."
                    datos['rut'] = '' 
                    
                elif "usuarios_nombre_usuario_key" in error_msg:
                    mensaje = "Error: El nombre de usuario ya está ocupado. Intenta con otro."
                    datos['nombre_usuario'] = '' 
                    
                elif "usuarios_email_key" in error_msg:
                    mensaje = "Error: Este correo electrónico ya está registrado."
                    datos['email'] = '' 
                    
                else:
                    mensaje = f"Error en el registro: {e}"
            finally:
                cur.close()
                conn.close()

    return render_template('nuevo_docente.html', msg=mensaje, color=color, datos=datos)

@admin_bp.route('/asignar-curso', methods=['GET', 'POST'])
def asignar_curso():
    if 'user_id' not in session or session.get('rol') != 'ADMIN':
        return redirect(url_for('auth_bp.login'))

    mensaje = None
    color = "red"
    docentes = []
    cursos = []

    conn = obtener_conexion()
    if conn:
        try:
            cur = conn.cursor()
            
            # Traemos la lista de profes para el <select>
            cur.execute("SELECT id_docente, nombres, apellido_paterno FROM docentes ORDER BY nombres ASC")
            docentes = cur.fetchall()

            # Traemos la lista de cursos para el <select>
            cur.execute("SELECT id_curso, nombre_curso FROM cursos ORDER BY nombre_curso ASC")
            cursos = cur.fetchall()

            if request.method == 'POST':
                id_docente = request.form.get('id_docente')
                id_curso = request.form.get('id_curso')
                
                # Guardamos la relación en la tabla puente
                cur.execute("""
                    INSERT INTO curso_docente (id_docente, id_curso, periodo)
                    VALUES (%s, %s, '2024')
                """, (id_docente, id_curso))
                
                conn.commit()
                mensaje = "✅ El docente fue asignado al curso correctamente."
                color = "green"

        except Exception as e:
            if conn: conn.rollback()
            mensaje = f"Error: {e}"
        finally:
            cur.close()
            conn.close()

    return render_template('asignar_curso.html', docentes=docentes, cursos=cursos, msg=mensaje, color=color)

