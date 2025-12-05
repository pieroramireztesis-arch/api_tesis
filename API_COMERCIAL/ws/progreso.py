from flask import Blueprint, request, jsonify
from models.Progreso import Progreso
from conexionBD import Conexion
import json

ws_progreso = Blueprint('ws_progreso', __name__, url_prefix='/progreso')

# ==========================
#  POST /progreso
#  Registrar progreso
# ==========================
@ws_progreso.route('', methods=['POST'])
def registrar_progreso():
    try:
        data = request.get_json(force=True)

        id_estudiante = data.get('id_estudiante')
        id_ejercicio = data.get('id_ejercicio')
        nivel_actual = data.get('nivel_actual')
        estado = data.get('estado')
        tiempo_respuesta = data.get('tiempo_respuesta')

        if id_estudiante is None or id_ejercicio is None or nivel_actual is None or estado is None:
            return jsonify({"status": False, "mensaje": "Faltan campos obligatorios"}), 400

        resp = Progreso.registrar(
            id_estudiante, id_ejercicio, nivel_actual, estado, tiempo_respuesta
        )
        return jsonify(json.loads(resp))

    except Exception as e:
        return jsonify({"status": False, "mensaje": str(e)}), 500


# ==========================
#  GET /progreso
#  Listar todos
# ==========================
@ws_progreso.route('', methods=['GET'])
def listar_progreso():
    try:
        return jsonify(json.loads(Progreso.listar_todos()))
    except Exception as e:
        return jsonify({"status": False, "mensaje": str(e)}), 500


# ==========================================================
#  GET /progreso/resumen (CTO-RESUMEN-V2)
#  Progreso real basado en ejercicios distintos y reforzados
# ==========================================================
@ws_progreso.route('/resumen', methods=['GET'])
def resumen_progreso():
    id_estudiante = request.args.get('idEstudiante', type=int)
    if not id_estudiante:
        return jsonify({"status": False, "mensaje": "idEstudiante es obligatorio"}), 400

    con = Conexion()
    cur = con.cursor()

    PESO_NUEVO = 1.0
    PESO_REPETIDO = 0.30   # Ajustado para tu modelo híbrido

    try:
        cur.execute("""
            SELECT
                COUNT(DISTINCT e.id_ejercicio) AS total_ejercicios,

                -- ejercicios distintos correctos
                COUNT(
                    DISTINCT CASE WHEN o.es_correcta = TRUE THEN r.id_ejercicio END
                ) AS distintos_correctos,

                -- correctos totales (incluye refuerzos)
                COUNT(
                    CASE WHEN o.es_correcta = TRUE THEN 1 END
                ) AS correctos_totales

            FROM ejercicios e
            LEFT JOIN respuestas_estudiantes r
                ON r.id_ejercicio = e.id_ejercicio
               AND r.id_estudiante = %s
            LEFT JOIN opciones_ejercicio o
                ON o.id_opcion = r.id_opcion
        """, (id_estudiante,))

        row = cur.fetchone() or {}

        total = row["total_ejercicios"]
        distintos_correctos = row["distintos_correctos"]
        correctos_totales = row["correctos_totales"]

        repetidos = max(0, correctos_totales - distintos_correctos)

        if total > 0:
            puntaje = (
                distintos_correctos * PESO_NUEVO +
                repetidos * PESO_REPETIDO
            ) / total
        else:
            puntaje = 0

        porcentaje = min(100, max(0, round(puntaje * 100)))

        # Texto motivador
        if porcentaje >= 80:
            resumen = "¡Excelente progreso!"
        elif porcentaje >= 50:
            resumen = "Vas bien, sigue así."
        elif porcentaje > 0:
            resumen = "Estás empezando, continúa practicando."
        else:
            resumen = "Aún no has iniciado actividades."

        return jsonify({
            "status": True,
            "nivelPorcentaje": porcentaje,
            "ejerciciosDesarrollados": int(distintos_correctos),
            "resumenTexto": resumen
        })

    except Exception as e:
        return jsonify({"status": False, "mensaje": str(e)}), 500
    finally:
        cur.close()
        con.close()

