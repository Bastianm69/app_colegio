import os
from dotenv import load_dotenv
from flask import Flask
from mailer import mail

# Cargamos las variables en env.
load_dotenv()

# 1. Importamos nuestros Blueprints
from rutas.auth import auth_bp
from rutas.admin import admin_bp
from rutas.docente import docente_bp 

app = Flask(__name__)
# Leemos la clave secreta desde el .env
app.secret_key = os.getenv('CLAVE_SECRETA_FLASK', 'clave_respaldo_por_si_acaso')

# 2. Configuración del Correo
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False  
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASS')
mail.init_app(app)

# 3. Registramos las Rutas 
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(docente_bp)   

if __name__ == '__main__':
    app.run(debug=True, port=5000)