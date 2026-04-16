from flask import Flask, render_template, request, redirect, url_for, session
from db_connection import obtener_conexion
from db_tokens import crear_token_db, verificar_token_db 
from mailer import mail, enviar_correo_autorizacion 

# 1. INICIALIZAMOS FLASK (Esto es lo que faltaba)
app = Flask(__name__)
app.secret_key = 'clave_secreta_para_sesiones' # Obligatorio para usar session

# 2. CONFIGURACIÓN DEL CORREO (Acuérdate de poner tus datos reales aquí)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'bastianmatta12@gmail.com'
app.config['MAIL_PASSWORD'] = 'kzfhzjfqmdbgweqb'
mail.init_app(app)

# --- RUTA DE INICIO ---
@app.route('/')
def index():
    return redirect(url_for('login'))

# --- RUTA DE LOGIN ---
@app.route('/login', methods=['GET', 'POST'])
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
                    id_usuario = user_found[0]
                    rol = user_found[2]
                    email_docente = user_found[3] # La variable mágica
                    
                    cur.execute("CALL sp_registrar_intento_login(%s, %s, %s, %s)", 
                                (usuario_f, id_usuario, ip_cliente, True))
                    conn.commit()

                    if not email_docente:
                        error = "Tu cuenta no tiene un correo registrado. Contacta al administrador."
                    else:
                        session['pre_login_id'] = id_usuario
                        session['pre_login_rol'] = rol
                        
                        token = crear_token_db(id_usuario, conn)
                        
                        if token and enviar_correo_autorizacion(email_docente, token):
                            return redirect(url_for('verificar')) 
                        else:
                            error = "Error interno al intentar enviar el correo de seguridad."

                else:
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


# --- RUTA DE VERIFICACIÓN (SALA DE ESPERA) ---
@app.route('/verificar', methods=['GET', 'POST'])
def verificar():
    if 'pre_login_id' not in session:
        return redirect(url_for('login'))

    error = None
    if request.method == 'POST':
        codigo_web = request.form.get('codigo')
        user_id = session['pre_login_id']
        rol = session['pre_login_rol']
        
        conn = obtener_conexion()
        if verificar_token_db(user_id, codigo_web, conn):
            # ¡CÓDIGO CORRECTO! Acceso total concedido
            session['user_id'] = user_id
            session.pop('pre_login_id')
            session.pop('pre_login_rol')
            
            if rol == 'ADMIN':
                return redirect(url_for('admin_panel'))
            else:
                return f"<h1>Bienvenido Docente</h1>"
        else:
            error = "Código incorrecto o expirado."

    return render_template('verificar.html', error=error)

# --- RUTA DEL PANEL DE ADMIN (Temporal para que no te dé error al redirigir) ---
@app.route('/admin')
def admin_panel():
    return render_template('panel_admin.html') # Asumo que tienes este HTML

# 3. ARRANCAMOS EL SERVIDOR
if __name__ == '__main__':
    app.run(debug=True, port=5000)