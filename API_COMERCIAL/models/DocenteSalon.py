from conexionBD import Conexion
import json

class DocenteSalon:
    @staticmethod
    def asignar(id_docente, id_salon):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = "INSERT INTO docente_salones (id_docente, id_salon) VALUES (%s, %s)"
            cursor.execute(sql, (id_docente, id_salon))
            con.commit()
            return json.dumps({"status": True, "message": "Docente asignado al salón correctamente"})
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
                SELECT ds.id_docente, u.nombre || ' ' || u.apellidos AS docente,
                       s.id_salon, s.nombre_salon, s.grado
                FROM docente_salones ds
                JOIN docente d ON ds.id_docente = d.id_docente
                JOIN usuarios u ON d.id_usuario = u.id_usuario
                JOIN salones s ON ds.id_salon = s.id_salon
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
    def eliminar(id_docente, id_salon):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = "DELETE FROM docente_salones WHERE id_docente = %s AND id_salon = %s"
            cursor.execute(sql, (id_docente, id_salon))
            con.commit()
            return json.dumps({"status": True, "message": "Asignación eliminada correctamente"})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()
