# ws/docente.py
from flask import Blueprint, request, jsonify
from models.Docente import Docente
import json

ws_docente = Blueprint('ws_docente', __name__)

# ========================================
# CRUD BÁSICO DE DOCENTES
# ========================================

@ws_docente.route('/docentes', methods=['POST'])
def crear_docente():
    data = request.get_json() or {}
    if 'especialidad' not in data or 'id_usuario' not in data:
        return jsonify({'status': False, 'message': 'Faltan parámetros'})
    obj = Docente(especialidad=data['especialidad'], id_usuario=data['id_usuario'])
    return jsonify(json.loads(obj.crear()))


@ws_docente.route('/docentes', methods=['GET'])
def listar_docentes():
    return jsonify(json.loads(Docente.listar()))


@ws_docente.route('/docentes/<int:id_docente>', methods=['GET'])
def obtener_docente(id_docente):
    return jsonify(json.loads(Docente.obtener(id_docente)))


@ws_docente.route('/docentes/<int:id_docente>', methods=['PUT'])
def actualizar_docente(id_docente):
    data = request.get_json() or {}
    if 'especialidad' not in data:
        return jsonify({'status': False, 'message': 'Faltan parámetros'})
    obj = Docente(id_docente=id_docente, especialidad=data['especialidad'])
    return jsonify(json.loads(obj.actualizar()))


@ws_docente.route('/docentes/<int:id_docente>', methods=['DELETE'])
def eliminar_docente(id_docente):
    return jsonify(json.loads(Docente.eliminar(id_docente)))


# ========================================
# DASHBOARD DEL DOCENTE
# GET /docentes/<id_docente>/dashboard
# ========================================

@ws_docente.route('/docentes/<int:id_docente>/dashboard', methods=['GET'])
def docentes_dashboard(id_docente):
    return jsonify(json.loads(Docente.dashboard(id_docente)))
