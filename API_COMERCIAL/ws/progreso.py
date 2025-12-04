from flask import Blueprint, request, jsonify
from models.Progreso import Progreso
from conexionBD import Conexion
import json

ws_progreso = Blueprint('ws_progreso', __name__, url_prefix='/progreso')


# ==========================
#  POST /progreso
#  Registrar progreso (si se usa)
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
            return jsonify({
                "status": False,
                "mensaje": "Faltan campos obligatorios"
            }), 400

        resp = Progreso.registrar(
            id_estudiante,
            id_ejercicio,
            nivel_actual,
            estado,
            tiempo_respuesta
        )
        return jsonify(json.loads(resp))

    except Exception as e:
        return jsonify({
            "status": False,
            "mensaje": str(e)
        }), 500


# ==========================
#  GET /progreso
#  Listar todos
# ==========================
@ws_progreso.route('', methods=['GET'])
def listar_progreso():
    try:
        return jsonify(json.loads(Progreso.listar_todos()))
    except Exception as e:
        return jsonify({
            "status": False,
            "mensaje": str(e)
        }), 500


# ==========================
#  GET /progreso/resumen?idEstudiante=4
#  Resumen global basado en EJERCICIOS COMPLETADOS
# ==========================
@ws_progreso.route('/resumen', methods=['GET'])
def resumen_progreso():
    """
    Parámetro:
      - idEstudiante (query) -> obligatorio

    Nueva lógica:
      - ejerciciosDesarrollados = # de ejercicios distintos que el estudiante ha respondido
        (en las competencias 1..4)
      - nivelPorcentaje = (ejerciciosDesarrollados / ejerciciosTotales) * 100

    Respuesta:
      {
        "ejerciciosDesarrollados": int,
        "nivelPorcentaje": int,   # 0..100
        "resumenTexto": str,
        "status": true/false
      }
    """
    id_estudiante = request.args.get('idEstudiante', type=int)
    if not id_estudiante:
        return jsonify({
            "status": False,
            "mensaje": "idEstudiante es obligatorio"
        }), 400

    con = Conexion()
    cur = con.cursor()

    try:
        # Total de ejercicios disponibles (competencias MINEDU 1..4)
        # y cuántos de ellos ya ha resuelto el estudiante.
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

        row = cur.fetchone() or {}
        total = row.get("total_ejercicios", 0) or 0
        resueltos = row.get("resueltos", 0) or 0

        if total > 0:
            porcentaje = int(round(100.0 * float(resueltos) / float(total)))
        else:
            porcentaje = 0

        if porcentaje < 0:
            porcentaje = 0
        if porcentaje > 100:
            porcentaje = 100

        # Mensaje tipo semáforo según porcentaje de COMPLETITUD
        if porcentaje >= 80:
            resumen = "¡Excelente! Has completado casi todos los ejercicios."
        elif porcentaje >= 50:
            resumen = "Vas bien, aún puedes mejorar."
        elif porcentaje > 0:
            resumen = "Estás avanzando, sigue practicando."
        else:
            resumen = "Aún no has empezado a resolver ejercicios."

        return jsonify({
            "ejerciciosDesarrollados": int(resueltos),
            "nivelPorcentaje": porcentaje,
            "resumenTexto": resumen,
            "status": True
        }), 200

    except Exception as e:
        print("Error en /progreso/resumen:", str(e))
        return jsonify({
            "ejerciciosDesarrollados": 0,
            "nivelPorcentaje": 0,
            "resumenTexto": "Error al calcular el progreso.",
            "status": False,
            "mensaje": str(e)
        }), 500
    finally:
        cur.close()
        con.close()


