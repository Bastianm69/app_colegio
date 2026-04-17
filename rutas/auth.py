from flask import Blueprint, render_template, request, redirect, url_for, session
from db_connection import obtener_conexion
from db_tokens import crear_token_db, verificar_token_db
from mailer import enviar_correo_autorizacion

# 1. Creamos el Blueprint para la Autenticación
auth_bp = Blueprint('auth_bp', __name__)

# 2. Ruta principal redirige al login
@auth_bp.route('/')
def index():
    return redirect(url_for('auth_bp.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        usuario_f = request.form.get('usuario')
        password_f = request.form.get('password')
        ip_cliente = request.remote_addr

        conn = obtener_conexion()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT u.id_usuario, u.nombre_usuario, r.nombre_rol, u.email 
                    FROM usuarios u
                    JOIN roles r ON u.id_rol = r.id_rol
                    WHERE u.nombre_usuario = %s AND u.password_hash = %s
                """, (usuario_f, password_f))
                
                user_found = cur.fetchone()

                if user_found:
                    id_usuario, nombre_u, rol, email_docente = user_found
                    
                    # Registro de intento exitoso
                    cur.execute("CALL sp_registrar_intento_login(%s, %s, %s, %s)", 
                                (usuario_f, id_usuario, ip_cliente, True))
                    conn.commit()

                    if not email_docente:
                        error = "Tu cuenta no tiene un correo registrado."
                    else:
                        session['pre_login_id'] = id_usuario
                        session['pre_login_rol'] = rol
                        
                        token = crear_token_db(id_usuario, conn)
                        if token and enviar_correo_autorizacion(email_docente, token):
                            return redirect(url_for('auth_bp.verificar')) 
                        else:
                            error = "Error al enviar el correo de seguridad."
                else:
                    # Registro de intento fallido
                    cur.execute("CALL sp_registrar_intento_login(%s, %s, %s, %s)", 
                                (usuario_f, None, ip_cliente, False))
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
        if verificar_token_db(user_id, codigo_web, conn):
            # Acceso Concedido
            session['user_id'] = user_id
            session['rol'] = rol
            session.pop('pre_login_id')
            session.pop('pre_login_rol')
            
            # Redirección según el rol
            if rol == 'ADMIN':
                return redirect(url_for('admin_bp.admin_panel'))
            else:
                return redirect(url_for('docente_bp.panel_docente')) # Lo crearemos después
        else:
            error = "Código incorrecto o expirado."

    return render_template('verificar.html', error=error)

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth_bp.login'))