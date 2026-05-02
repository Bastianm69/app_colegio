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
        print(f"LOG: Datos capturados del formulario: {datos}")
        
        # 2. Verificar el RUT
        rut_valido = validar_rut(datos.get('rut'))
        print(f"LOG: ¿RUT válido? {'SÍ' if rut_valido else 'NO'} ({datos.get('rut')})")
        
        if not rut_valido:
            print("LOG: Abortando por RUT inválido.")
            flash("Error: El RUT ingresado no tiene un formato válido.", "error")
            return render_template('nuevo_docente.html', datos=datos)

        # 3. Intento de conexión
        print("LOG: Intentando conectar a la base de datos...")
        conn = obtener_conexion()
        
        if conn:
            print("LOG: Conexión establecida con éxito.")
            try:
                # 4. Llamada a la lógica de BD
                print("LOG: Llamando a la función registrar_docente_db...")
                exito, mensaje = registrar_docente_db(datos, conn)
                
                print(f"LOG: Resultado de la función DB: exito={exito}, mensaje={mensaje}")
                
                conn.close()
                print("LOG: Conexión cerrada.")
                
                if exito:
                    print("LOG: Redirigiendo al panel por éxito.")
                    flash(mensaje, "success")
                    return redirect(url_for('admin_bp.admin_panel'))
                else:
                    print(f"LOG: Error reportado por la lógica de BD: {mensaje}")
                    flash(mensaje, "error")
            except Exception as e:
                print(f"LOG: ¡ERROR CRÍTICO inesperado en la ruta!: {str(e)}")
                flash(f"Error inesperado: {e}", "error")
        else:
            print("LOG: ERROR - No se pudo obtener la conexión (conn es None)")
            flash("Error técnico: No se pudo establecer conexión con el servidor.", "error")
        
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
@admin_bp.route('/asignar-curso/<rut>')
def asignar_curso(rut):
    # Por ahora solo retornamos un mensaje para que no de error
    return redirect(url_for('admin_bp.asignar_curso', rut=rut))

@admin_bp.route('/cursos')
def lista_cursos():
    return "dios escucha este programador"




