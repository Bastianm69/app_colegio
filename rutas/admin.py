from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from db_connection import obtener_conexion
from validaciones import validar_rut 
from db_registrar_docente import registrar_docente_db
from db_registrar_docente import obtener_todos_los_docentes, dar_de_baja_docente_db
from db_registrar_docente import obtener_docente_por_rut, actualizar_docente_db
from psycopg2.extras import RealDictCursor

import logging


# 1. Definición del Blueprint
admin_bp = Blueprint('admin_bp', __name__)

# ==============================================================================
# PANEL PRINCIPAL DEL ADMINISTRADOR
# ==============================================================================
@admin_bp.route('/admin')
def admin_panel():
    # Seguridad: Verificamos en la lista 'roles' en lugar de 'rol'
    roles_usuario = session.get('roles', [])
    if 'user_id' not in session or 'ADMIN' not in roles_usuario:
        return redirect(url_for('auth_bp.login'))
    
    nombre_admin = session.get('nombre_usuario', 'Administrador')
    return render_template('panel_admin.html', nombre_admin=nombre_admin)

# ==============================================================================
# MÓDULO: REGISTRAR NUEVO DOCENTE
# ==============================================================================
@admin_bp.route('/nuevo-docente', methods=['GET', 'POST'])
def nuevo_docente():
    # Seguridad: Actualizado al sistema de múltiples roles
    roles_usuario = session.get('roles', [])
    if 'user_id' not in session or 'ADMIN' not in roles_usuario:
        return redirect(url_for('auth_bp.login'))

    datos = {}
    asignaturas = [] # Lista para los checkboxes

    # Conexión inicial para obtener datos necesarios en el formulario (GET y POST)
    conn = obtener_conexion()
    if not conn:
        flash("Error técnico: No se pudo establecer conexión.", "error")
        return redirect(url_for('admin_bp.admin_panel'))

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Traemos las asignaturas para mostrarlas siempre en el formulario
        cur.execute("SELECT id_asignatura, nombre_asignatura FROM public.asignaturas ORDER BY nombre_asignatura ASC")
        asignaturas = cur.fetchall()
        cur.close()
    except Exception as e:
        print(f"LOG ERROR: No se pudieron cargar las asignaturas: {e}")

    if request.method == 'POST':
        print("\n" + ">>>" * 10)
        print("LOG: Inicio de solicitud POST en /nuevo-docente")
        
        # 1. Capturamos datos normales y la LISTA de IDs de asignaturas seleccionadas
        datos = dict(request.form)
        asignaturas_seleccionadas = request.form.getlist('asignaturas_habilitadas')
        
        print(f"LOG: Datos capturados: {datos}")
        print(f"LOG: Asignaturas marcadas: {asignaturas_seleccionadas}")
        
        # Validación del RUT
        rut_valido = validar_rut(datos.get('rut'))
        if not rut_valido:
            print(f"LOG: RUT inválido abortando: {datos.get('rut')}")
            flash("Error: El RUT ingresado no tiene un formato válido.", "error")
            return render_template('nuevo_docente.html', datos=datos, asignaturas=asignaturas)

        try:
            # 2. Llamada a la lógica de base de datos (le pasamos la lista de materias)
            print("LOG: Llamando a registrar_docente_db...")
            
            # Nota: Debes actualizar registrar_docente_db para que acepte 'asignaturas_seleccionadas'
            exito, mensaje = registrar_docente_db(datos, conn, asignaturas_seleccionadas)
            
            print(f"LOG: Resultado DB: exito={exito}, mensaje={mensaje}")
            
            if exito:
                flash(mensaje, "success")
                return redirect(url_for('admin_bp.admin_panel'))
            else:
                flash(mensaje, "error")
        except Exception as e:
            print(f"LOG: ERROR CRÍTICO: {str(e)}")
            flash(f"Error inesperado: {e}", "error")
        finally:
            conn.close()
            print("LOG: Conexión cerrada.")
        
        print("<<<" * 10 + "\n")

    return render_template('nuevo_docente.html', datos=datos, asignaturas=asignaturas)

# ==============================================================================
# MÓDULO: REGISTRAR NUEVO ALUMNO CON EL APODERADO 
# ==============================================================================

