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
    roles_usuario = session.get('roles', [])
    if 'user_id' not in session or 'ADMIN' not in roles_usuario:
        return redirect(url_for('auth_bp.login'))

    datos = {}
    asignaturas = [] 

    conn = obtener_conexion()
    if not conn:
        flash("Error técnico: No se pudo establecer conexión.", "error")
        return redirect(url_for('admin_bp.admin_panel'))

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id_asignatura, nombre_asignatura FROM public.asignaturas ORDER BY nombre_asignatura ASC")
        asignaturas = cur.fetchall()
        cur.close()
    except Exception as e:
        print(f"LOG ERROR: No se pudieron cargar las asignaturas: {e}")

    if request.method == 'POST':
        datos = dict(request.form)
        asignaturas_seleccionadas = request.form.getlist('asignaturas_habilitadas')
        
        rut_valido = validar_rut(datos.get('rut'))
        if not rut_valido:
            flash("Error: El RUT ingresado no tiene un formato válido.", "error")
            return render_template('nuevo_docente.html', datos=datos, asignaturas=asignaturas)

        try:
            exito, mensaje = registrar_docente_db(datos, conn, asignaturas_seleccionadas)
            if exito:
                flash(mensaje, "success")
                return redirect(url_for('admin_bp.admin_panel'))
            else:
                flash(mensaje, "error")
        except Exception as e:
            flash(f"Error inesperado: {e}", "error")
        finally:
            conn.close()
        
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
        crear_alumno = True if d.get('check_alumno') == 'on' else False
        
        try:
            if crear_alumno:
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
            flash(f"Error en la BD: {e}", "error")
            
    cur.execute("SELECT id_curso, nivel, nombre_curso FROM cursos WHERE anio_academico = 2026 ORDER BY id_curso ASC")
    cursos = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('nuevo_alumno.html', cursos=cursos)

# ==============================================================================
# API AJAX: BUSCAR APODERADO
# ==============================================================================
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

# ==============================================================================
# MÓDULO: VER FAMILIAS
# ==============================================================================
@admin_bp.route('/familias', methods=['GET'])
def ver_familias():
    roles_usuario = session.get('roles', [])
    if 'user_id' not in session or 'ADMIN' not in roles_usuario:
        return redirect(url_for('auth_bp.login'))

    conn = obtener_conexion()
    cur = conn.cursor()

    try:
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

        familias = {}
        for row in resultados:
            id_apo = row[0]
            if id_apo not in familias:
                familias[id_apo] = {
                    'rut': row[1], 
                    'nombre_completo': f"{row[2]} {row[3]} {row[4]}",
                    'fono': row[5], 
                    'email': row[6],
                    'alumnos': []
                }
            
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

    return render_template('ver_familias.html', familias=familias.values())

# ==============================================================================
# MÓDULO: VER DOCENTES Y ELIMINAR
# ==============================================================================
@admin_bp.route('/ver-docentes')
def lista_docentes():
    conn = obtener_conexion()
    docentes = obtener_todos_los_docentes(conn)
    conn.close()
    return render_template('ver_docentes.html', docentes=docentes)

@admin_bp.route('/eliminar-docente/<rut>')
def eliminar_docente(rut):
    if not session.get('user_id'):
        return redirect(url_for('auth_bp.login'))

    conn = obtener_conexion()
    exito, mensaje = dar_de_baja_docente_db(rut, conn)
    conn.close()
    return redirect(url_for('admin_bp.lista_docentes'))

