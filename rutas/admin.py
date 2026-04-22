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

    mi_id = session['user_id']
    nombre_admin = "Administrador"

    conn = obtener_conexion()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT nombre_usuario FROM usuarios WHERE id_usuario = %s", (mi_id,))
            resultado = cur.fetchone()
            if resultado:
                nombre_admin = resultado[0]
        except Exception as e:
            print(f"Error al obtener nombre de admin: {e}")
        finally:
            cur.close()
            conn.close()
    return render_template('panel_admin.html', nombre=nombre_admin)

@admin_bp.route('/nuevo-docente', methods=['GET', 'POST'])
def nuevo_docente():
    # Seguridad: Verificar sesión de administrador
    if 'user_id' not in session or session.get('rol') != 'ADMIN':
        return redirect(url_for('auth_bp.login'))

    mensaje = None
    color = "red"
    
    # ---------------------------------------------------------
    # Creamos un diccionario vacío al inicio. 
    # Si la petición es GET (solo entrar a la página), este diccionario 
    # se enviará vacío y el formulario aparecerá en blanco.
    # ---------------------------------------------------------
    datos = {}

    if request.method == 'POST':
        # request.form trae todo lo que el usuario escribió.
        f = request.form 
        
        # ---------------------------------------------------------
        # IMPORTANTE: Convertimos request.form en un diccionario normal dict().
        # Hacemos esto porque request.form es de solo lectura (no se puede modificar).
        # Al convertirlo en un dict(), podemos borrarle campos específicos si hay errores.
        # ---------------------------------------------------------
        datos = dict(f) 
        
        # Validamos el RUT antes de tocar la base de datos
        if not validar_rut(f.get('rut')):
            # Si el RUT es inválido matemáticamente, lo borramos del diccionario
            datos['rut'] = '' 
            # Devolvemos la página: el mensaje saldrá rojo y la casilla del RUT estará vacía
            return render_template('nuevo_docente.html', msg="Error: El RUT ingresado es inválido.", color="red", datos=datos)

        conn = obtener_conexion()
        if conn:
            try:
                cur = conn.cursor()
                
                # LA GRAN CONSULTA: 3 inserciones + unión final + RETORNO de ID
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
                    FROM ins_usuario u, ins_medico m, ins_direccion d
                    RETURNING id_docente;  -- Pedimos a PostgreSQL el ID del docente creado
                """
                
                cur.execute(query, (
                    # Datos para ins_usuario
                    f.get('nombre_usuario'), f.get('password'), f.get('email'),
                    
                    # Datos para ins_medico
                    f.get('grupo_sangre'), f.get('alergias'), f.get('enfermedades_cronicas'), 
                    f.get('medicamentos'), f.get('discapacidad'),
                    
                    # Datos para ins_direccion
                    f.get('calle_numero'), f.get('comuna'), f.get('region'), 
                    f.get('codigo_postal'), f.get('detalles'),
                    
                    # Datos personales para docentes
                    f.get('rut'), f.get('nombres'), f.get('apellido_paterno'), 
                    f.get('apellido_materno'), f.get('especialidad_nivel'), f.get('fono')
                ))
                
                # REGISTRO DE AUDITORÍA (LOG)
                id_nuevo_docente = cur.fetchone()[0]
                id_admin_actual = session['user_id'] 
                detalles_log = f"Se registró al docente {f.get('nombres')} {f.get('apellido_paterno')} (RUT: {f.get('rut')})"
                
                query_log = """
                    INSERT INTO logs_actividad (id_usuario, accion, tabla_afectada, registro_id, detalles)
                    VALUES (%s, 'CREAR', 'docentes', %s, %s)
                """
                cur.execute(query_log, (id_admin_actual, id_nuevo_docente, detalles_log))
                
                # Confirmamos que TODO se guarde
                conn.commit()
                mensaje = "¡Docente registrado con éxito (Historial de actividad guardado)!"
                color = "green"
                
                # ---------------------------------------------------------
                # Si llegamos aquí, la base de datos guardó todo perfecto.
                # Vaciamos el diccionario 'datos' para que el formulario 
                # quede limpio y listo para registrar al siguiente docente.
                # ---------------------------------------------------------
                datos = {}
            
            except Exception as e:
                # Si algo falla (ej: RUT duplicado), deshacemos los cambios
                conn.rollback()
                
                error_msg = str(e)
                
                # ---------------------------------------------------------
                # MANEJO DE ERRORES INTELIGENTE:
                # Revisamos qué parte de la base de datos se quejó y borramos 
                # SOLO esa casilla en el diccionario 'datos'.
                # ---------------------------------------------------------
                
                if "docentes_rut_key" in error_msg:
                    mensaje = "Error: Este RUT ya pertenece a otro profesor en el sistema."
                    datos['rut'] = '' # Vaciamos solo el RUT
                    
                elif "usuarios_nombre_usuario_key" in error_msg:
                    mensaje = "Error: El nombre de usuario ya está ocupado. Intenta con otro."
                    datos['nombre_usuario'] = '' # Vaciamos solo el Usuario
                    
                elif "usuarios_email_key" in error_msg:
                    mensaje = "Error: Este correo electrónico ya está registrado."
                    datos['email'] = '' # Vaciamos solo el Correo
                    
                else:
                    mensaje = f"Error en el registro: {e}"
            finally:
                cur.close()
                conn.close()

    # ---------------------------------------------------------
    # Al final, le mandamos el diccionario 'datos' a tu archivo HTML.
    # - Si hubo éxito, 'datos' irá vacío (formulario limpio).
    # - Si hubo error, 'datos' irá con casi todo, menos el campo que falló.
    # ---------------------------------------------------------
    return render_template('nuevo_docente.html', msg=mensaje, color=color, datos=datos)