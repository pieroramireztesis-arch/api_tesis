from flask import Blueprint, jsonify
from conexionBD import Conexion
from models.Progreso import Progreso
import json

ws_dashboard = Blueprint('ws_dashboard', __name__, url_prefix='/dashboard')


@ws_dashboard.route('/mini/<int:id_estudiante>', methods=['GET'])
def mini_dashboard(id_estudiante: int):
    """
    Mini dashboard para el estudiante.

    Ahora usa la MISMA lógica que:
      - /progreso/resumen  -> completitud global (ejercicios resueltos / totales)
      - /progreso/por_competencia -> completitud por competencia

    Respuesta:
    {
      "saludo": "Juan",
      "progresoGeneral": 12,   # 0..100, completitud global
      "promedio": 65,          # promedio de puntajes (0..100)
      "temas": [
        {"nombre": "Resuelve problemas de cantidad", "porcentaje": 0},
        {"nombre": "Resuelve problemas de regularidad, equivalencia y cambio", "porcentaje": 10},
        ...
      ]
    }
    """
    con = Conexion()
    cur = con.cursor()
    try:
        # 1) Saludo (nombre del estudiante)
        cur.execute("""
            SELECT u.nombre
            FROM usuarios u
            JOIN estudiante e ON e.id_usuario = u.id_usuario
            WHERE e.id_estudiante = %s
            LIMIT 1
        """, (id_estudiante,))
        row = cur.fetchone()
        saludo = (row and row.get('nombre')) or "Alumno"

        # 2) Progreso general (MISMA LÓGICA QUE /progreso/resumen)
        #    completitud global: ejercicios resueltos / ejercicios totales (competencias 1..4)
        cur.execute("""
            SELECT
                COUNT(DISTINCT e.id_ejercicio) AS total_ejercicios,
                COUNT(DISTINCT r.id_ejercicio) AS resueltos
            FROM ejercicios e
            LEFT JOIN respuestas_estudiantes r
                   ON r.id_ejercicio = e.id_ejercicio
                  AND r.id_estudiante = %s
            WHERE e.id_competencia BETWEEN 1 AND 4
        """, (id_estudiante,))
        row_total = cur.fetchone() or {}
        total_ej = row_total.get("total_ejercicios", 0) or 0
        resueltos = row_total.get("resueltos", 0) or 0

        if total_ej > 0:
            progreso_general = int(round(100.0 * float(resueltos) / float(total_ej)))
        else:
            progreso_general = 0

        if progreso_general < 0:
            progreso_general = 0
        if progreso_general > 100:
            progreso_general = 100

        # 3) Promedio general de puntajes (0..100) - lo mantenemos como info extra
        cur.execute("""
            SELECT COALESCE(ROUND(AVG(puntaje)), 0)::int AS promedio
            FROM puntajes
            WHERE id_estudiante = %s
        """, (id_estudiante,))
        row_prom = cur.fetchone() or {}
        promedio = row_prom.get('promedio', 0) or 0

        # 4) % por competencia (MISMA LÓGICA QUE /progreso/por_competencia)
        cur.execute("""
            SELECT
                c.id_competencia,
                c.descripcion,
                COUNT(DISTINCT e.id_ejercicio) AS total_ejercicios,
                COUNT(DISTINCT r.id_ejercicio) AS resueltos
            FROM competencias c
            LEFT JOIN ejercicios e
                   ON e.id_competencia = c.id_competencia
            LEFT JOIN respuestas_estudiantes r
                   ON r.id_ejercicio = e.id_ejercicio
                  AND r.id_estudiante = %s
            WHERE c.id_competencia BETWEEN 1 AND 4
            GROUP BY c.id_competencia, c.descripcion
            ORDER BY c.id_competencia
        """, (id_estudiante,))
        temas_rows = cur.fetchall() or []

        temas = []
        for r in temas_rows:
            total_comp = r.get("total_ejercicios") or 0
            resueltos_comp = r.get("resueltos") or 0

            if total_comp > 0:
                pct = int(round(100.0 * float(resueltos_comp) / float(total_comp)))
            else:
                pct = 0

            if pct < 0:
                pct = 0
            if pct > 100:
                pct = 100

            temas.append({
                "nombre": r["descripcion"],
                "porcentaje": pct
            })

        return jsonify({
            "saludo": saludo,
            "progresoGeneral": progreso_general,
            "promedio": int(promedio),
            "temas": temas
        }), 200

    except Exception as e:
        return jsonify({
            "saludo": "Alumno",
            "progresoGeneral": 0,
            "promedio": 0,
            "temas": [],
            "error": str(e)
        }), 500
    finally:
        cur.close()
        con.close()


