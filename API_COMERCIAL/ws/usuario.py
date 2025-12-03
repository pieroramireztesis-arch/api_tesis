from flask import Blueprint, request, jsonify
from models.Usuario import Usuario
from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash, generate_password_hash
import json

ws_usuario = Blueprint('ws_usuario', __name__)


# =========================================================
# 0. LOGIN DE USUARIO  (USADO POR ANDROID: POST /usuario/login)
# =========================================================
@ws_usuario.route('/usuario/login', methods=['POST'])
def login_usuario():
    from conexionBD import Conexion
    data = request.get_json() or {}

    correo = (data.get('correo') or '').strip()
    contrasena = (data.get('contrasena') or '').strip()

    if not correo or not contrasena:
        return jsonify({
            "status": False,
            "message": "Correo y contraseña son obligatorios"
        }), 400

    con = Conexion()
    cur = con.cursor()

    try:
        print("LOGIN:", correo, contrasena)

        cur.execute("""
            SELECT 
                u.id_usuario,
                u.nombre,
                u.apellidos,
                u.correo,
                u.rol,
                u.estado_usuario,
                e.id_estudiante,
                d.id_docente,
                u.contrasena
            FROM usuarios u
            LEFT JOIN estudiante e ON e.id_usuario = u.id_usuario
            LEFT JOIN docente   d ON d.id_usuario = u.id_usuario
            WHERE u.correo = %s
        """, (correo,))

        row = cur.fetchone()
        print("SQL RESULT:", row)

        if not row:
            return jsonify({
                "status": False,
                "message": "Correo no encontrado"
            }), 401

        if row["estado_usuario"] != 'activo':
            return jsonify({
                "status": False,
                "message": "Usuario inactivo"
            }), 403

        password_db = row["contrasena"]

        # 🔐 Comparar contra el hash almacenado
        if (not password_db) or (not check_password_hash(password_db, contrasena)):
            return jsonify({
                "status": False,
                "message": "Contraseña incorrecta"
            }), 401

        id_usuario    = row["id_usuario"]
        nombre        = row["nombre"]
        apellidos     = row["apellidos"]
        correo_db     = row["correo"]
        rol           = row["rol"]
        estado        = row["estado_usuario"]
        id_estudiante = row["id_estudiante"]
        id_docente    = row["id_docente"]

        additional_claims = {
            "correo": correo_db,
            "rol": rol,
            "id_docente": id_docente,
            "id_estudiante": id_estudiante
        }

        access_token = create_access_token(
            identity=str(id_usuario),          # ✅ string
            additional_claims=additional_claims
        )

        return jsonify({
            "status": True,
            "message": "Inicio de sesión satisfactorio. Bienvenido al sistema",
            "token": access_token,
            "data": {
                "id_usuario": id_usuario,
                "nombre": nombre,
                "apellidos": apellidos,
                "correo": correo_db,
                "rol": rol,
                "estado_usuario": estado,
                "id_estudiante": id_estudiante,
                "id_docente": id_docente
            }
        }), 200

    except Exception as e:
        print("ERROR LOGIN:", e)
        return jsonify({
            "status": False,
            "message": str(e)
        }), 500

    finally:
        cur.close()
        con.close()


# =========================================================
# 4. ACTUALIZAR USUARIO (PUT /usuarios/<id_usuario>)
# =========================================================
@ws_usuario.route('/usuarios/<int:id_usuario>', methods=['PUT'])
def actualizar_usuario(id_usuario):
    data = request.get_json()
    if not data or 'nombre' not in data or 'apellidos' not in data or 'correo' not in data or 'rol' not in data or 'estado_usuario' not in data:
        return jsonify({'status': False, 'message': 'Faltan parámetros'})

    obj = Usuario(
        id_usuario=id_usuario,
        nombre=data['nombre'],
        apellidos=data['apellidos'],
        correo=data['correo'],
        rol=data['rol'],
        estado_usuario=data['estado_usuario']
    )
    return jsonify(json.loads(obj.actualizar()))