# ==============================================================================
# MÓDULO: EDITAR DOCENTE
# ==============================================================================
@admin_bp.route('/editar-docente/<rut>', methods=['GET', 'POST'])
def editar_docente(rut):
    conn = obtener_conexion()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if request.method == 'POST':
        materias_seleccionadas = request.form.getlist('asignaturas_habilitadas')
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
        
        exito, msj = actualizar_docente_db(datos_form, conn)
        
        if exito:
            conn.close()
            flash("Perfil actualizado exitosamente", "success")
            return redirect(url_for('admin_bp.lista_docentes'))
        else:
            flash(f"Error al actualizar: {msj}", "error")

    cur.execute("SELECT * FROM v_detalle_docentes WHERE rut = %s", (rut,))
    docente = cur.fetchone()
    
    if not docente:
        cur.close()
        conn.close()
        flash("Docente no encontrado", "error")
        return redirect(url_for('admin_bp.lista_docentes'))

    cur.execute("SELECT id_asignatura, nombre_asignatura FROM public.asignaturas ORDER BY nombre_asignatura ASC")
    todas_materias = cur.fetchall()
    
    id_docente = docente['id_docente'] 
    cur.execute("SELECT id_asignatura FROM public.docente_materias WHERE id_docente = %s", (id_docente,))
    materias_actuales = [row['id_asignatura'] for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return render_template('editar_docente.html', 
                           d=docente, 
                           todas_materias=todas_materias, 
                           materias_actuales=materias_actuales)

# ==============================================================================
# MÓDULO: RUTAS EXTRAS DE CURSOS
# ==============================================================================
@admin_bp.route('/cursos')
def lista_cursos():
    return "dios escucha este programador"

# ==============================================================================
# MÓDULO: ASIGNAR MATERIAS (MALLA ANUAL)
# ==============================================================================
@admin_bp.route('/asignar-materias', methods=['GET', 'POST'])
def asignar_materias():
    roles_usuario = session.get('roles', [])
    if 'user_id' not in session or 'ADMIN' not in roles_usuario:
        return redirect(url_for('auth_bp.login'))

    conn = obtener_conexion()
    cur = conn.cursor()

    if request.method == 'POST':
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
                'id_malla': m[0],
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

# ==============================================================================
# MÓDULO: GESTIONAR HORARIOS (VISTA DE PARRILLA TOTALMENTE BASADA EN SP)
# ==============================================================================
@admin_bp.route('/gestionar-horarios', methods=['GET', 'POST'])
def gestionar_horarios():
    roles_usuario = session.get('roles', [])
    if 'user_id' not in session or 'ADMIN' not in roles_usuario:
        return redirect(url_for('auth_bp.login'))

    conn = obtener_conexion()
    # FORZAMOS A LEER COMO DICCIONARIO PARA EVITAR ERRORES DE ÍNDICE
    cur = conn.cursor(cursor_factory=RealDictCursor) 

    # --- LÓGICA DE GUARDADO (POST) ---
    if request.method == 'POST':
        id_malla = request.form.get('id_malla')
        dia_semana = request.form.get('dia_semana')
        bloque_tiempo = request.form.get('bloque_tiempo')
        id_docente = request.form.get('id_docente')
        id_curso_actual = request.form.get('id_curso_actual') 

        try:
            cur.execute("CALL public.sp_asignar_horario_maestro(%s, %s, %s, %s)", 
                        (id_malla, dia_semana, bloque_tiempo, id_docente or None))
            conn.commit()
            flash("Clase asignada con éxito en la parrilla.", "success")
            
        except Exception as e:
            conn.rollback()
            mensaje_error = str(e).split('\n')[0] 
            flash(f"No se pudo asignar: {mensaje_error}", "error")
        
        return redirect(url_for('admin_bp.gestionar_horarios', id_curso=id_curso_actual))

    # --- LÓGICA DE VISTA (GET) ---
    id_curso_seleccionado = request.args.get('id_curso')
    cursos = []
    mallas_curso = []
    grid = {} 
    bloques_fijos = ["08:00 - 09:30", "09:45 - 11:15", "11:30 - 13:00", "14:00 - 15:30", "15:45 - 17:15"]
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]

    try:
        # 1. Traer lista de cursos mediante SP
        cur.execute("SELECT * FROM public.sp_obtener_cursos_activos(%s)", (2026,))
        cursos_bd = cur.fetchall()
        # Transformamos para que el HTML siga funcionando igual
        cursos = [(c['id_curso'], c['nivel'], c['nombre_curso']) for c in cursos_bd]

        if id_curso_seleccionado:
            # 2. Traer el progreso de horas mediante SP
            cur.execute("SELECT * FROM public.sp_obtener_progreso_malla(%s, %s)", (id_curso_seleccionado, 2026))
            mallas_bd = cur.fetchall()

            for m in mallas_bd:
                # AHORA LEEMOS POR NOMBRE EXACTO, IMPOSIBLE QUE FALLE
                id_m = m['id_malla']
                nombre = m['nombre_asignatura']
                h_totales = m['horas_totales']
                h_asignadas = m['horas_asignadas']
                h_restantes = h_totales - h_asignadas
                
                mallas_curso.append({
                    'id_malla': id_m,
                    'nombre_asignatura': nombre,
                    'horas_totales': h_totales,
                    'horas_asignadas': h_asignadas,
                    'horas_restantes': h_restantes,
                    'porcentaje': min((h_asignadas / h_totales) * 100 if h_totales > 0 else 0, 100)
                })

            # 3. Cargar la parrilla mediante SP
            cur.execute("SELECT * FROM public.sp_obtener_horario_curso(%s)", (id_curso_seleccionado,))
            horarios_db = cur.fetchall()

            for h in horarios_db:
                dia = h['dia_semana']
                bloque = h['bloque_tiempo']
                asig = h['nombre_asignatura']
                nom_profe = h['nombres']
                ape_profe = h['apellido_paterno']

                if bloque not in grid:
                    grid[bloque] = {}
                grid[bloque][dia] = {
                    'asignatura': asig,
                    'profesor': f"{nom_profe} {ape_profe}" if nom_profe else "Sin Profesor"
                }

    except Exception as e:
        flash(f"Error cargando datos: {e}", "error")
    finally:
        cur.close()
        conn.close()

    return render_template('gestionar_horarios.html', 
                           cursos=cursos, 
                           id_curso_seleccionado=int(id_curso_seleccionado) if id_curso_seleccionado else None,
                           mallas_curso=mallas_curso,
                           grid=grid,
                           bloques=bloques_fijos, 
                           dias=dias_semana)

# ==============================================================================
# API AJAX: FILTRO DINÁMICO ANTI-CHOQUES
# ==============================================================================
@admin_bp.route('/api/docentes-disponibles', methods=['GET'])
def api_docentes_disponibles():
    id_malla = request.args.get('id_malla')
    dia = request.args.get('dia')
    bloque = request.args.get('bloque')
    
    if not all([id_malla, dia, bloque]):
        return jsonify({'error': 'Faltan parámetros'}), 400

    conn = obtener_conexion()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT * FROM public.sp_obtener_docentes_disponibles(%s, %s, %s)", (id_malla, dia, bloque))
        docentes = cur.fetchall()
        return jsonify(docentes)
    except Exception as e:
        print(f"Error API Filtro: {e}")
        return jsonify({'error': 'Error interno de base de datos'}), 500
    finally:
        cur.close()
        conn.close()