# ==========================
#  GET /progreso/por_competencia?idEstudiante=4
#  Porcentaje de COMPLETITUD por competencia MINEDU (0..100)
# ==========================
@ws_progreso.route('/por_competencia', methods=['GET'])
def progreso_por_competencia():
    """
    Devuelve el porcentaje de ejercicios completados por competencia del estudiante,
    basado en:
      - ejercicios: total de ejercicios por competencia
      - respuestas_estudiantes: ejercicios que el estudiante ya resolvió

    Respuesta:
    {
      "status": true,
      "temas": [
        {"idCompetencia": 1, "nombre": "Resuelve problemas de cantidad", "porcentaje": 60},
        {"idCompetencia": 2, "nombre": "Resuelve problemas de regularidad, equivalencia y cambio", "porcentaje": 40},
        ...
      ]
    }
    """
    id_estudiante = request.args.get('idEstudiante', type=int)
    if not id_estudiante:
        return jsonify({
            "status": False,
            "mensaje": "idEstudiante es obligatorio"
        }), 400

    con = Conexion()
    cursor = con.cursor()

    try:
        # Para cada competencia:
        #   total = # ejercicios en esa competencia
        #   resueltos = # ejercicios de esa competencia que el estudiante ha respondido
        cursor.execute("""
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

        rows = cursor.fetchall() or []
        temas = []

        for row in rows:
            total = row.get("total_ejercicios") or 0
            resueltos = row.get("resueltos") or 0

            if total > 0:
                pct = int(round(100.0 * float(resueltos) / float(total)))
            else:
                pct = 0

            if pct < 0:
                pct = 0
            if pct > 100:
                pct = 100

            temas.append({
                "idCompetencia": row["id_competencia"],
                "nombre": row["descripcion"],
                "porcentaje": pct
            })

        return jsonify({
            "status": True,
            "temas": temas
        }), 200

    except Exception as e:
        print("Error en /progreso/por_competencia:", str(e))
        return jsonify({
            "status": False,
            "mensaje": str(e)
        }), 500
    finally:
        cursor.close()
        con.close()


# ==========================
#  GET /progreso/historial?idEstudiante=4
#  Últimas 3 actividades del estudiante
# ==========================
@ws_progreso.route('/historial', methods=['GET'])
def historial_progreso():
    """
    Devuelve las últimas 3 actividades del estudiante.

    Respuesta:
    {
      "status": true,
      "items": [
        {
          "idProgreso": 10,
          "idEjercicio": 5,
          "titulo": "Ejercicio: Simplificar polinomios",
          "subtitulo": "Resultado: correcto"
        },
        ...
      ]
    }
    """
    id_estudiante = request.args.get('idEstudiante', type=int)
    if not id_estudiante:
        return jsonify({
            "status": False,
            "mensaje": "idEstudiante es obligatorio"
        }), 400

    con = Conexion()
    cur = con.cursor()

    try:
        cur.execute("""
            SELECT
                p.id_progreso,
                p.id_ejercicio,
                e.descripcion     AS ejercicio,
                p.estado
            FROM progreso p
            JOIN ejercicios e ON e.id_ejercicio = p.id_ejercicio
            WHERE p.id_estudiante = %s
            ORDER BY p.id_progreso DESC
            LIMIT 3
        """, (id_estudiante,))

        rows = cur.fetchall() or []
        items = []

        for r in rows:
            estado = (r.get("estado") or "").strip().lower()
            if estado.startswith("correcto"):
                subtitulo = "Resultado: correcto"
            elif estado.startswith("incorrecto"):
                subtitulo = "Resultado: incorrecto"
            else:
                subtitulo = f"Estado: {r.get('estado') or 'sin datos'}"

            items.append({
                "idProgreso": r["id_progreso"],
                "idEjercicio": r["id_ejercicio"],
                "titulo": f"Ejercicio: {r['ejercicio']}",
                "subtitulo": subtitulo
            })

        return jsonify({
            "status": True,
            "items": items
        }), 200

    except Exception as e:
        print("Error en /progreso/historial:", str(e))
        return jsonify({
            "status": False,
            "mensaje": str(e)
        }), 500
    finally:
        cur.close()
        con.close()


# ==========================
#  DELETE /progreso/<id>
# ==========================
@ws_progreso.route('/<int:id_progreso>', methods=['DELETE'])
def eliminar_progreso(id_progreso):
    try:
        return jsonify(json.loads(Progreso.eliminar(id_progreso)))
    except Exception as e:
        return jsonify({
            "status": False,
            "mensaje": str(e)
        }), 500
