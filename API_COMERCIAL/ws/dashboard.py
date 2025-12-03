from flask import Blueprint, jsonify
from conexionBD import Conexion
from models.Progreso import Progreso
import json

ws_dashboard = Blueprint('ws_dashboard', __name__, url_prefix='/dashboard')


@ws_dashboard.route('/mini/<int:id_estudiante>', methods=['GET'])
def mini_dashboard(id_estudiante: int):
    con = Conexion()
    cur = con.cursor()
    try:
        # 1) Saludo (nombre)
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
        #    Usamos Progreso.listar(id_estudiante) para contar cuántos
        #    ejercicios están correctos sobre el total.
        lista_json = Progreso.listar(id_estudiante)  # string JSON
        payload = json.loads(lista_json)

        items = payload.get('data', []) if payload.get('status', False) else []
        total = len(items)
        correctas = sum(
            1 for p in items
            if str(p.get('estado', '')).lower().startswith('correcto')
        )
        progreso_general = int(round((correctas / total) * 100)) if total > 0 else 0

        # 3) Promedio general de puntajes (0..100)
        cur.execute("""
            SELECT COALESCE(ROUND(AVG(puntaje)), 0)::int AS promedio
            FROM puntajes
            WHERE id_estudiante = %s
        """, (id_estudiante,))
        row = cur.fetchone() or {}
        promedio = row.get('promedio', 0) or 0

        # 4) % por competencia (MISMA LÓGICA QUE /progreso/por_competencia)
        cur.execute("""
            SELECT
                c.id_competencia,
                c.descripcion,
                AVG(p.puntaje) AS promedio
            FROM competencias c
            LEFT JOIN puntajes p
                   ON p.id_competencia = c.id_competencia
                  AND p.id_estudiante = %s
            -- Si quieres forzar solo las 4 competencias MINEDU, descomenta:
            -- WHERE c.id_competencia BETWEEN 1 AND 4
            GROUP BY c.id_competencia, c.descripcion
            ORDER BY c.id_competencia
        """, (id_estudiante,))
        temas_rows = cur.fetchall() or []

        temas = []
        for r in temas_rows:
            prom = r.get("promedio")
            if prom is None:
                pct = 0
            else:
                pct = int(round(prom))
            temas.append({
                "nombre": r["descripcion"],
                "porcentaje": pct
            })

        return jsonify({
            "saludo": saludo,
            "progresoGeneral": progreso_general,  # 👉 Este es el 44% que ves en "Mi Progreso"
            "promedio": int(promedio),
            "temas": temas
        })

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
            # Lo convertimos en un texto que encaje con:
            # "<nombre> ha ${item.tipo} \"${item.tema}\""
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

        # RESPUESTA FINAL
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
