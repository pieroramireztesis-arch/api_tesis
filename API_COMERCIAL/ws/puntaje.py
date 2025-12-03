from flask import Blueprint, request, jsonify
from models.Puntaje import Puntaje
import json
from conexionBD import Conexion
import datetime

ws_puntaje = Blueprint('ws_puntaje', __name__, url_prefix='/puntaje')

# Listar todos los puntajes
@ws_puntaje.route('', methods=['GET'])
@ws_puntaje.route('/', methods=['GET'])
def listar_puntajes():
    return jsonify(json.loads(Puntaje.listar()))

# Obtener puntajes por estudiante
@ws_puntaje.route('/<int:id_estudiante>', methods=['GET'])
def obtener_puntaje(id_estudiante):
    return jsonify(json.loads(Puntaje.obtener_por_estudiante(id_estudiante)))

# Crear puntaje manualmente
@ws_puntaje.route('', methods=['POST'])
def crear_puntaje():
    data = request.get_json()
    if not data or 'id_estudiante' not in data or 'id_competencia' not in data or 'puntaje' not in data:
        return jsonify({'status': False, 'message': 'Faltan parámetros'})
    
    con = Conexion()
    cursor = con.cursor()
    try:
        sql = """
            INSERT INTO puntajes (puntaje, fecha_registro, id_competencia, id_estudiante)
            VALUES (%s, %s, %s, %s) RETURNING id_puntaje;
        """
        cursor.execute(sql, (data['puntaje'], datetime.datetime.now(), data['id_competencia'], data['id_estudiante']))
        nuevo_id = cursor.fetchone()['id_puntaje']
        con.commit()
        return jsonify({'status': True, 'message': 'Puntaje creado', 'id_puntaje': nuevo_id})
    except Exception as e:
        return jsonify({'status': False, 'message': str(e)})
    finally:
        cursor.close()
        con.close()

# Actualizar puntaje manualmente
@ws_puntaje.route('/<int:id_puntaje>', methods=['PUT'])
def actualizar_puntaje(id_puntaje):
    data = request.get_json()
    if not data or 'puntaje' not in data:
        return jsonify({'status': False, 'message': 'Faltan parámetros'})
    
    con = Conexion()
    cursor = con.cursor()
    try:
        sql = """
            UPDATE puntajes
            SET puntaje = %s, fecha_registro = %s
            WHERE id_puntaje = %s;
        """
        cursor.execute(sql, (data['puntaje'], datetime.datetime.now(), id_puntaje))
        con.commit()
        return jsonify({'status': True, 'message': 'Puntaje actualizado'})
    except Exception as e:
        return jsonify({'status': False, 'message': str(e)})
    finally:
        cursor.close()
        con.close()
