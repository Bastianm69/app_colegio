from flask import Flask
from mailer import mail

# 1. Importamos nuestros Blueprints
from rutas.auth import auth_bp
from rutas.admin import admin_bp
# from rutas.docente import docente_bp  <-- Lo descomentaremos cuando crees este archivo

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_sesiones_super_segura'

# 2. Configuración del Correo
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'bastianmatta12@gmail.com'
app.config['MAIL_PASSWORD'] = 'kzfhzjfqmdbgweqb'
mail.init_app(app)

# 3. Registramos las Rutas (Pegamos las piezas del rompecabezas)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
# app.register_blueprint(docente_bp)

if __name__ == '__main__':
    app.run(debug=True, port=5000)