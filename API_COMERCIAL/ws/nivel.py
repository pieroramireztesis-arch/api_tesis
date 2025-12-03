from flask import Blueprint, request, jsonify
from models.Nivel import Nivel
import json

ws_nivel = Blueprint('ws_nivel', __name__, url_prefix='/nivel')

# Crear un nuevo nivel
@ws_nivel.route('', methods=['POST'])
def registrar_nivel():
    data = request.get_json()
    return jsonify(json.loads(Nivel.registrar(data['nombre_nivel'], data['descripcion'])))

# Listar todos los niveles
@ws_nivel.route('', methods=['GET'])
def listar_niveles():
    return jsonify(json.loads(Nivel.listar_todos()))

# Actualizar un nivel
@ws_nivel.route('/<int:id_nivel>', methods=['PUT'])
def actualizar_nivel(id_nivel):
    data = request.get_json()
    return jsonify(json.loads(Nivel.actualizar(id_nivel, data)))

# Eliminar un nivel
@ws_nivel.route('/<int:id_nivel>', methods=['DELETE'])
def eliminar_nivel(id_nivel):
    return jsonify(json.loads(Nivel.eliminar(id_nivel)))
