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


# NOTA: GET /docentes/<id_docente>/estudiantes está implementado en ws/docente.py
# (eliminado aquí para evitar conflicto de rutas en Flask)
