# ws/docente_salon.py
from flask import Blueprint, request, jsonify
from conexionBD import Conexion
from flask_jwt_extended import jwt_required
import json

ws_docente_salon = Blueprint('ws_docente_salon', __name__)

# ============================
# 1) Asignar docente a salón
#    POST /docente_salon
#    body: { "id_docente": 1, "id_salon": 2 }
# ============================
@ws_docente_salon.route('/docente_salon', methods=['POST'])
def asignar_docente():
    data = request.get_json() or {}
    id_docente = data.get('id_docente')
    id_salon = data.get('id_salon')

    if not id_docente or not id_salon:
        return jsonify({"status": False, "message": "Faltan parámetros"}), 400

    try:
        from models.DocenteSalon import DocenteSalon
        return jsonify(json.loads(DocenteSalon.asignar(id_docente, id_salon)))
    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500


# ============================
# 2) Listar asignaciones
#    GET /docente_salon
# ============================
@ws_docente_salon.route('/docente_salon', methods=['GET'])
def listar_docentes_salones():
    try:
        from models.DocenteSalon import DocenteSalon
        return jsonify(json.loads(DocenteSalon.listar()))
    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500


# ============================
# 3) Eliminar asignación
#    DELETE /docente_salon/<id_docente>/<id_salon>
# ============================
@ws_docente_salon.route('/docente_salon/<int:id_docente>/<int:id_salon>', methods=['DELETE'])
def eliminar_asignacion(id_docente, id_salon):
    try:
        from models.DocenteSalon import DocenteSalon
        return jsonify(json.loads(DocenteSalon.eliminar(id_docente, id_salon)))
    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500


# ============================
# 4) Estudiantes de un docente
#    GET /docentes/<id_docente>/estudiantes
#    (para TeacherReportsActivity, lista de alumnos del docente)
# ============================
@ws_docente_salon.route('/docentes/<int:id_docente>/estudiantes', methods=['GET'])
@jwt_required()
def docentes_estudiantes(id_docente: int):
    """
    Devuelve todos los estudiantes pertenecientes a los salones del docente.
    Compatible con TeacherStudentsDTO en Android.
    """
    con = Conexion()
    cur = con.cursor()
    try:
        cur.execute("""
            SELECT
                e.id_estudiante,
                u.nombre || ' ' || u.apellidos AS nombre,
                COALESCE(e.progreso_general, 0) AS progreso
            FROM docente d
            JOIN docente_salones ds
                ON ds.id_docente = d.id_docente
            JOIN salones s
                ON s.id_salon = ds.id_salon
            JOIN estudiante_salones es
                ON es.id_salon = s.id_salon
            JOIN estudiante e
                ON e.id_estudiante = es.id_estudiante
            JOIN usuarios u
                ON u.id_usuario = e.id_usuario
            WHERE d.id_docente = %s
              AND e.estado_estudiante = 'activo'
            ORDER BY nombre;
        """, (id_docente,))

        rows = cur.fetchall() or []

        data = []
        for r in rows:
            # Si tu cursor es tipo diccionario (lo normal en tu Conexion),
            # r["id_estudiante"] / r["nombre"] / r["progreso"] funcionarán.
            # Por si acaso, soportamos también tupla.
            if isinstance(r, dict):
                id_est = r.get("id_estudiante")
                nombre = r.get("nombre")
                progreso = r.get("progreso", 0)
            else:
                id_est = r[0]
                nombre = r[1]
                progreso = r[2]

            data.append({
                "id_estudiante": int(id_est),
                "nombre": nombre,
                "progreso": int(progreso or 0),
            })

        return jsonify({"status": True, "data": data}), 200

    except Exception as e:
        print("ERROR EN /docentes/<id_docente>/estudiantes:", e)
        return jsonify({"status": False, "message": str(e)}), 500
    finally:
        try:
            cur.close()
            con.close()
        except:
            pass
