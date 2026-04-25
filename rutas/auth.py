from flask import Blueprint, render_template, request, redirect, url_for, session

# Importamos nuestras propias funciones desde otros archivos del proyecto
from db_connection import obtener_conexion
from db_tokens import crear_token_db, verificar_token_db # Funciones para el código 2FA
from mailer import enviar_correo_autorizacion # Función para enviar el email

# 1. Creamos el Blueprint para la Autenticación
# Le damos el nombre 'auth_bp'. Todo lo que tenga @auth_bp.route pertenecerá a este módulo.
auth_bp = Blueprint('auth_bp', __name__)

# RUTA RAÍZ (La puerta principal)

@auth_bp.route('/')
def index():
    # Si alguien entra a la página principal sin más, lo empujamos de inmediato a la pantalla de login
    return redirect(url_for('auth_bp.login'))

# RUTA DE LOGIN (Paso 1: Validar credenciales)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None # Variable para guardar mensajes de error si algo sale mal

    # Si el método es POST, significa que el usuario presionó el botón "Ingresar" en el formulario
    if request.method == 'POST':
        # Atrapamos lo que escribió en las cajas de texto de HTML (name="usuario" y name="password")
        usuario_f = request.form.get('usuario')
        password_f = request.form.get('password')
        
        # --- LÓGICA DE IP REAL ---
        # Tratamos de saber desde qué computadora (IP) se está conectando. 
        # 'X-Forwarded-For' ayuda a ver la IP real incluso si el colegio usa un proxy o firewall.
        ip_cliente = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_cliente and ',' in ip_cliente:
            ip_cliente = ip_cliente.split(',')[0].strip()

        # Abrimos la carretera hacia la base de datos
        conn = obtener_conexion()
        if conn:
            try: # Plan de rescate por si la base de datos falla
                # Creamos a nuestro "mensajero"
                cur = conn.cursor()
                
                # Búsqueda de credenciales
                # ATENCIÓN: Esta consulta se puede mejorar a futuro pasando a un Stored Procedure (SP)
                # Fíjate cómo usa los %s por seguridad para evitar Inyección SQL.
                cur.execute("""
                    SELECT u.id_usuario, u.nombre_usuario, r.nombre_rol, u.email 
                    FROM usuarios u
                    JOIN roles r ON u.id_rol = r.id_rol
                    WHERE u.nombre_usuario = %s AND u.password_hash = %s
                """, (usuario_f, password_f))
                
                # Traemos el resultado (si el usuario y la clave coincidieron)
                user_found = cur.fetchone()

                # Si encontró al usuario (las credenciales son correctas)
                if user_found:
                    # Desempaquetamos los 4 datos que pedimos en el SELECT
                    id_usuario, nombre_u, rol, email_docente = user_found
                    
                    # CUIDADO: Aún no lo dejamos entrar. Lo guardamos en una "sala de espera" (pre_login)
                    # en la sesión, hasta que verifique su código por correo.
                    session['pre_login_id'] = id_usuario
                    session['pre_login_rol'] = rol
                    session['pre_login_nombre'] = nombre_u 
                    
                    # Llamamos a un SP en la BD para dejar un registro de que alguien hizo login correcto
                    cur.execute("CALL sp_registrar_intento_login(%s, %s, %s, %s)", 
                                (usuario_f, id_usuario, ip_cliente, True))
                    conn.commit() # Guardamos los cambios del log

                    # Validamos si tiene correo para enviarle el código
                    if not email_docente:
                        error = "Tu cuenta no tiene un correo registrado."
                    else:
                        # Generamos el token seguro en la base de datos
                        token = crear_token_db(id_usuario, conn)
                        
                        # Si el token se creó bien y el correo se envió con éxito...
                        if token and enviar_correo_autorizacion(email_docente, token):
                            # ...lo mandamos a la pantalla del segundo paso (Verificar)
                            return redirect(url_for('auth_bp.verificar')) 
                        else:
                            error = "Error al enviar el correo de seguridad."
                
                # Si las credenciales fueron INCORRECTAS
                else:
                    # Llamamos al SP para registrar un intento fallido (False)
                    cur.execute("CALL sp_registrar_intento_login(%s, %s, %s, %s)", 
                                (usuario_f, None, ip_cliente, False))
                    conn.commit()
                    error = "Usuario o contraseña incorrectos."
                
                # Le decimos al mensajero que termine y cerramos la calle
                cur.close()
                conn.close()
                
            except Exception as e:
                # Si se cae la base de datos, mostramos el error sin que se muera la app
                error = f"Error en la base de datos: {e}"
        else:
            error = "No hay conexión con la base de datos."
    
    # Si fue método GET (solo entró a la página) o si hubo algún error, mostramos el login.html
    return render_template('login.html', error=error)



# RUTA DE VERIFICACIÓN (Paso 2: Código 2FA)

@auth_bp.route('/verificar', methods=['GET', 'POST'])
def verificar():
    # Seguridad: Si el usuario intenta entrar a la URL "/verificar" directamente sin 
    # haber pasado por el login (no tiene 'pre_login_id'), lo devolvemos al login.
    if 'pre_login_id' not in session:
        return redirect(url_for('auth_bp.login'))

    error = None
    if request.method == 'POST':
        # Atrapamos el código de 6 dígitos que ingresó en el HTML
        codigo_web = request.form.get('codigo')
        
        # Recuperamos sus datos de la "sala de espera"
        user_id = session['pre_login_id']
        rol = session['pre_login_rol']
        
        conn = obtener_conexion()
        
        # Invocamos la función de base de datos que revisa si el código es real y no está vencido
        if verificar_token_db(user_id, codigo_web, conn):
            
            # ¡CÓDIGO CORRECTO! Lo pasamos de la "sala de espera" a la "Sesión Oficial"
            session['user_id'] = user_id
            session['rol'] = rol
            
            # session.pop() saca el dato de la memoria y lo borra al mismo tiempo.
            # Si por alguna razón no hay nombre, usa 'Administrador' por defecto.
            session['nombre_usuario'] = session.pop('pre_login_nombre', 'Administrador')
            
            # Limpiamos la basura de la sala de espera por seguridad
            session.pop('pre_login_id', None)
            session.pop('pre_login_rol', None)
            
            # Dependiendo de quién sea, le abrimos una puerta u otra
            if rol == 'ADMIN':
                return redirect(url_for('admin_bp.admin_panel'))
            else:
                return redirect(url_for('docente_bp.panel_docente'))
        else:
            # Si el código estaba mal o pasaron los 15 minutos
            error = "Código incorrecto o expirado."

    # Mostramos la pantallita para pedir el código
    return render_template('verificar.html', error=error)



# RUTA DE LOGOUT (Cerrar sesión)

@auth_bp.route('/logout')
def logout():
    # Borra absolutamente todo lo que hay en el espacio de memoria del usuario
    session.clear()
    # Y lo patea de vuelta a la pantalla de login
    return redirect(url_for('auth_bp.login'))