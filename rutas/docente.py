from flask import Blueprint, render_template, request, redirect, url_for, session
from db_connection import obtener_conexion
from datetime import date

docente_bp = Blueprint('docente_bp', __name__)

# 1. RUTA PRINCIPAL: Panel de Control del Docente
@docente_bp.route('/docente')
def panel_docente():
    # --- LOGS DE DEPURACIÓN ---
    print("--- DEBUG ACCESO PANEL DOCENTE ---")
    print(f"User ID en sesión: {session.get('user_id')}")
    print(f"Roles en sesión: {session.get('roles')}")

    # Seguridad: Verificamos si el usuario está logueado y si 'DOCENTE' está en su lista de roles
    # TIP: Asegúrate de que en tu BD diga 'DOCENTE' (mayúsculas) o 'Docente'
    roles_usuario = session.get('roles', [])
    if 'user_id' not in session or 'DOCENTE' not in roles_usuario:
        print("--- DEBUG: Acceso denegado al Panel Docente. Redirigiendo al Login ---")
        return redirect(url_for('auth_bp.login'))

    print("--- DEBUG: Acceso concedido al Panel Docente ---")
    
    conn = obtener_conexion()
    clases = []
    nombre_profesor = "Docente"

    if conn:
        try:
            cur = conn.cursor()
            # 1. Buscamos quién es este profesor usando su cuenta de usuario
            cur.execute("SELECT id_docente, nombres, apellido_paterno FROM docentes WHERE id_usuario = %s", (session['user_id'],))
            docente = cur.fetchone()
            
            if docente:
                id_docente = docente[0]
                nombre_profesor = f"{docente[1]} {docente[2]}"
                
                # 2. Buscamos qué ramos y a qué cursos le hace clases
                query_clases = """
                    SELECT DISTINCT c.id_curso, c.nombre_curso, c.nivel, a.nombre_asignatura
                    FROM carga_academica ca
                    JOIN cursos c ON ca.id_curso = c.id_curso
                    JOIN asignaturas a ON ca.id_asignatura = a.id_asignatura
                    WHERE ca.id_docente = %s
                """
                cur.execute(query_clases, (id_docente,))
                clases = cur.fetchall() 
                
        except Exception as e:
            print(f"Error en panel docente: {e}")
        finally:
            cur.close()
            conn.close()

    return render_template('panel_docente.html', nombre=nombre_profesor, clases=clases)

# 2. RUTA PARA PASAR ASISTENCIA
@docente_bp.route('/docente/asistencia/<int:id_curso>', methods=['GET', 'POST'])
def tomar_asistencia(id_curso):
    if 'user_id' not in session or session.get('rol') != 'DOCENTE':
        return redirect(url_for('auth_bp.login'))

    conn = obtener_conexion()
    alumnos = []
    nombre_curso = ""
    hoy = date.today()

    if request.method == 'POST':
        # SI EL PROFESOR APRETÓ GUARDAR:
        if conn:
            try:
                cur = conn.cursor()
                # Recorremos cada respuesta del formulario (radio buttons)
                for key, value in request.form.items():
                    if key.startswith('estado_'):
                        # Extraemos el ID del alumno del nombre del botón
                        id_alumno = key.split('_')[1] 
                        estado = value # 'PRESENTE', 'AUSENTE', etc.
                        
                        # Guardamos en la base de datos
                        cur.execute("""
                            INSERT INTO asistencias (id_alumno, fecha, estado)
                            VALUES (%s, %s, %s)
                        """, (id_alumno, hoy, estado))
                
                conn.commit()
                # Opcional: Podríamos agregar un log de actividad aquí también
                return redirect(url_for('docente_bp.panel_docente'))
            except Exception as e:
                conn.rollback()
                print(f"Error al guardar asistencia: {e}")
            finally:
                cur.close()
                conn.close()

    # SI EL PROFESOR SOLO ENTRÓ A VER LA PÁGINA (GET):
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT nombre_curso FROM cursos WHERE id_curso = %s", (id_curso,))
            nombre_curso = cur.fetchone()[0]

            # Traemos a todos los alumnos de ese curso ordenados por apellido
            cur.execute("""
                SELECT id_alumno, rut, nombres, apellido_paterno, apellido_materno 
                FROM alumnos 
                WHERE id_curso = %s 
                ORDER BY apellido_paterno, apellido_materno
            """, (id_curso,))
            alumnos = cur.fetchall()
        except Exception as e:
            print(f"Error al cargar lista: {e}")
        finally:
            cur.close()
            conn.close()

    return render_template('tomar_asistencia.html', curso=nombre_curso, alumnos=alumnos, fecha=hoy)