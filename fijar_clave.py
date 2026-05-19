from werkzeug.security import generate_password_hash
from db_connection import obtener_conexion

def ejecutar_actualizacion():
    conn = obtener_conexion()
    if not conn:
        print("❌ No se pudo conectar a la base de datos.")
        return
    
    try:
        cur = conn.cursor()
        
        # 1. Tu propio Flask genera el Hash perfecto y compatible con tu versión
        hash_nativo = generate_password_hash('123')
        print(f"📦 Hash generado por tu sistema: {hash_nativo}")
        
        # 2. Se lo inyectamos directamente a bastian1
        cur.execute("""
            UPDATE public.usuarios 
            SET password_hash = %s 
            WHERE nombre_usuario = 'bastian1'
        """, (hash_nativo,))
        
        conn.commit()
        cur.close()
        print("✅ ¡Contraseña de 'bastian1' actualizada con éxito a '123'!")
        
    except Exception as e:
        print(f"❌ Error al actualizar: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    ejecutar_actualizacion()