from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from db_connection import obtener_conexion
from datetime import date 

docente_bp = Blueprint('docente_bp', __name__)
# esto es para colocar el nombre al docente en la paguina 
def obtener_info_docente_sesion():
    """Llama a la BD para obtener ID y nombre del docente logueado."""
    conn = obtener_conexion()
    info_docente = None
    if conn:
        try:
            cur = conn.cursor()
            # Usamos la nueva función de la BD
            cur.execute("SELECT * FROM public.fn_obtener_info_docente(%s)", (session['user_id'],))
            info_docente = cur.fetchone()
        except Exception as e:
            print(f"Error al rescatar info del docente: {e}")
        finally:
            conn.close()
    return info_docente

# ==========================================================
# 1. PANEL PRINCIPAL 
# ==========================================================
@docente_bp.route('/docente')
def panel_docente():
    roles_str = str(session.get('roles', [])).upper()
    if 'user_id' not in session or 'DOCENTE' not in roles_str:
        return redirect(url_for('auth_bp.login'))

    clases = []
    nombre_profesor = "Docente"
    
    # 1. Obtenemos datos del profe 
    info = obtener_info_docente_sesion()
    
    if info:
        id_docente = info[0]
        nombre_profesor = f"{info[1]} {info[2]}"
        
        # 2. Obtenemos sus clases llamando a la función de la BD
        conn = obtener_conexion()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM public.fn_obtener_clases_docente(%s)", (id_docente,))
                clases = cur.fetchall() 
            except Exception as e:
                print(f"Error en panel docente: {e}")
            finally:
                conn.close()

    return render_template('panel_docente.html', nombre=nombre_profesor, clases=clases)


# ==========================================================
# 2. HORARIO ASIGNADO 
# ==========================================================
@docente_bp.route('/docente/horario')
def ver_horario():
    roles_str = str(session.get('roles', [])).upper()
    if 'user_id' not in session or 'DOCENTE' not in roles_str:
        return redirect(url_for('auth_bp.login'))

    info = obtener_info_docente_sesion()
    horario_completo = []

    if info:
        id_docente = info[0]
        conn = obtener_conexion()
        if conn:
            try:
                cur = conn.cursor()
                # Llamamos a la función del horario en la BD
                cur.execute("SELECT * FROM public.fn_obtener_horario_docente(%s)", (id_docente,))
                horario_completo = cur.fetchall()
            except Exception as e:
                print(f"Error al cargar horario: {e}")
            finally:
                conn.close()

    return render_template('docente_horario.html', horario=horario_completo)


# ==========================================================
# 3. MÓDULO DE ASISTENCIA: MENÚ DE CURSOS
# ==========================================================
@docente_bp.route('/docente/asistencia')
def asistencia_menu():
    roles_str = str(session.get('roles', [])).upper()
    if 'user_id' not in session or 'DOCENTE' not in roles_str:
        return redirect(url_for('auth_bp.login'))

    info = obtener_info_docente_sesion()
    cursos = []

    if info:
        id_docente = info[0]
        conn = obtener_conexion()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM public.fn_obtener_cursos_docente(%s)", (id_docente,))
                cursos = cur.fetchall()
            except Exception as e:
                print(f"Error al cargar cursos para asistencia: {e}")
            finally:
                conn.close()

    return render_template('docente_asistencia_menu.html', cursos=cursos)


# ==========================================================
# 3.1 MÓDULO DE ASISTENCIA: TOMAR ASISTENCIA
# ==========================================================
@docente_bp.route('/docente/asistencia/<int:id_curso>', methods=['GET', 'POST'])
def tomar_asistencia(id_curso):
    roles_str = str(session.get('roles', [])).upper()
    if 'user_id' not in session or 'DOCENTE' not in roles_str:
        return redirect(url_for('auth_bp.login'))

    hoy = date.today()
    alumnos = []
    
    # 
    nombre_curso = request.args.get('nombre_curso', 'Curso Seleccionado')

    conn = obtener_conexion()
    
    # --- SI EL PROFESOR APRIETA "GUARDAR ASISTENCIA" ---
    if request.method == 'POST':
        if conn:
            try:
                cur = conn.cursor()
                # Recorremos todas las respuestas del formulario
                for key, value in request.form.items():
                    if key.startswith('estado_'):
                        id_alumno = int(key.split('_')[1])
                        estado = value # 'PRESENTE', 'AUSENTE', o 'ATRASADO'
                        observacion = request.form.get(f'obs_{id_alumno}', '')

                        # Ejecutamos nuestro SP limpio!
                        cur.execute("CALL public.sp_guardar_asistencia(%s, %s, %s, %s)", 
                                    (id_alumno, hoy, estado, observacion))
                
                conn.commit()
                flash("Asistencia registrada exitosamente.", "success")
                return redirect(url_for('docente_bp.asistencia_menu'))
            
            except Exception as e:
                conn.rollback()
                print(f"Error al guardar asistencia: {e}")
            finally:
                conn.close()

    # --- SI EL PROFESOR SOLO ENTRÓ A VER LA PÁGINA ---
    elif conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM public.fn_obtener_alumnos_curso(%s)", (id_curso,))
            alumnos = cur.fetchall()
        except Exception as e:
            print(f"Error al cargar lista de alumnos: {e}")
        finally:
            conn.close()

    return render_template('tomar_asistencia.html', curso=nombre_curso, alumnos=alumnos, fecha=hoy, id_curso=id_curso)


