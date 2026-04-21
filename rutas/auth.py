from flask import Blueprint, render_template, request, redirect, url_for, session
from db_connection import obtener_conexion
from db_tokens import crear_token_db, verificar_token_db
from mailer import enviar_correo_autorizacion

# 1. Creamos el Blueprint para la Autenticación
auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/')
def index():
    return redirect(url_for('auth_bp.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        usuario_f = request.form.get('usuario')
        password_f = request.form.get('password')
        
        # --- LÓGICA DE IP REAL ---
        # 1. Intentamos obtener la IP de la cabecera 'X-Forwarded-For'. 
        #    Los servidores en internet (como Render o Cloudflare) guardan la IP real del usuario ahí.
        # 2. Si esa cabecera no existe (como cuando pruebas en tu PC), usamos 'request.remote_addr'.
        ip_cliente = request.headers.get('X-Forwarded-For', request.remote_addr)

        # 3. A veces 'X-Forwarded-For' devuelve una lista de IPs separadas por comas.
        #    La IP real del profesor siempre es la primera de esa lista.
        if ip_cliente and ',' in ip_cliente:
            ip_cliente = ip_cliente.split(',')[0].strip()
        # -------------------------

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
                    
                    # Registro de intento exitoso con la IP real capturada arriba
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
                    # Registro de intento fallido con la IP real
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
            session['user_id'] = user_id
            session['rol'] = rol
            session.pop('pre_login_id')
            session.pop('pre_login_rol')
            
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