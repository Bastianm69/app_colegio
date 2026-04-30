# son las rutas relacionadas con la autenticación 

from flask import Blueprint, flash, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash # Importación para validar contraseñas seguras

# Importamos nuestras propias funciones desde otros archivos del proyecto
from db_connection import obtener_conexion
from db_tokens import crear_token_db, verificar_token_db # Funciones para el código 2FA
from mailer import enviar_correo_autorizacion # Función para enviar el email

# 1. Creamos el Blueprint para la Autenticación
auth_bp = Blueprint('auth_bp', __name__)

# --- FUNCIONES AUXILIARES ---

def cambiar_password_db(id_usuario, password_plana, conn):
    """
    Recibe la contraseña nueva escrita por el usuario, la encripta 
    y llama al SP para guardarla en la base de datos.
    """
    try:
        # 1. ¡CRÍTICO! Encriptamos la contraseña ANTES de tocar la base de datos
        nuevo_hash = generate_password_hash(password_plana)
        
        cur = conn.cursor()
        
        # 2. Llamamos al SP pasándole el ID y la contraseña ya encriptada (Hash)
        cur.execute("CALL sp_cambiar_password(%s, %s)", (id_usuario, nuevo_hash))
        
        # 3. Guardamos los cambios
        conn.commit()
        cur.close()
        
        return True 
        
    except Exception as e:
        conn.rollback() 
        print(f"Error al cambiar la contraseña en la BD: {e}")
        return False


# --- RUTAS DE LA APLICACIÓN ---

@auth_bp.route('/')
def index():
    return redirect(url_for('auth_bp.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None 

    if request.method == 'POST':
        usuario_f = request.form.get('usuario')
        password_f = request.form.get('password')
        
        # Lógica de IP Real
        ip_cliente = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_cliente and ',' in ip_cliente:
            ip_cliente = ip_cliente.split(',')[0].strip()

        conn = obtener_conexion()
        if conn:
            try: 
                cur = conn.cursor()
                
                # Búsqueda usando la función de la BD
                cur.callproc('fn_obtener_datos_login', (usuario_f,))
                user_found = cur.fetchone()

                # Validamos contraseña con el hash
                if user_found and check_password_hash(user_found[4], password_f):
                    id_usuario, nombre_u, rol, email_docente = user_found[:4]
                    
                    session['pre_login_id'] = id_usuario
                    session['pre_login_rol'] = rol
                    session['pre_login_nombre'] = nombre_u 
                    
                    cur.execute("CALL sp_registrar_intento_login(%s, %s, %s, %s)", 
                                (usuario_f, id_usuario, ip_cliente, True))
                    conn.commit() 

                    if not email_docente:
                        error = "Tu cuenta no tiene un correo registrado."
                    else:
                        token = crear_token_db(id_usuario, conn)
                        # Enviamos correo de LOGIN (es_recuperacion por defecto es False)
                        if token and enviar_correo_autorizacion(email_docente, token):
                            return redirect(url_for('auth_bp.verificar')) 
                        else:
                            error = "Error al enviar el correo de seguridad."
                else:
                    id_para_auditoria = user_found[0] if user_found else None
                    cur.execute("CALL sp_registrar_intento_login(%s, %s, %s, %s)", 
                                (usuario_f, id_para_auditoria, ip_cliente, False))
                    conn.commit()
                    error = "Usuario o contraseña incorrectos."
                
                cur.close()
                conn.close()
                
            except Exception as e:
                error = f"Error en la base de datos: {e}"
        else:
            error = "No hay conexión con la base de datos."
    
    return render_template('login.html', error=error)


@auth_bp.route('/verificar', methods=['GET', 'POST'])
def verificar():
    if 'pre_login_id' not in session:
        return redirect(url_for('auth_bp.login'))

    error = None
    if request.method == 'POST':
        codigo_web = request.form.get('codigo')
        user_id = session['pre_login_id']
        rol = session['pre_login_rol']
        
        conn = obtener_conexion()
        es_codigo_valido = verificar_token_db(user_id, codigo_web, conn)
        conn.close()
        
        if es_codigo_valido:
            session['user_id'] = user_id
            session['rol'] = rol
            session['nombre_usuario'] = session.pop('pre_login_nombre', 'Administrador')
            
            session.pop('pre_login_id', None)
            session.pop('pre_login_rol', None)
            
            if rol == 'ADMIN':
                return redirect(url_for('admin_bp.admin_panel'))
            else:
                return redirect(url_for('docente_bp.panel_docente'))
        else:
            error = "Código incorrecto o expirado."

    return render_template('verificar.html', error=error)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth_bp.login'))


@auth_bp.route('/recuperar_clave', methods=['GET', 'POST'])
def recuperar_clave():
    if request.method == 'POST':
        email_ingresado = request.form.get('email')
        
        conn = obtener_conexion()
        if conn:
            try:
                cur = conn.cursor()
                cur.callproc('fn_obtener_usuario_por_email', (email_ingresado,))
                resultado = cur.fetchone()
                
                if resultado and resultado[0]:
                    id_usuario = resultado[0]
                    token = crear_token_db(id_usuario, conn)
                    
                    # ENVIAMOS EL CORREO INDICANDO QUE ES RECUPERACIÓN
                    if token:
                        enviar_correo_autorizacion(email_ingresado, token, es_recuperacion=True)
                        session['reset_id_usuario'] = id_usuario
                
                cur.close()
                conn.close()
                
            except Exception as e:
                print(f"Error en recuperación: {e}")

        # Bandera de acceso para el Paso 2
        session['permitir_paso_2'] = True
        flash("Si el correo está en nuestros registros, recibirás un código de 6 dígitos con instrucciones.", "success")
        return redirect(url_for('auth_bp.restablecer_clave'))
        
    return render_template('recuperar_clave.html')


@auth_bp.route('/restablecer_clave', methods=['GET', 'POST'])
def restablecer_clave():
    if not session.get('permitir_paso_2'):
        return redirect(url_for('auth_bp.recuperar_clave'))

    error = None
    if request.method == 'POST':
        codigo_web = request.form.get('codigo')
        nueva_clave = request.form.get('nueva_password')
        id_usuario = session.get('reset_id_usuario')
        
        if id_usuario:
            conn = obtener_conexion()
            if verificar_token_db(id_usuario, codigo_web, conn):
                if cambiar_password_db(id_usuario, nueva_clave, conn):
                    session.pop('reset_id_usuario', None)
                    session.pop('permitir_paso_2', None)
                    flash("¡Contraseña actualizada con éxito! Ya puedes iniciar sesión.", "success")
                    conn.close()
                    return redirect(url_for('auth_bp.login'))
                else:
                    error = "Hubo un error al actualizar la contraseña."
            else:
                error = "El código de seguridad es incorrecto o ha expirado."
            conn.close()
        else:
            # Caso de correo falso, mantenemos el mismo error por seguridad
            error = "El código de seguridad es incorrecto o ha expirado."

    return render_template('restablecer_clave.html', error=error)