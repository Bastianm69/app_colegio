from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db_connection import obtener_conexion
from validaciones import validar_rut 
from db_registrar_docente import registrar_docente_db
from db_registrar_docente import obtener_todos_los_docentes, dar_de_baja_docente_db
from db_registrar_docente import obtener_docente_por_rut, actualizar_docente_db


# 1. Definición del Blueprint
admin_bp = Blueprint('admin_bp', __name__)

# ==============================================================================
# PANEL PRINCIPAL DEL ADMINISTRADOR
# ==============================================================================
@admin_bp.route('/admin')
def admin_panel():
    # Seguridad: Solo permitimos la entrada si es ADMIN y tiene sesión iniciada
    if 'user_id' not in session or session.get('rol') != 'ADMIN':
        return redirect(url_for('auth_bp.login'))
    
    nombre_admin = session.get('nombre_usuario', 'Administrador')
    return render_template('panel_admin.html', nombre_admin=nombre_admin)

# ==============================================================================
# MÓDULO: REGISTRAR NUEVO DOCENTE
# ==============================================================================
@admin_bp.route('/nuevo-docente', methods=['GET', 'POST'])
@admin_bp.route('/nuevo-docente', methods=['GET', 'POST'])
def nuevo_docente():
    if 'user_id' not in session or session.get('rol') != 'ADMIN':
        return redirect(url_for('auth_bp.login'))

    datos = {}

    if request.method == 'POST':
        print("\n" + ">>>" * 10)
        print("LOG: Inicio de solicitud POST en /nuevo-docente")
        
        # 1. Ver qué datos llegan del HTML
        datos = dict(request.form)
        print(f"LOG: Datos capturados: {datos}")
        
        # Validación del RUT
        rut_valido = validar_rut(datos.get('rut'))
        if not rut_valido:
            print(f"LOG: RUT inválido abortando: {datos.get('rut')}")
            flash("Error: El RUT ingresado no tiene un formato válido.", "error")
            return render_template('nuevo_docente.html', datos=datos)

        # Intento de conexión y registro
        conn = obtener_conexion()
        if conn:
            try:
                # 2. Llamada a la lógica que ya arreglamos antes
                print("LOG: Llamando a registrar_docente_db...")
                exito, mensaje = registrar_docente_db(datos, conn)
                
                print(f"LOG: Resultado DB: exito={exito}, mensaje={mensaje}")
                
                if exito:
                    flash(mensaje, "success")
                    return redirect(url_for('admin_bp.admin_panel'))
                else:
                    flash(mensaje, "error")
            except Exception as e:
                print(f"LOG: ERROR CRÍTICO: {str(e)}")
                flash(f"Error inesperado: {e}", "error")
            finally:
                conn.close()
                print("LOG: Conexión cerrada.")
        else:
            flash("Error técnico: No se pudo establecer conexión.", "error")
        
        print("<<<" * 10 + "\n")

    return render_template('nuevo_docente.html', datos=datos)

# ==============================================================================
# MÓDULO: VER DOCENTES
# ==============================================================================

@admin_bp.route('/ver-docentes')
def lista_docentes():
    conn = obtener_conexion()
    docentes = obtener_todos_los_docentes(conn)
    conn.close()
    return render_template('ver_docentes.html', docentes=docentes)


@admin_bp.route('/eliminar-docente/<rut>')
def eliminar_docente(rut):
    # Verificación básica de sesión
    if not session.get('user_id'):
        return redirect(url_for('auth_bp.login'))

    conn = obtener_conexion()
    exito, mensaje = dar_de_baja_docente_db(rut, conn)
    conn.close()
    
    # Después de cambiar el estado, volvemos a la lista para ver el cambio
    return redirect(url_for('admin_bp.lista_docentes'))

@admin_bp.route('/editar-docente/<rut>', methods=['GET', 'POST'])
def editar_docente(rut):
    conn = obtener_conexion()
    
    if request.method == 'POST':
        # Captura de datos desde el HTML
        datos_form = {
            'rut': rut,
            'email': request.form.get('email'),
            'nombres': request.form.get('nombres'),
            'apellido_paterno': request.form.get('apellido_paterno'),
            'apellido_materno': request.form.get('apellido_materno'),
            'especialidad_nivel': request.form.get('especialidad_nivel'),
            'fono': request.form.get('fono'),
            'calle_numero': request.form.get('calle_numero'),
            'comuna': request.form.get('comuna'),
            'region': request.form.get('region'),
            'codigo_postal': request.form.get('codigo_postal'),
            'detalles': request.form.get('detalles'),
            'grupo_sangre': request.form.get('grupo_sangre'),
            'discapacidad': request.form.get('discapacidad'),
            'alergias': request.form.get('alergias'),
            'enfermedades_cronicas': request.form.get('enfermedades_cronicas'),
            'medicamentos': request.form.get('medicamentos')
        }
        
        exito, msj = actualizar_docente_db(datos_form, conn)
        conn.close()
        
        if exito:
            # Redirige a la tabla para ver los cambios
            return redirect(url_for('admin_bp.lista_docentes'))
        else:
            return f"Error: {msj}"

    # Lógica para mostrar el formulario (GET)
    docente = obtener_docente_por_rut(conn, rut)
    conn.close()
    return render_template('editar_docente.html', d=docente)

# ==============================================================================
# MÓDULO: ASIGNAR CURSO (Preparado para el próximo SP)
# ==============================================================================
@admin_bp.route('/asignar-cursos')
def asignar_cursos_vista():
    # El guardia de seguridad plural que ya conocemos
    roles_usuario = session.get('roles', [])
    if 'user_id' not in session or 'ADMIN' not in roles_usuario:
        return redirect(url_for('auth_bp.login'))

    conn = obtener_conexion()
    cursos = []
    docentes = []

    if conn:
        try:
            cur = conn.cursor()
            
            # 1. Obtenemos los cursos y el nombre de su jefe actual (si tiene)
            query_cursos = """
                SELECT c.id_curso, c.nombre_curso, c.nivel, d.nombres, d.apellido_paterno, c.id_profesor_jefe
                FROM cursos c
                LEFT JOIN docentes d ON c.id_profesor_jefe = d.id_docente
                ORDER BY c.nivel, c.nombre_curso
            """
            cur.execute(query_cursos)
            cursos = cur.fetchall()

            # 2. Obtenemos la lista de todos los docentes para los select del HTML
            cur.execute("SELECT id_docente, nombres, apellido_paterno FROM docentes ORDER BY apellido_paterno")
            docentes = cur.fetchall()

        except Exception as e:
            print(f"Error al cargar vista de asignación: {e}")
        finally:
            cur.close()
            conn.close()

    return render_template('admin/asignar_cursos.html', cursos=cursos, docentes=docentes)

@admin_bp.route('/cursos')
def lista_cursos():
    return "dios escucha este programador"




