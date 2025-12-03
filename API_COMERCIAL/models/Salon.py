from conexionBD import Conexion
import json

class Salon:
    @staticmethod
    def registrar(nombre_salon, grado):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                INSERT INTO salones (nombre_salon, grado)
                VALUES (%s, %s)
            """
            cursor.execute(sql, (nombre_salon, grado))
            con.commit()
            return json.dumps({"status": True, "message": "Salón registrado correctamente"})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()

    @staticmethod
    def listar_todos():
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = "SELECT id_salon, nombre_salon, grado FROM salones ORDER BY id_salon"
            cursor.execute(sql)
            datos = cursor.fetchall()
            return json.dumps({"status": True, "data": datos})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()

    @staticmethod
    def actualizar(id_salon, data):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                UPDATE salones
                SET nombre_salon = %s,
                    grado = %s
                WHERE id_salon = %s
            """
            cursor.execute(sql, (data['nombre_salon'], data['grado'], id_salon))
            con.commit()
            return json.dumps({"status": True, "message": "Salón actualizado correctamente"})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()

    @staticmethod
    def eliminar(id_salon):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = "DELETE FROM salones WHERE id_salon = %s"
            cursor.execute(sql, (id_salon,))
            con.commit()
            return json.dumps({"status": True, "message": "Salón eliminado correctamente"})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()
