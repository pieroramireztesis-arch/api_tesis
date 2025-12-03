from flask import Blueprint, request, jsonify
from models.Respuesta import Respuesta
from models.Puntaje import Puntaje
import json
from conexionBD import Conexion

ws_respuesta = Blueprint('ws_respuesta', __name__)

# Crear respuesta
@ws_respuesta.route('/respuestas', methods=['POST'])
def crear_respuesta():
    data = request.get_json()
    if not data or 'respuesta_texto' not in data or 'id_estudiante' not in data or 'id_ejercicio' not in data or 'id_opcion' not in data:
        return jsonify({'status': False, 'message': 'Faltan parámetros'})

    obj = Respuesta(
        respuesta_texto=data['respuesta_texto'],
        id_estudiante=data['id_estudiante'],
        id_ejercicio=data['id_ejercicio'],
        id_opcion=data['id_opcion']
    )

    # Registrar respuesta
    resultado = json.loads(obj.crear())

    # Si la respuesta se registró correctamente, actualizar puntaje
    if resultado['status']:
        Puntaje.actualizar_puntaje(
            id_estudiante=data['id_estudiante'],
            id_ejercicio=data['id_ejercicio'],
            id_opcion=data['id_opcion']
        )
        resultado['message'] += ' y puntaje actualizado'

    return jsonify(resultado)


# Listar respuestas
@ws_respuesta.route('/respuestas', methods=['GET'])
def listar_respuestas():
    return jsonify(json.loads(Respuesta.listar()))


# Obtener respuesta por id
@ws_respuesta.route('/respuestas/<int:id_respuesta>', methods=['GET'])
def obtener_respuesta(id_respuesta):
    return jsonify(json.loads(Respuesta.obtener(id_respuesta)))


# Eliminar respuesta
@ws_respuesta.route('/respuestas/<int:id_respuesta>', methods=['DELETE'])
def eliminar_respuesta(id_respuesta):
    return jsonify(json.loads(Respuesta.eliminar(id_respuesta)))


# Actualizar respuesta
@ws_respuesta.route('/respuestas/<int:id_respuesta>', methods=['PUT'])
def actualizar_respuesta(id_respuesta):
    data = request.get_json()
    if not data or 'respuesta_texto' not in data or 'id_opcion' not in data or 'id_estudiante' not in data or 'id_ejercicio' not in data:
        return jsonify({'status': False, 'message': 'Faltan parámetros'})

    con = Conexion()
    cursor = con.cursor()
    try:
        sql = """
            UPDATE respuestas_estudiantes
            SET respuesta_texto = %s, id_opcion = %s, fecha = NOW()
            WHERE id_respuesta = %s;
        """
        cursor.execute(sql, (
            data['respuesta_texto'],
            data['id_opcion'],
            id_respuesta
        ))
        con.commit()

        # actualizar puntaje después de la edición
        Puntaje.actualizar_puntaje(
            id_estudiante=data['id_estudiante'],
            id_ejercicio=data['id_ejercicio'],
            id_opcion=data['id_opcion']
        )

        return jsonify({'status': True, 'message': 'Respuesta y puntaje actualizados'})
    except Exception as e:
        return jsonify({'status': False, 'message': str(e)})
    finally:
        cursor.close()
        con.close()