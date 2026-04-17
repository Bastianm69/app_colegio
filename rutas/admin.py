from flask import Blueprint, render_template, request, redirect, url_for, session
from db_connection import obtener_conexion
from validaciones import validar_rut 

# 1. Definición del Blueprint
admin_bp = Blueprint('admin_bp', __name__)

@admin_bp.route('/admin')
def admin_panel():
    if 'user_id' not in session or session.get('rol') != 'ADMIN':
        return redirect(url_for('auth_bp.login'))
    return render_template('panel_admin.html')

@admin_bp.route('/nuevo-docente', methods=['GET', 'POST'])
def nuevo_docente():
    # Seguridad: Verificar sesión de administrador
    if 'user_id' not in session or session.get('rol') != 'ADMIN':
        return redirect(url_for('auth_bp.login'))

    mensaje = None
    color = "red"

    if request.method == 'POST':
        # Recogemos todos los datos del formulario
        f = request.form 
        
        # Validamos el RUT antes de tocar la base de datos
        if not validar_rut(f.get('rut')):
            return render_template('nuevo_docente.html', msg="Error: El RUT ingresado es inválido.", color="red")

        conn = obtener_conexion()
        if conn:
            try:
                cur = conn.cursor()
                
                # LA GRAN CONSULTA: 3 inserciones automáticas + unión final
                query = """
                    WITH ins_usuario AS (
                        INSERT INTO usuarios (nombre_usuario, password_hash, email, id_rol, activo)
                        VALUES (%s, %s, %s, 2, true) RETURNING id_usuario
                    ),
                    ins_medico AS (
                        INSERT INTO datos_medicos (grupo_sangre, alergias, enfermedades_cronicas, medicamentos, discapacidad)
                        VALUES (%s, %s, %s, %s, %s) RETURNING id_dato_medico
                    ),
                    ins_direccion AS (
                        INSERT INTO direcciones (calle_numero, comuna, region, codigo_postal, detalles)
                        VALUES (%s, %s, %s, %s, %s) RETURNING id_direccion
                    )
                    INSERT INTO docentes (
                        id_usuario, id_dato_medico, id_direccion, 
                        rut, nombres, apellido_paterno, apellido_materno, 
                        especialidad_nivel, fono
                    )
                    SELECT 
                        u.id_usuario, m.id_dato_medico, d.id_direccion, 
                        %s, %s, %s, %s, %s, %s
                    FROM ins_usuario u, ins_medico m, ins_direccion d;
                """
                
                cur.execute(query, (
                    # Datos para ins_usuario
                    f.get('nombre_usuario'), f.get('password'), f.get('email'),
                    
                    # Datos para ins_medico
                    f.get('grupo_sangre'), f.get('alergias'), f.get('enfermedades_cronicas'), 
                    f.get('medicamentos'), f.get('discapacidad'),
                    
                    # Datos para ins_direccion (según tu captura de pantalla)
                    f.get('calle_numero'), f.get('comuna'), f.get('region'), 
                    f.get('codigo_postal'), f.get('detalles'),
                    
                    # Datos personales para docentes
                    f.get('rut'), f.get('nombres'), f.get('apellido_paterno'), 
                    f.get('apellido_materno'), f.get('especialidad_nivel'), f.get('fono')
                ))
                
                conn.commit()
                mensaje = "¡Docente registrado con éxito (Cuenta, Salud y Dirección creadas)!"
                color = "green"
            
            except Exception as e:
                conn.rollback()
                # Personalización de errores comunes
                error_msg = str(e)
                if "docentes_rut_key" in error_msg:
                    mensaje = "Error: El RUT ya existe en el sistema."
                elif "usuarios_nombre_usuario_key" in error_msg:
                    mensaje = "Error: El nombre de usuario ya está ocupado."
                else:
                    mensaje = f"Error en el registro: {e}"
            finally:
                cur.close()
                conn.close()

    # El render_template está fuera del IF POST para manejar el método GET (ver el formulario)
    return render_template('nuevo_docente.html', msg=mensaje, color=color)