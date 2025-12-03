from conexionBD import Conexion
import json

class Recomendacion:
    @staticmethod
    def registrar(id_estudiante, id_ejercicio, id_respuesta, tipo_recomendacion, mensaje):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                INSERT INTO recomendaciones (id_estudiante, id_ejercicio, id_respuesta, tipo_recomendacion, mensaje, fecha)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(sql, (id_estudiante, id_ejercicio, id_respuesta, tipo_recomendacion, mensaje))
            con.commit()
            return json.dumps({"status": True, "message": "Recomendación registrada correctamente"})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()

    @staticmethod
    def listar(id_estudiante):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                SELECT r.id_recomendacion, r.tipo_recomendacion, r.mensaje,
                       TO_CHAR(r.fecha, 'YYYY-MM-DD HH24:MI:SS') AS fecha,
                       e.descripcion AS ejercicio
                FROM recomendaciones r
                JOIN ejercicios e ON r.id_ejercicio = e.id_ejercicio
                WHERE r.id_estudiante = %s
                ORDER BY r.fecha DESC
            """
            cursor.execute(sql, (id_estudiante,))
            datos = cursor.fetchall()
            return json.dumps({"status": True, "data": datos})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()

    @staticmethod
    def eliminar(id_recomendacion):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = "DELETE FROM recomendaciones WHERE id_recomendacion = %s"
            cursor.execute(sql, (id_recomendacion,))
            con.commit()
            return json.dumps({"status": True, "message": "Recomendación eliminada"})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()