@admin_bp.route('/nuevo-alumno', methods=['GET', 'POST'])
def nuevo_alumno():
    roles_usuario = session.get('roles', [])
    if 'user_id' not in session or 'ADMIN' not in roles_usuario:
        return redirect(url_for('auth_bp.login'))

    conn = obtener_conexion()
    cur = conn.cursor()

    if request.method == 'POST':
        d = request.form
        vive_con = True if d.get('vive_con') == 'on' else False
        
        # VERIFICAMOS SI LA CASILLA ESTÁ MARCADA
        crear_alumno = True if d.get('check_alumno') == 'on' else False
        
        try:
            if crear_alumno:
                # FLUJO 1: Guardar Apoderado + Matricular Alumno
                cur.execute("""
                    CALL sp_matricular_alumno_completo(
                        %s, %s, %s, %s, %s, %s, %s, %s::INT,
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )""", (
                        d.get('rut_al'), d.get('nom_al'), d.get('ape_p_al'), d.get('ape_m_al'),
                        d.get('fec_nac'), d.get('genero'), d.get('nacionalidad'), d.get('id_curso'),
                        d.get('rut_apo'), d.get('nom_apo'), d.get('ape_p_apo'), d.get('ape_m_apo'),
                        d.get('parentesco_apo'), d.get('fono_apo'), d.get('email_apo'), vive_con,
                        d.get('calle'), d.get('comuna'), d.get('region'), d.get('cod_postal'), d.get('detalles_dir')
                    ))
                flash("Apoderado guardado y Alumno matriculado con éxito.", "success")
            else:
                # FLUJO 2: Solo guardar/actualizar Apoderado
                cur.execute("""
                    CALL sp_gestionar_apoderado_solo(
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )""", (
                        d.get('rut_apo'), d.get('nom_apo'), d.get('ape_p_apo'), d.get('ape_m_apo'),
                        d.get('parentesco_apo'), d.get('fono_apo'), d.get('email_apo'), vive_con,
                        d.get('calle'), d.get('comuna'), d.get('region'), d.get('cod_postal'), d.get('detalles_dir')
                    ))
                flash("Datos del apoderado actualizados correctamente.", "success")
            
            conn.commit()
            return redirect(url_for('admin_bp.admin_panel'))
            
        except Exception as e:
            conn.rollback()
            print(f"ERROR: {e}")
            flash(f"Error en la BD: {e}", "error")
            
    cur.execute("SELECT id_curso, nivel, nombre_curso FROM cursos WHERE anio_academico = 2026 ORDER BY id_curso ASC")
    cursos = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('nuevo_alumno.html', cursos=cursos)


