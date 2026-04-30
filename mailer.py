# Esto es lo que ocupamos para enviar el correo al usuario

from flask_mail import Mail, Message         

mail = Mail()

def enviar_correo_autorizacion(email_destino, token, es_recuperacion=False):
    # 1. Definimos el Asunto y Cuerpo dependiendo del propósito
    if es_recuperacion:
        asunto = "Restablecer Contraseña - Sistema Escolar"
        cuerpo = f"Has solicitado restablecer tu contraseña. Tu código de seguridad es: {token}. Expira en 15 minutos."
    else:
        asunto = "Código de Acceso - Sistema Escolar"
        cuerpo = f"Tu código de acceso para iniciar sesión es: {token}. Expira en 15 minutos."

    # 2. Creamos el mensaje con los datos dinámicos
    msg = Message(asunto,
                  sender="bastianmatta12@gmail.com", 
                  recipients=[email_destino])
    
    msg.body = cuerpo
    
    # Intento de envío con reporte de error detallado
    try:
        mail.send(msg)
        return True
    except Exception as e:
        print("\n" + "="*50)
        print("🚨 ¡ALERTA! ERROR AL ENVIAR EL CORREO 🚨")
        print(f"TIPO: {'Recuperación' if es_recuperacion else 'Login'}")
        print(f"DETALLE EXACTO: {e}")
        print("="*50 + "\n")
        return False