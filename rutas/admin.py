from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db_connection import obtener_conexion
from validaciones import validar_rut 

# IMPORTANTE: Asegúrate de que este archivo 'db_usuarios.py' exista 
# con la función 'registrar_docente_db' que creamos antes.
from db_usuarios import registrar_docente_db 

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
# MÓDULO: ASIGNAR CURSO (Preparado para el próximo SP)
# ==============================================================================
@admin_bp.route('/asignar-curso', methods=['GET', 'POST'])
def asignar_curso():
    if 'user_id' not in session or session.get('rol') != 'ADMIN':
        return redirect(url_for('auth_bp.login'))

    # Aquí iría la lógica para cargar docentes y cursos desde la BD para los selects
    docentes = []
    cursos = []

    if request.method == 'POST':
        # Pendiente: Implementación con sp_asignar_docente_curso
        flash("Funcionalidad en desarrollo: Conectando con Stored Procedure...", "info")

    return render_template('asignar_curso.html', docentes=docentes, cursos=cursos)