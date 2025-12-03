from flask import Blueprint, request, jsonify
from models.Sesion import Sesion
import json
import jwt
import datetime
from config import SecretKey

# Crear blueprint
ws_sesion = Blueprint('ws_sesion', __name__)

# Endpoint de login
@ws_sesion.route('/usuario/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'correo' not in data or 'contrasena' not in data:
        return jsonify({'status': False, 'message': 'Faltan parámetros'})

    # Llamar al modelo
    obj = Sesion(data['correo'], data['contrasena'])
    resultado = obj.iniciarSesion()
    res_json = json.loads(resultado)

    # Generar token si todo está OK
    if res_json['status']:
        token = jwt.encode({
            'correo': data['correo'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        }, SecretKey.JWT_SECRET_KEY, algorithm="HS256")

        res_json['token'] = token

    return jsonify(res_json)
