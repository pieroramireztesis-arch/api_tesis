from conexionBD import Conexion
import json

class Progreso:
    @staticmethod
    def registrar(id_estudiante, id_ejercicio, nivel_actual, estado, tiempo_respuesta):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                INSERT INTO progreso (id_estudiante, id_ejercicio, nivel_actual, estado, tiempo_respuesta, fecha)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(sql, (id_estudiante, id_ejercicio, nivel_actual, estado, tiempo_respuesta))
            con.commit()
            return json.dumps({"status": True, "message": "Progreso registrado correctamente"})
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
                SELECT p.id_progreso, p.nivel_actual, p.estado, p.tiempo_respuesta,
                       TO_CHAR(p.fecha, 'YYYY-MM-DD HH24:MI:SS') AS fecha,
                       e.descripcion AS ejercicio
                FROM progreso p
                JOIN ejercicios e ON p.id_ejercicio = e.id_ejercicio
                WHERE p.id_estudiante = %s
                ORDER BY p.fecha DESC
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
    def eliminar(id_progreso):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = "DELETE FROM progreso WHERE id_progreso = %s"
            cursor.execute(sql, (id_progreso,))
            con.commit()
            return json.dumps({"status": True, "message": "Registro de progreso eliminado"})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()