# ==========================================================
#  GET /progreso/por_competencia (CTO-PORCOMP-V2)
#  Cálculo ponderado REAL por competencia
# ==========================================================
@ws_progreso.route('/por_competencia', methods=['GET'])
def progreso_por_competencia():
    id_estudiante = request.args.get('idEstudiante', type=int)
    if not id_estudiante:
        return jsonify({"status": False, "mensaje": "idEstudiante es obligatorio"}), 400

    con = Conexion()
    cur = con.cursor()

    PESO_NUEVO = 1.0
    PESO_REPETIDO = 0.30

    try:
        cur.execute("""
            SELECT
                c.id_competencia,
                c.descripcion,

                COUNT(DISTINCT e.id_ejercicio) AS total,
                
                COUNT(DISTINCT CASE WHEN o.es_correcta = TRUE THEN r.id_ejercicio END)
                AS distintos_correctos,

                COUNT(CASE WHEN o.es_correcta = TRUE THEN 1 END)
                AS correctos_totales

            FROM competencias c
            LEFT JOIN ejercicios e
                ON e.id_competencia = c.id_competencia
            LEFT JOIN respuestas_estudiantes r
                ON r.id_ejercicio = e.id_ejercicio
               AND r.id_estudiante = %s
            LEFT JOIN opciones_ejercicio o
                ON o.id_opcion = r.id_opcion
            WHERE c.id_competencia BETWEEN 1 AND 4
            GROUP BY c.id_competencia, c.descripcion
            ORDER BY c.id_competencia
        """, (id_estudiante,))

        filas = cur.fetchall()
        temas = []

        for f in filas:
            total = f["total"]
            d_correctos = f["distintos_correctos"]
            t_correctos = f["correctos_totales"]

            repetidos = max(0, t_correctos - d_correctos)

            if total > 0:
                puntaje = (
                    d_correctos * PESO_NUEVO +
                    repetidos * PESO_REPETIDO
                ) / total
            else:
                puntaje = 0

            porcentaje = min(100, max(0, round(puntaje * 100)))

            temas.append({
                "idCompetencia": f["id_competencia"],
                "nombre": f["descripcion"],
                "porcentaje": porcentaje
            })

        return jsonify({"status": True, "temas": temas})

    except Exception as e:
        return jsonify({"status": False, "mensaje": str(e)}), 500
    finally:
        cur.close()
        con.close()
# ==========================================================
#  GET /progreso/historial (CTO-HIST-V2)
#  Historial real: estado, fecha, desarrollo, intentos
# ==========================================================
@ws_progreso.route('/historial', methods=['GET'])
def historial():
    id_estudiante = request.args.get('idEstudiante', type=int)
    if not id_estudiante:
        return jsonify({"status": False, "mensaje": "idEstudiante es obligatorio"}), 400

    con = Conexion()
    cur = con.cursor()

    try:
        cur.execute("""
            SELECT
                p.id_progreso,
                p.fecha,
                p.estado,
                p.id_ejercicio,
                e.descripcion AS ejercicio,
                r.desarrollo_url,

                (
                    SELECT COUNT(*)
                    FROM respuestas_estudiantes r2
                    JOIN opciones_ejercicio o2 ON o2.id_opcion = r2.id_opcion
                    WHERE r2.id_ejercicio = p.id_ejercicio
                    AND r2.id_estudiante = %s
                    AND o2.es_correcta = FALSE
                ) AS intentos_incorrectos

            FROM progreso p
            JOIN ejercicios e ON e.id_ejercicio = p.id_ejercicio
            LEFT JOIN respuestas_estudiantes r
                ON r.id_ejercicio = p.id_ejercicio
               AND r.id_estudiante = %s
            WHERE p.id_estudiante = %s
            ORDER BY p.id_progreso DESC
            LIMIT 5
        """, (id_estudiante, id_estudiante, id_estudiante))

        filas = cur.fetchall()
        items = []

        for f in filas:
            items.append({
                "idProgreso": f["id_progreso"],
                "fecha": f["fecha"].strftime("%d/%m/%Y %H:%M"),
                "idEjercicio": f["id_ejercicio"],
                "titulo": f"Ejercicio: {f['ejercicio']}",
                "estado": f["estado"],
                "intentosIncorrectos": f["intentos_incorrectos"],
                "desarrolloUrl": f["desarrollo_url"]
            })

        return jsonify({"status": True, "items": items})

    except Exception as e:
        return jsonify({"status": False, "mensaje": str(e)}), 500

    finally:
        cur.close()
        con.close()