# 2. LA NUEVA API PARA EL BOTÓN BUSCAR (AJAX)
@admin_bp.route('/api/buscar-apoderado/<rut>', methods=['GET'])
def api_buscar_apoderado(rut):
    conn = obtener_conexion()
    if not conn:
        return jsonify({'error': 'Sin conexión'}), 500

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT a.nombres, a.apellido_paterno, a.apellido_materno, a.parentesco, 
                   a.fono, a.email,
                   d.calle_numero, d.comuna, d.region, d.codigo_postal, d.detalles
            FROM public.apoderados a
            LEFT JOIN public.direcciones d ON a.id_direccion = d.id_direccion
            WHERE a.rut = %s
        """, (rut,))
        
        datos = cur.fetchone()
        cur.close()
        conn.close()

        if datos:
            return jsonify({
                'encontrado': True,
                'nombres': datos[0], 'ape_p': datos[1], 'ape_m': datos[2],
                'parentesco': datos[3], 'fono': datos[4], 'email': datos[5],
                'calle': datos[6], 'comuna': datos[7], 'region': datos[8],
                'cod_postal': datos[9] or '', 'detalles': datos[10] or ''
            })
        else:
            return jsonify({'encontrado': False})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
            
    # 3. GET: Cargar la lista de cursos para el <select> del formulario
    try:
        cur.execute("SELECT id_curso, nivel, nombre_curso FROM cursos WHERE anio_academico = 2026 ORDER BY id_curso ASC")
        cursos = cur.fetchall()
    except Exception as e:
        print(f"LOG ERROR CURSOS: {str(e)}")
        cursos = []
    finally:
        cur.close()
        conn.close()

    return render_template('nuevo_alumno.html', cursos=cursos)

# ==============================================================================
# MÓDULO: VER alumnos con sus apoderados y cursos (vista tipo "familias")
# ==============================================================================

@admin_bp.route('/familias', methods=['GET'])
def ver_familias():
    # Validar sesión de admin
    roles_usuario = session.get('roles', [])
    if 'user_id' not in session or 'ADMIN' not in roles_usuario:
        return redirect(url_for('auth_bp.login'))

    conn = obtener_conexion()
    cur = conn.cursor()

    try:
        # Obtenemos apoderados cruzados con sus alumnos y el curso de cada alumno
        cur.execute("""
            SELECT 
                apo.id_apoderado, apo.rut as rut_apo, apo.nombres as nom_apo, 
                apo.apellido_paterno as ape_p_apo, apo.apellido_materno as ape_m_apo, 
                apo.fono, apo.email,
                al.rut as rut_al, al.nombres as nom_al, al.apellido_paterno as ape_p_al, 
                al.apellido_materno as ape_m_al, c.nivel, c.nombre_curso
            FROM public.apoderados apo
            LEFT JOIN public.alumnos al ON apo.id_apoderado = al.id_apoderado
            LEFT JOIN public.cursos c ON al.id_curso = c.id_curso
            ORDER BY apo.apellido_paterno ASC, al.nombres ASC
        """)
        resultados = cur.fetchall()

        # Diccionario para agrupar a los alumnos bajo su apoderado
        familias = {}
        for row in resultados:
            id_apo = row[0]
            # Si el apoderado no está en el diccionario, lo creamos
            if id_apo not in familias:
                familias[id_apo] = {
                    'rut': row[1], 
                    'nombre_completo': f"{row[2]} {row[3]} {row[4]}",
                    'fono': row[5], 
                    'email': row[6],
                    'alumnos': []
                }
            
            # Si hay datos de un alumno asociado (row[7] es el RUT del alumno), lo añadimos a la lista
            if row[7]: 
                curso_str = f"{row[11]} {row[12]}" if row[11] else "Sin curso asignado"
                familias[id_apo]['alumnos'].append({
                    'rut': row[7],
                    'nombre_completo': f"{row[8]} {row[9]} {row[10]}",
                    'curso': curso_str
                })

    except Exception as e:
        print(f"Error al cargar familias: {e}")
        familias = {}
    finally:
        cur.close()
        conn.close()

    # Pasamos los valores del diccionario a la vista HTML
    return render_template('ver_familias.html', familias=familias.values())

# ==============================================================================
# MÓDULO: VER DOCENTES
# ==============================================================================

@admin_bp.route('/ver-docentes')
def lista_docentes():
    conn = obtener_conexion()
    docentes = obtener_todos_los_docentes(conn)
    conn.close()
    return render_template('ver_docentes.html', docentes=docentes)


@admin_bp.route('/eliminar-docente/<rut>')
def eliminar_docente(rut):
    # Verificación básica de sesión
    if not session.get('user_id'):
        return redirect(url_for('auth_bp.login'))

    conn = obtener_conexion()
    exito, mensaje = dar_de_baja_docente_db(rut, conn)
    conn.close()
    
    # Después de cambiar el estado, volvemos a la lista para ver el cambio
    return redirect(url_for('admin_bp.lista_docentes'))

from psycopg2.extras import RealDictCursor # IMPORTANTE: Asegúrate de tener esto arriba

@admin_bp.route('/editar-docente/<rut>', methods=['GET', 'POST'])
def editar_docente(rut):
    conn = obtener_conexion()
    
    # Configuramos el cursor como RealDictCursor para acceder por nombre de columna
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if request.method == 'POST':
        # 1. Capturamos la lista de IDs de las materias (vienen de los checkboxes)
        materias_seleccionadas = request.form.getlist('asignaturas_habilitadas')
        
        # 2. Captura de datos desde el HTML
        datos_form = {
            'rut': rut,
            'nombre_usuario': request.form.get('usuario'),
            'email': request.form.get('email'),
            'nombres': request.form.get('nombres'),
            'apellido_paterno': request.form.get('apellido_paterno'),
            'apellido_materno': request.form.get('apellido_materno'),
            'especialidad_nivel': request.form.get('especialidad_nivel'),
            'fono': request.form.get('fono'),
            'calle_numero': request.form.get('calle_numero'),
            'comuna': request.form.get('comuna'),
            'region': request.form.get('region'),
            'codigo_postal': request.form.get('codigo_postal'),
            'detalles': request.form.get('detalles'),
            'grupo_sangre': request.form.get('grupo_sangre'),
            'discapacidad': request.form.get('discapacidad'),
            'alergias': request.form.get('alergias'),
            'enfermedades_cronicas': request.form.get('enfermedades_cronicas'),
            'medicamentos': request.form.get('medicamentos'),
            'materias': materias_seleccionadas 
        }
        
        # Llamamos a la función que ejecuta el SP
        exito, msj = actualizar_docente_db(datos_form, conn)
        
        if exito:
            conn.close()
            flash("Perfil actualizado exitosamente", "success")
            return redirect(url_for('admin_bp.lista_docentes'))
        else:
            flash(f"Error al actualizar: {msj}", "error")

    # --- Lógica para mostrar el formulario (GET) ---
    
    # 1. Obtenemos los datos actuales (Ahora 'docente' será un diccionario)
    # IMPORTANTE: Asegúrate de que obtener_docente_por_rut use el mismo cursor_factory si es posible,
    # o simplemente haz la consulta aquí directamente para asegurar compatibilidad.
    cur.execute("SELECT * FROM v_detalle_docentes WHERE rut = %s", (rut,))
    docente = cur.fetchone()
    
    if not docente:
        cur.close()
        conn.close()
        flash("Docente no encontrado", "error")
        return redirect(url_for('admin_bp.lista_docentes'))

    # 2. Obtenemos TODAS las asignaturas existentes
    cur.execute("SELECT id_asignatura, nombre_asignatura FROM public.asignaturas ORDER BY nombre_asignatura ASC")
    todas_materias = cur.fetchall()
    
    # 3. Obtenemos solo los IDs de las materias que ya tiene este docente
    # Al ser RealDictCursor, ahora docente['id_docente'] SI funciona
    id_docente = docente['id_docente'] 
    cur.execute("SELECT id_asignatura FROM public.docente_materias WHERE id_docente = %s", (id_docente,))
    
    # Como el cursor es Dict, row es un diccionario {'id_asignatura': valor}
    materias_actuales = [row['id_asignatura'] for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return render_template('editar_docente.html', 
                           d=docente, 
                           todas_materias=todas_materias, 
                           materias_actuales=materias_actuales)

# ==============================================================================
# MÓDULO: ASIGNAR CURSO 
# ==============================================================================
@admin_bp.route('/asignar-cursos')
def asignar_cursos_vista():
    # El guardia de seguridad plural que ya conocemos
    roles_usuario = session.get('roles', [])
    if 'user_id' not in session or 'ADMIN' not in roles_usuario:
        return redirect(url_for('auth_bp.login'))

    conn = obtener_conexion()
    cursos = []
    docentes = []

    if conn:
        try:
            cur = conn.cursor()
            
            # 1. Obtenemos los cursos y el nombre de su jefe actual (si tiene)
            query_cursos = """
                SELECT c.id_curso, c.nombre_curso, c.nivel, d.nombres, d.apellido_paterno, c.id_profesor_jefe
                FROM cursos c
                LEFT JOIN docentes d ON c.id_profesor_jefe = d.id_docente
                ORDER BY c.nivel, c.nombre_curso
            """
            cur.execute(query_cursos)
            cursos = cur.fetchall()

            # 2. Obtenemos la lista de todos los docentes para los select del HTML
            cur.execute("SELECT id_docente, nombres, apellido_paterno FROM docentes ORDER BY apellido_paterno")
            docentes = cur.fetchall()

        except Exception as e:
            print(f"Error al cargar vista de asignación: {e}")
        finally:
            cur.close()
            conn.close()

    return render_template('asignar_cursos.html', cursos=cursos, docentes=docentes)

@admin_bp.route('/cursos')
def lista_cursos():
    return "dios escucha este programador"

@admin_bp.route('/asignar-clases', methods=['GET', 'POST'])
def asignar_clases():
    # Guardia plural de seguridad
    roles_usuario = session.get('roles', [])
    if 'user_id' not in session or 'ADMIN' not in roles_usuario:
        return redirect(url_for('auth_bp.login'))

    conn = obtener_conexion()
    docentes = []
    cursos = []
    asignaturas = []
    cargas_actuales = []

    if conn:
        try:
            cur = conn.cursor()

            # SI EL USUARIO PRESIONÓ EL BOTÓN "ASIGNAR" (POST)
            if request.method == 'POST':
                id_docente = request.form.get('id_docente')
                id_curso = request.form.get('id_curso')
                id_asignatura = request.form.get('id_asignatura')
                anio = 2026 # Puedes cambiarlo o hacerlo dinámico después

                # Insertamos en la tabla puente (carga_academica)
                query_insert = """
                    INSERT INTO carga_academica (id_docente, id_curso, id_asignatura, anio_escolar)
                    VALUES (%s, %s, %s, %s)
                """
                cur.execute(query_insert, (id_docente, id_curso, id_asignatura, anio))
                conn.commit()
                flash("Clase asignada correctamente al docente.", "success")
                return redirect(url_for('admin_bp.asignar_clases'))

            # SI SOLO ESTÁ ENTRANDO A LA PÁGINA (GET)
            # 1. Traemos datos para los Selectores (Combobox)
            cur.execute("SELECT id_docente, nombres, apellido_paterno FROM docentes ORDER BY apellido_paterno")
            docentes = cur.fetchall()

            cur.execute("SELECT id_curso, nivel, nombre_curso FROM cursos ORDER BY nivel, nombre_curso")
            cursos = cur.fetchall()

            cur.execute("SELECT id_asignatura, nombre_asignatura FROM asignaturas ORDER BY nombre_asignatura")
            asignaturas = cur.fetchall()

            # 2. Traemos el historial de lo que ya está asignado para mostrarlo en la tabla
            query_historial = """
                SELECT ca.id_carga, d.nombres, d.apellido_paterno, c.nivel, c.nombre_curso, a.nombre_asignatura
                FROM carga_academica ca
                JOIN docentes d ON ca.id_docente = d.id_docente
                JOIN cursos c ON ca.id_curso = c.id_curso
                JOIN asignaturas a ON ca.id_asignatura = a.id_asignatura
                WHERE ca.anio_escolar = 2026
                ORDER BY d.apellido_paterno, c.nivel
            """
            cur.execute(query_historial)
            cargas_actuales = cur.fetchall()

        except Exception as e:
            conn.rollback() # Si hay error (ej. clase duplicada), deshacemos
            flash(f"Error al asignar clase: probablemente ya existe. Detalles: {e}", "error")
        finally:
            cur.close()
            conn.close()

    return render_template('asignar_clases.html', docentes=docentes, cursos=cursos, asignaturas=asignaturas, cargas=cargas_actuales)



# ==============================================================================
# MÓDULO: ASIGNAR HORARIO 
# ==============================================================================

@admin_bp.route('/gestionar-horarios', methods=['GET', 'POST'])
def gestionar_horarios():
    roles_usuario = session.get('roles', [])
    if 'user_id' not in session or 'ADMIN' not in roles_usuario:
        return redirect(url_for('auth_bp.login'))

    conn = obtener_conexion()
    cur = conn.cursor()

    if request.method == 'POST':
        id_malla = request.form.get('id_malla')
        dia_semana = request.form.get('dia_semana')
        bloque_tiempo = request.form.get('bloque_tiempo')
        id_docente = request.form.get('id_docente')
        if not id_docente: 
            id_docente = None  # Permitir asignar sin docente para marcar el horario como "ocupado" pero sin profesor asignado

        try:
            # Insertamos en la nueva tabla sencilla
            cur.execute("""
                INSERT INTO public.horario_maestro (id_malla, dia_semana, bloque_tiempo, id_docente) 
                VALUES (%s, %s, %s, %s)
            """, (id_malla, dia_semana, bloque_tiempo, id_docente))
            conn.commit()
            flash("Horario y profesor asignados con éxito.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error al asignar horario: {e}", "error")
        return redirect(url_for('admin_bp.gestionar_horarios'))

    # Carga de datos para la vista GET
    try:
        # 1. Traer la Malla (los huecos a llenar)
        cur.execute("""
            SELECT m.id_malla, c.nombre_curso, a.nombre_asignatura 
            FROM public.malla_anual m
            JOIN public.cursos c ON m.id_curso = c.id_curso
            JOIN public.asignaturas a ON m.id_asignatura = a.id_asignatura
            WHERE m.anio_escolar = 2026
        """)
        mallas = cur.fetchall()

        # 2. Traer docentes para el selector
        cur.execute("SELECT id_docente, nombres, apellido_paterno FROM public.docentes WHERE activo = true")
        docentes = cur.fetchall()

        # 3. Traer los Horarios Maestros ya guardados para la tabla
        cur.execute("""
            SELECT hm.id_horario, hm.dia_semana, hm.bloque_tiempo, c.nombre_curso, a.nombre_asignatura, d.nombres, d.apellido_paterno
            FROM public.horario_maestro hm
            JOIN public.malla_anual m ON hm.id_malla = m.id_malla
            JOIN public.cursos c ON m.id_curso = c.id_curso
            JOIN public.asignaturas a ON m.id_asignatura = a.id_asignatura
            LEFT JOIN public.docentes d ON hm.id_docente = d.id_docente
            ORDER BY hm.dia_semana, hm.bloque_tiempo
        """)
        horarios_guardados = cur.fetchall()

        # Definimos bloques y días fijos estándar para simplificar el frontend
        bloques_fijos = ["08:00 - 09:30", "09:45 - 11:15", "11:30 - 13:00", "14:00 - 15:30", "15:45 - 17:15"]
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]

    except Exception as e:
        flash(f"Error cargando datos: {e}", "error")
        mallas, docentes, horarios_guardados, bloques_fijos, dias_semana = [], [], [], [], []
    finally:
        cur.close()
        conn.close()

    return render_template('gestionar_horarios.html', 
                           mallas=mallas, docentes=docentes, 
                           horarios=horarios_guardados,
                           bloques=bloques_fijos, dias=dias_semana)


@admin_bp.route('/asignar-cursos', methods=['GET', 'POST'])
def asignar_cursos():
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login'))

    conn = obtener_conexion()
    cur = conn.cursor()

    if request.method == 'POST':
        accion = request.form.get('accion')
        id_curso = request.form.get('id_curso')

        try:
            if accion == 'asignar':
                id_docente = request.form.get('id_docente')
                cur.execute("SELECT public.sp_asignar_profesor_jefe(%s, %s)", (id_curso, id_docente))
            elif accion == 'eliminar':
                cur.execute("SELECT public.sp_quitar_profesor_jefe(%s)", (id_curso,))
            
            conn.commit()
            flash("Operación realizada con éxito", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error en la base de datos: {e}", "error")
        
        return redirect(url_for('admin_bp.asignar_cursos'))

    try:
        cur.execute("SELECT * FROM public.sp_obtener_cursos_jefaturas(%s)", (2026,))
        cursos = cur.fetchall()

        cur.execute("SELECT * FROM public.sp_listar_docentes_activos()")
        docentes = cur.fetchall()
    except Exception as e:
        flash(f"Error al cargar datos: {e}", "error")
        cursos, docentes = [], []
    finally:
        cur.close()
        conn.close()
    
    return render_template('asignar_cursos.html', cursos=cursos, docentes=docentes)


@admin_bp.route('/asignar-materias', methods=['GET', 'POST'])
def asignar_materias():
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login'))

    conn = obtener_conexion()
    cur = conn.cursor()

    if request.method == 'POST':
        # Capturamos la acción (por defecto será 'agregar')
        accion = request.form.get('accion', 'agregar')

        if accion == 'agregar':
            id_curso = request.form.get('id_curso')
            id_asignatura = request.form.get('id_asignatura')
            horas = request.form.get('horas_semanales') 
            try:
                cur.execute("SELECT public.sp_crear_materia_malla(%s::INT, %s::INT, %s::INT, %s::INT)", 
                            (id_curso, id_asignatura, horas, 2026))
                conn.commit()
                flash("Materia agregada a la malla exitosamente.", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error al agregar materia: {e}", "error")

        elif accion == 'eliminar':
            id_malla = request.form.get('id_malla')
            try:
                cur.execute("SELECT public.sp_eliminar_materia_malla(%s::INT)", (id_malla,))
                conn.commit()
                flash("Materia eliminada del curso correctamente.", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error al eliminar materia: {e}", "error")
        
        return redirect(url_for('admin_bp.asignar_materias'))

    try:
        cur.execute("SELECT id_curso, nivel, nombre_curso FROM public.cursos WHERE anio_academico = 2026 ORDER BY nivel, nombre_curso")
        cursos = cur.fetchall()

        cur.execute("SELECT id_asignatura, nombre_asignatura FROM public.asignaturas ORDER BY nombre_asignatura")
        asignaturas = cur.fetchall()

        cur.execute("SELECT * FROM public.sp_obtener_malla_curso(2026)")
        malla_plana = cur.fetchall()
        
        malla_agrupada = {}
        for m in malla_plana:
            nombre_curso = f"{m[1]} {m[2]}" 
            if nombre_curso not in malla_agrupada:
                malla_agrupada[nombre_curso] = []
                
            malla_agrupada[nombre_curso].append({
                'id_malla': m[0],  # ¡NUEVO! Guardamos el ID para poder borrar
                'asignatura': m[3],
                'horas': m[4] if len(m) > 4 else 0
            })

    except Exception as e:
        flash(f"Error cargando datos: {e}", "error")
        cursos, asignaturas, malla_agrupada = [], [], {}
    finally:
        cur.close()
        conn.close()

    return render_template('asignar_materias.html', cursos=cursos, asignaturas=asignaturas, malla_agrupada=malla_agrupada)

