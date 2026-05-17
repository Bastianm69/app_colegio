from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from db_connection import obtener_conexion
from datetime import date 

docente_bp = Blueprint('docente_bp', __name__)

# --- FUNCIÓN AUXILIAR LIMPIA ---
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
    
    # 1. Obtenemos datos del profe usando la función auxiliar
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
# 3.1 MÓDULO DE ASISTENCIA: TOMAR ASISTENCIA EN SALA
# ==========================================================
@docente_bp.route('/docente/asistencia/<int:id_curso>', methods=['GET', 'POST'])
def tomar_asistencia(id_curso):
    roles_str = str(session.get('roles', [])).upper()
    if 'user_id' not in session or 'DOCENTE' not in roles_str:
        return redirect(url_for('auth_bp.login'))

    hoy = date.today()
    alumnos = []
    
    # Recibimos el nombre del curso por la URL (query parameter) para no hacer otra consulta SQL
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
@docente_bp.route('/docente/notas')
def notas_menu():
    roles_str = str(session.get('roles', [])).upper()
    if 'user_id' not in session or 'DOCENTE' not in roles_str:
        return redirect(url_for('auth_bp.login'))
    return "<h1>Menú de Notas en construcción</h1><a href='/docente'>Volver</a>"