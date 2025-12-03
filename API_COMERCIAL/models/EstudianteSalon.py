from conexionBD import Conexion
import json

class EstudianteSalon:
    @staticmethod
    def asignar(id_estudiante, id_salon):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = "INSERT INTO estudiante_salones (id_estudiante, id_salon) VALUES (%s, %s)"
            cursor.execute(sql, (id_estudiante, id_salon))
            con.commit()
            return json.dumps({"status": True, "message": "Estudiante asignado al salón correctamente"})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()

    @staticmethod
    def listar():
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                SELECT es.id_estudiante, u.nombre || ' ' || u.apellidos AS estudiante,
                       s.id_salon, s.nombre_salon, s.grado
                FROM estudiante_salones es
                JOIN estudiante e ON es.id_estudiante = e.id_estudiante
                JOIN usuarios u ON e.id_usuario = u.id_usuario
                JOIN salones s ON es.id_salon = s.id_salon
            """
            cursor.execute(sql)
            datos = cursor.fetchall()
            return json.dumps({"status": True, "data": datos})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()

    @staticmethod
    def eliminar(id_estudiante, id_salon):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = "DELETE FROM estudiante_salones WHERE id_estudiante = %s AND id_salon = %s"
            cursor.execute(sql, (id_estudiante, id_salon))
            con.commit()
            return json.dumps({"status": True, "message": "Asignación eliminada correctamente"})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()
