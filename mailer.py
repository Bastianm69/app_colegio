#Esto es lo que ocupamos para enviar el correo al usuario#

from flask_mail import Mail, Message        

mail = Mail()

def enviar_correo_autorizacion(email_destino, token):
    msg = Message("Código de Acceso Sistema Escolar",
                  sender="bastianmatta12@gmail.com", 
                  recipients=[email_destino])
    
    msg.body = f"Tu código de acceso es: {token}. Expira en 15 minutos."
    
    # esto es para mostrar error en consola si el correo no se envía por alguna razón (credenciales mal, servicio caído, etc)
    try:
        mail.send(msg)
        return True
    except Exception as e:
        print("\n" + "="*50)
        print("🚨 ¡ALERTA! ERROR AL ENVIAR EL CORREO 🚨")
        print(f"DETALLE EXACTO: {e}")
        print("="*50 + "\n")
        return False