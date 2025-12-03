from conexionBD import Conexion
import json

class Usuario:
    def __init__(self, id_usuario=None, nombre=None, apellidos=None, correo=None, contrasena=None, rol=None, estado_usuario='activo'):
        self.id_usuario = id_usuario
        self.nombre = nombre
        self.apellidos = apellidos
        self.correo = correo
        self.contrasena = contrasena
        self.rol = rol
        self.estado_usuario = estado_usuario

    # Crear usuario
    def crear(self):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                INSERT INTO usuarios (nombre, apellidos, correo, contrasena, rol, estado_usuario)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_usuario;
            """
            cursor.execute(sql, (self.nombre, self.apellidos, self.correo, self.contrasena, self.rol, self.estado_usuario))
            nuevo_id = cursor.fetchone()['id_usuario']
            con.commit()
            return json.dumps({'status': True, 'id_usuario': nuevo_id, 'message': 'Usuario creado'})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

    # Listar todos los usuarios
    @staticmethod
    def listar():
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = "SELECT id_usuario, nombre, apellidos, correo, rol, estado_usuario FROM usuarios;"
            cursor.execute(sql)
            datos = cursor.fetchall()
            return json.dumps({'status': True, 'data': datos})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

    # Obtener usuario por id
    @staticmethod
    def obtener(id_usuario):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = "SELECT id_usuario, nombre, apellidos, correo, rol, estado_usuario FROM usuarios WHERE id_usuario = %s;"
            cursor.execute(sql, (id_usuario,))
            datos = cursor.fetchone()
            if datos:
                return json.dumps({'status': True, 'data': datos})
            else:
                return json.dumps({'status': False, 'message': 'Usuario no encontrado'})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

    # Actualizar usuario
    def actualizar(self):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                UPDATE usuarios
                SET nombre = %s, apellidos = %s, correo = %s, rol = %s, estado_usuario = %s
                WHERE id_usuario = %s;
            """
            cursor.execute(sql, (self.nombre, self.apellidos, self.correo, self.rol, self.estado_usuario, self.id_usuario))
            con.commit()
            return json.dumps({'status': True, 'message': 'Usuario actualizado'})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

    # Eliminar usuario
    @staticmethod
    def eliminar(id_usuario):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = "DELETE FROM usuarios WHERE id_usuario = %s;"
            cursor.execute(sql, (id_usuario,))
            con.commit()
            return json.dumps({'status': True, 'message': 'Usuario eliminado'})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()
