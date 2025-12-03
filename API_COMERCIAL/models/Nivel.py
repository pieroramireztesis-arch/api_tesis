from conexionBD import Conexion
import json

class Nivel:
    @staticmethod
    def registrar(nombre_nivel, descripcion):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                INSERT INTO niveles (nombre_nivel, descripcion)
                VALUES (%s, %s)
            """
            cursor.execute(sql, (nombre_nivel, descripcion))
            con.commit()
            return json.dumps({"status": True, "message": "Nivel registrado correctamente"})
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
            sql = "SELECT id_nivel, nombre_nivel, descripcion FROM niveles ORDER BY id_nivel"
            cursor.execute(sql)
            datos = cursor.fetchall()
            return json.dumps({"status": True, "data": datos})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()

    @staticmethod
    def actualizar(id_nivel, data):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                UPDATE niveles
                SET nombre_nivel = %s,
                    descripcion = %s
                WHERE id_nivel = %s
            """
            cursor.execute(sql, (data['nombre_nivel'], data['descripcion'], id_nivel))
            con.commit()
            return json.dumps({"status": True, "message": "Nivel actualizado correctamente"})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()

    @staticmethod
    def eliminar(id_nivel):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = "DELETE FROM niveles WHERE id_nivel = %s"
            cursor.execute(sql, (id_nivel,))
            con.commit()
            return json.dumps({"status": True, "message": "Nivel eliminado correctamente"})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()
