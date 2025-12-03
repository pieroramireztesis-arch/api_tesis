from flask import Blueprint, request, jsonify
from models.HistorialMaterial import HistorialMaterial
import json

ws_historial_material = Blueprint('ws_historial_material', __name__, url_prefix='/historial_material')

# Crear nuevo historial
@ws_historial_material.route('', methods=['POST'])
def registrar_historial():
    data = request.get_json()
    return jsonify(json.loads(HistorialMaterial.registrar(
        data['id_estudiante'],
        data['id_material'],
        data['estado'],
        data['tiempo_visto'],
        data['veces_revisado']
    )))

# Listar todos los historiales
@ws_historial_material.route('', methods=['GET'])
def listar_todos():
    return jsonify(json.loads(HistorialMaterial.listar_todos()))

# Listar historial de un estudiante específico
@ws_historial_material.route('/<int:id_estudiante>', methods=['GET'])
def listar_historial(id_estudiante):
    return jsonify(json.loads(HistorialMaterial.listar(id_estudiante)))

# Actualizar historial
@ws_historial_material.route('/<int:id_historial>', methods=['PUT'])
def actualizar_historial(id_historial):
    data = request.get_json()
    return jsonify(json.loads(HistorialMaterial.actualizar(id_historial, data)))