# ==========================================================
# 4. CALIFICACIONES 
# ==========================================================
# ==========================================================
# 4. MÓDULO DE CALIFICACIONES: SELECCIÓN DE ASIGNATURA
# ==========================================================
@docente_bp.route('/docente/notas')
def notas_menu():
    roles_str = str(session.get('roles', [])).upper()
    if 'user_id' not in session or 'DOCENTE' not in roles_str:
        return redirect(url_for('auth_bp.login'))

    info = obtener_info_docente_sesion()
    clases_notas = []

    if info:
        id_docente = info[0]
        conn = obtener_conexion()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM public.fn_obtener_clases_notas(%s)", (id_docente,))
                clases_notas = cur.fetchall()
            except Exception as e:
                print(f"Error al cargar menú de notas: {e}")
            finally:
                conn.close()

    return render_template('docente_notas_menu.html', clases_notas=clases_notas)


# ==========================================================
# 4.1 MÓDULO DE CALIFICACIONES: VER PLANILLA Y INGRESAR NOTAS
# ==========================================================
@docente_bp.route('/docente/notas/<int:id_curso>/<int:id_asignatura>', methods=['GET', 'POST'])
def gestionar_notas(id_curso, id_asignatura):
    roles_str = str(session.get('roles', [])).upper()
    if 'user_id' not in session or 'DOCENTE' not in roles_str:
        return redirect(url_for('auth_bp.login'))

    # Rescatamos nombres desde la URL para no sobrecargar de consultas SQL la BD
    nombre_curso = request.args.get('curso', 'Curso')
    nombre_asignatura = request.args.get('asignatura', 'Asignatura')
    hoy = date.today()

    conn = obtener_conexion()

    # --- SI EL PROFESOR INGRESA UNA NUEVA EVALUACIÓN (POST) ---
    if request.method == 'POST':
        titulo_eval = request.form.get('titulo_evaluacion', '').strip()
        fecha_eval = request.form.get('fecha_evaluacion', str(hoy))
        
        if conn and titulo_eval:
            try:
                cur = conn.cursor()
                # Recorremos el formulario buscando los campos de notas dinámicas
                for key, value in request.form.items():
                    if key.startswith('nota_') and value.strip():
                        id_alumno = int(key.split('_')[1])
                        # Validamos formato decimal en Chile (reemplazar coma por punto)
                        valor_nota = float(value.replace(',', '.'))
                        obs = request.form.get(f'obs_{id_alumno}', '')

                        if 1.0 <= valor_nota <= 7.0:
                            cur.execute("CALL public.sp_guardar_calificacion(%s, %s, %s, %s, %s, %s)",
                                        (id_alumno, id_asignatura, titulo_eval, valor_nota, fecha_eval, obs))
                
                conn.commit()
                flash("Calificaciones guardadas exitosamente.", "success")
                return redirect(url_for('docente_bp.gestionar_notas', id_curso=id_curso, id_asignatura=id_asignatura, curso=nombre_curso, asignatura=nombre_asignatura))
            except Exception as e:
                conn.rollback()
                print(f"Error al guardar calificaciones: {e}")
            finally:
                conn.close()

    # --- CARGAR PLANILLA DE NOTAS (GET) ---
    planilla_raw = []
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM public.fn_obtener_planilla_notas(%s, %s)", (id_curso, id_asignatura))
            planilla_raw = cur.fetchall()
        except Exception as e:
            print(f"Error al cargar planilla de notas: {e}")
        finally:
            conn.close()

    # Procesamiento en Python para estructurar la matriz de datos tipo "Excel"
    # Estructura final deseada: { id_alumno: { 'nombre': '...', 'evaluaciones': { 'Prueba 1': 6.5 }, 'promedio': 0.0 } }
    planilla_alumnos = {}
    evaluaciones_set = set() # Guarda los títulos únicos de evaluaciones para las columnas de la tabla

    for row in planilla_raw:
        id_al, rut, nombre, titulo, nota, fecha = row
        if id_al not in planilla_alumnos:
            planilla_alumnos[id_al] = {
                'rut': rut,
                'nombre': nombre,
                'notas': {},
                'promedio': 0.0
            }
        
        if titulo:
            planilla_alumnos[id_al]['notas'][titulo] = float(nota)
            evaluaciones_set.add(titulo)

    # Ordenamos los títulos de las evaluaciones alfabética o cronológicamente para que las columnas mantengan el orden
    columnas_evaluaciones = sorted(list(evaluaciones_set))

    # Calculamos el promedio de cada alumno dinámicamente en Python
    for al_id, datos in planilla_alumnos.items():
        lista_notas = datos['notas'].values()
        if lista_notas:
            # Redondeo escolar estándar de un decimal
            datos['promedio'] = round(sum(lista_notas) / len(lista_notas), 1)
        else:
            datos['promedio'] = '-'

    # Si la lista de alumnos está vacía, hacemos una consulta limpia para traer al menos los nombres de quienes pertenecen al curso
    if not planilla_alumnos and conn:
        try:
            conn = obtener_conexion()
            cur = conn.cursor()
            cur.execute("SELECT * FROM public.fn_obtener_alumnos_curso(%s)", (id_curso,))
            alumnos_base = cur.fetchall()
            for al in alumnos_base:
                planilla_alumnos[al[0]] = {
                    'rut': al[1],
                    'nombre': f"{al[3]} {al[4]}, {al[2]}",
                    'notas': {},
                    'promedio': '-'
                }
        except Exception as e:
            print(f"Error cargando alumnos base: {e}")
        finally:
            conn.close()

    return render_template('ingresar_notas.html', 
                           id_curso=id_curso, 
                           id_asignatura=id_asignatura, 
                           curso=nombre_curso, 
                           asignatura=nombre_asignatura, 
                           planilla=planilla_alumnos, 
                           columnas=columnas_evaluaciones,
                           fecha_hoy=hoy)