# =========================================================
# 4A. OBTENER USUARIO POR ID (GET /usuarios/<id_usuario>)
#      -> LO QUE USA ProfileFragment (RetrofitClient.api.getUsuario)
# =========================================================
@ws_usuario.route('/usuarios/<int:id_usuario>', methods=['GET'])
def obtener_usuario(id_usuario):
    from conexionBD import Conexion
    con = Conexion()
    cur = con.cursor()

    try:
        cur.execute("""
            SELECT id_usuario, nombre, apellidos, correo, rol, estado_usuario
            FROM usuarios
            WHERE id_usuario = %s
        """, (id_usuario,))

        row = cur.fetchone()

        if not row:
            return jsonify({'status': False, 'message': 'Usuario no encontrado'}), 404

        return jsonify({'status': True, 'data': row}), 200

    except Exception as e:
        return jsonify({'status': False, 'message': str(e)}), 500

    finally:
        cur.close()
        con.close()


# =========================================================
# 5. ELIMINAR USUARIO
# =========================================================
@ws_usuario.route('/usuarios/<int:id_usuario>', methods=['DELETE'])
def eliminar_usuario(id_usuario):
    return jsonify(json.loads(Usuario.eliminar(id_usuario)))


# =========================================================
# 6. OBTENER USUARIO DESDE ID_ESTUDIANTE
# =========================================================
@ws_usuario.route('/usuarios/por-estudiante/<int:id_estudiante>', methods=['GET'])
def usuario_por_estudiante(id_estudiante):
    from conexionBD import Conexion
    con = Conexion()
    cur = con.cursor()

    try:
        cur.execute("""
            SELECT u.id_usuario, u.nombre, u.apellidos, u.correo, u.rol, u.estado_usuario
            FROM usuarios u
            JOIN estudiante e ON e.id_usuario = u.id_usuario
            WHERE e.id_estudiante = %s
        """, (id_estudiante,))

        row = cur.fetchone()

        if row:
            return jsonify({'status': True, 'data': row})

        return jsonify({'status': False, 'message': 'No encontrado'})

    except Exception as e:
        return jsonify({'status': False, 'message': str(e)})

    finally:
        cur.close()
        con.close()


# =========================================================
# 7. ACTUALIZAR PERFIL (PUT /usuarios/<id_usuario>/perfil)
# =========================================================
@ws_usuario.route('/usuarios/<int:id_usuario>/perfil', methods=['PUT'])
def actualizar_perfil(id_usuario):
    from conexionBD import Conexion
    data = request.get_json() or {}

    nombre = (data.get('nombre') or '').strip()
    apellidos = (data.get('apellidos') or '').strip()
    correo = (data.get('correo') or '').strip()
    nueva1 = (data.get('nueva_password') or '').strip()
    nueva2 = (data.get('nueva_contrasena') or '').strip()
    nueva_contrasena = nueva1 if nueva1 else nueva2

    if not nombre or not apellidos or not correo:
        return jsonify({'status': False, 'message': 'Faltan parámetros'}), 200

    con = Conexion()
    cur = con.cursor()

    try:
        # Validar que el correo no esté usado por otro usuario
        cur.execute("""
            SELECT 1 FROM usuarios WHERE correo=%s AND id_usuario<>%s
        """, (correo, id_usuario))

        if cur.fetchone():
            return jsonify({'status': False, 'message': 'Correo ya está en uso'}), 409

        sets = ["nombre=%s", "apellidos=%s", "correo=%s"]
        params = [nombre, apellidos, correo]

        # Si hay nueva contraseña, la guardamos encriptada
        if nueva_contrasena:
            hash_nueva = generate_password_hash(nueva_contrasena)
            sets.append("contrasena=%s")
            params.append(hash_nueva)

        params.append(id_usuario)

        sql = f"UPDATE usuarios SET {', '.join(sets)} WHERE id_usuario=%s"
        cur.execute(sql, tuple(params))
        con.commit()

        cur.execute("""
            SELECT id_usuario, nombre, apellidos, correo, rol, estado_usuario
            FROM usuarios
            WHERE id_usuario=%s
        """, (id_usuario,))

        row = cur.fetchone()

        return jsonify({
            'status': True,
            'message': 'Perfil actualizado',
            'data': row
        }), 200

    except Exception as e:
        con.rollback()
        return jsonify({'status': False, 'message': str(e)}), 500

    finally:
        cur.close()
        con.close()
