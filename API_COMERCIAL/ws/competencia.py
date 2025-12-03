from flask import Blueprint, request, jsonify
from models.Competencia import Competencia
import json

ws_competencia = Blueprint('ws_competencia', __name__)

# Crear competencia
@ws_competencia.route('/competencias', methods=['POST'])
def crear_competencia():
    data = request.get_json()
    if not data or 'descripcion' not in data or 'nivel' not in data:
        return jsonify({'status': False, 'message': 'Faltan parámetros'})
    obj = Competencia(descripcion=data['descripcion'], nivel=data['nivel'])
    return jsonify(json.loads(obj.crear()))

# Listar competencias
@ws_competencia.route('/competencias', methods=['GET'])
def listar_competencias():
    return jsonify(json.loads(Competencia.listar()))

# Obtener competencia por id
@ws_competencia.route('/competencias/<int:id_competencia>', methods=['GET'])
def obtener_competencia(id_competencia):
    return jsonify(json.loads(Competencia.obtener(id_competencia)))

# Actualizar competencia
@ws_competencia.route('/competencias/<int:id_competencia>', methods=['PUT'])
def actualizar_competencia(id_competencia):
    data = request.get_json()
    if not data or 'descripcion' not in data or 'nivel' not in data:
        return jsonify({'status': False, 'message': 'Faltan parámetros'})
    obj = Competencia(id_competencia=id_competencia, descripcion=data['descripcion'], nivel=data['nivel'])
    return jsonify(json.loads(obj.actualizar()))

# Eliminar competencia
@ws_competencia.route('/competencias/<int:id_competencia>', methods=['DELETE'])
def eliminar_competencia(id_competencia):
    return jsonify(json.loads(Competencia.eliminar(id_competencia)))