@ws_dashboard.route('/docente/<int:id_docente>', methods=['GET'])
def dashboard_docente(id_docente: int):
    """
    Endpoint para el panel del profesor.
    URL final: /dashboard/docente/<id_docente>

    Devuelve:
    {
      "status": true,
      "message": "ok",
      "data": {
        "estudiantesActivos": 10,
        "progresoPromedio": 65.0,
        "temaMasDificultad": "Ecuaciones de segundo grado",
        "actividadReciente": [
          {
            "tipo": "completado el tema",
            "nombreEstudiante": "Ana Torres",
            "tema": "Ecuaciones lineales",
            "fecha": "2024-11-30T15:23:11"
          },
          ...
        ]
      }
    }
    """
    con = Conexion()
    cur = con.cursor()

    try:
        # 1) VALIDAR QUE EL DOCENTE EXISTA Y OBTENER SU NOMBRE (PARA FUTURO)
        cur.execute("""
            SELECT u.nombre, u.apellidos
            FROM docente d
            JOIN usuarios u ON u.id_usuario = d.id_usuario
            WHERE d.id_docente = %s
            LIMIT 1
        """, (id_docente,))
        row_doc = cur.fetchone()
        if not row_doc:
            return jsonify({
                "status": False,
                "message": "Docente no encontrado",
                "data": None
            }), 404

        # 2) ESTUDIANTES ACTIVOS ASOCIADOS AL DOCENTE
        cur.execute("""
            SELECT COUNT(DISTINCT e.id_estudiante) AS activos
            FROM docente_salones ds
            JOIN salones s ON s.id_salon = ds.id_salon
            JOIN estudiante_salones es ON es.id_salon = s.id_salon
            JOIN estudiante e ON e.id_estudiante = es.id_estudiante
            WHERE ds.id_docente = %s
              AND e.estado_estudiante = 'activo'
        """, (id_docente,))
        row_activos = cur.fetchone() or {}
        estudiantes_activos = row_activos.get("activos", 0) or 0

        # 3) PROGRESO PROMEDIO (usando campo progreso_general de la tabla estudiante)
        cur.execute("""
            SELECT COALESCE(AVG(e.progreso_general), 0) AS promedio
            FROM docente_salones ds
            JOIN salones s ON s.id_salon = ds.id_salon
            JOIN estudiante_salones es ON es.id_salon = s.id_salon
            JOIN estudiante e ON e.id_estudiante = es.id_estudiante
            WHERE ds.id_docente = %s
              AND e.estado_estudiante = 'activo'
        """, (id_docente,))
        row_prom = cur.fetchone() or {}
        progreso_promedio = float(row_prom.get("promedio", 0) or 0)

        # 4) TEMA CON MÁS DIFICULTAD (menor promedio de nivel_estudiante_competencia)
        cur.execute("""
            SELECT c.descripcion,
                   AVG(nec.promedio_puntaje) AS promedio_comp
            FROM docente_salones ds
            JOIN salones s ON s.id_salon = ds.id_salon
            JOIN estudiante_salones es ON es.id_salon = s.id_salon
            JOIN nivel_estudiante_competencia nec ON nec.id_estudiante = es.id_estudiante
            JOIN competencias c ON c.id_competencia = nec.id_competencia
            WHERE ds.id_docente = %s
            GROUP BY c.descripcion
            ORDER BY promedio_comp ASC
            LIMIT 1
        """, (id_docente,))
        row_tema = cur.fetchone()
        tema_mas_dificultad = row_tema.get("descripcion") if row_tema else None

        # 5) ACTIVIDAD RECIENTE (últimos 3 registros de progreso de sus estudiantes)
        cur.execute("""
            SELECT 
                u.nombre || ' ' || u.apellidos AS estudiante,
                c.descripcion AS tema,
                p.fecha,
                p.estado
            FROM progreso p
            JOIN estudiante e ON e.id_estudiante = p.id_estudiante
            JOIN usuarios u ON u.id_usuario = e.id_usuario
            JOIN ejercicios ej ON ej.id_ejercicio = p.id_ejercicio
            JOIN competencias c ON c.id_competencia = ej.id_competencia
            WHERE e.id_estudiante IN (
                SELECT es.id_estudiante
                FROM docente_salones ds
                JOIN salones s ON s.id_salon = ds.id_salon
                JOIN estudiante_salones es ON es.id_salon = s.id_salon
                WHERE ds.id_docente = %s
            )
            ORDER BY p.fecha DESC
            LIMIT 3
        """, (id_docente,))

        rows_act = cur.fetchall() or []

        actividad_reciente = []
        for r in rows_act:
            estado = (r.get("estado") or "").lower()
            if estado.startswith("correcto"):
                tipo_texto = "completado el tema"
            elif estado.startswith("incorrecto"):
                tipo_texto = "intentado resolver el tema"
            else:
                tipo_texto = "trabajado en el tema"

            actividad_reciente.append({
                "tipo": tipo_texto,
                "nombreEstudiante": r.get("estudiante", ""),
                "tema": r.get("tema", ""),
                "fecha": r["fecha"].isoformat() if r.get("fecha") else None
            })

        data = {
            "estudiantesActivos": estudiantes_activos,
            "progresoPromedio": progreso_promedio,
            "temaMasDificultad": tema_mas_dificultad,
            "actividadReciente": actividad_reciente
        }

        return jsonify({
            "status": True,
            "message": "ok",
            "data": data
        }), 200

    except Exception as e:
        return jsonify({
            "status": False,
            "message": str(e),
            "data": None
        }), 500
    finally:
        cur.close()
        con.close()
