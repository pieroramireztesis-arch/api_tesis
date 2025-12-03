from conexionBD import Conexion
import json

class Estudiante:
    def __init__(self, id_estudiante=None, grado=None, id_usuario=None):
        self.id_estudiante = id_estudiante
        self.grado = grado
        self.id_usuario = id_usuario

    # Crear estudiante
    def crear(self):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                INSERT INTO estudiante (grado, id_usuario)
                VALUES (%s, %s) RETURNING id_estudiante;
            """
            cursor.execute(sql, (self.grado, self.id_usuario))
            nuevo_id = cursor.fetchone()['id_estudiante']
            con.commit()
            return json.dumps({'status': True, 'id_estudiante': nuevo_id, 'message': 'Estudiante creado'})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

    # Listar todos los estudiantes
    @staticmethod
    def listar():
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                SELECT e.id_estudiante, u.nombre, u.apellidos, e.grado, e.estado_estudiante
                FROM estudiante e
                JOIN usuarios u ON e.id_usuario = u.id_usuario
                WHERE u.rol = 'estudiante';
            """
            cursor.execute(sql)
            datos = cursor.fetchall()
            return json.dumps({'status': True, 'data': datos})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

    # Obtener estudiante por id
    @staticmethod
    def obtener(id_estudiante):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                SELECT e.id_estudiante, u.nombre, u.apellidos, e.grado, e.estado_estudiante
                FROM estudiante e
                JOIN usuarios u ON e.id_usuario = u.id_usuario
                WHERE e.id_estudiante = %s;
            """
            cursor.execute(sql, (id_estudiante,))
            datos = cursor.fetchone()
            if datos:
                return json.dumps({'status': True, 'data': datos})
            else:
                return json.dumps({'status': False, 'message': 'Estudiante no encontrado'})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

    # Actualizar estudiante
    def actualizar(self):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                UPDATE estudiante
                SET grado = %s
                WHERE id_estudiante = %s;
            """
            cursor.execute(sql, (self.grado, self.id_estudiante))
            con.commit()
            return json.dumps({'status': True, 'message': 'Estudiante actualizado'})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

    # Eliminar estudiante
    @staticmethod
    def eliminar(id_estudiante):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = "DELETE FROM estudiante WHERE id_estudiante = %s;"
            cursor.execute(sql, (id_estudiante,))
            con.commit()
            return json.dumps({'status': True, 'message': 'Estudiante eliminado'})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()
