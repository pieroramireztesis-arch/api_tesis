from flask import Blueprint, request, jsonify
from models.Estudiante import Estudiante
import json

ws_estudiante = Blueprint('ws_estudiante', __name__)

# =========================================================
# 1. CREAR ESTUDIANTE
# =========================================================
@ws_estudiante.route('/estudiantes', methods=['POST'])
def crear_estudiante():
    data = request.get_json()
    if not data or 'grado' not in data or 'id_usuario' not in data:
        return jsonify({'status': False, 'message': 'Faltan parámetros'})
    
    obj = Estudiante(
        grado=data['grado'],
        id_usuario=data['id_usuario']
    )
    return jsonify(json.loads(obj.crear()))

# =========================================================
# 2. LISTAR ESTUDIANTES
# =========================================================
@ws_estudiante.route('/estudiantes', methods=['GET'])
def listar_estudiantes():
    return jsonify(json.loads(Estudiante.listar()))

# =========================================================
# 3. OBTENER ESTUDIANTE POR ID
# =========================================================
@ws_estudiante.route('/estudiantes/<int:id_estudiante>', methods=['GET'])
def obtener_estudiante(id_estudiante):
    return jsonify(json.loads(Estudiante.obtener(id_estudiante)))

# =========================================================
# 4. ACTUALIZAR ESTUDIANTE
# =========================================================
@ws_estudiante.route('/estudiantes/<int:id_estudiante>', methods=['PUT'])
def actualizar_estudiante(id_estudiante):
    data = request.get_json()
    if not data or 'grado' not in data:
        return jsonify({'status': False, 'message': 'Faltan parámetros'})
    
    obj = Estudiante(
        id_estudiante=id_estudiante,
        grado=data['grado']
    )
    return jsonify(json.loads(obj.actualizar()))

# =========================================================
# 5. ELIMINAR ESTUDIANTE
# =========================================================
@ws_estudiante.route('/estudiantes/<int:id_estudiante>', methods=['DELETE'])
def eliminar_estudiante(id_estudiante):
    return jsonify(json.loads(Estudiante.eliminar(id_estudiante)))

# =========================================================
# 6. NUEVO: OBTENER ESTUDIANTE POR ID_USUARIO
#    /estudiantes/por-usuario/<id_usuario>
# =========================================================
@ws_estudiante.route('/estudiantes/por-usuario/<int:id_usuario>', methods=['GET'])
def estudiante_por_usuario(id_usuario):
    from conexionBD import Conexion
    con = Conexion()
    cur = con.cursor()

    try:
        cur.execute("""
            SELECT 
                e.id_estudiante,
                e.grado,
                e.estado_estudiante,
                e.id_usuario
            FROM estudiante e
            JOIN usuarios u ON u.id_usuario = e.id_usuario
            WHERE e.id_usuario = %s
        """, (id_usuario,))

        row = cur.fetchone()

        if not row:
            return jsonify({
                'status': False,
                'message': 'No se encontró estudiante para ese usuario'
            }), 404

        return jsonify({'status': True, 'data': row}), 200

    except Exception as e:
        return jsonify({'status': False, 'message': str(e)}), 500

    finally:
        cur.close()
        con.close()
