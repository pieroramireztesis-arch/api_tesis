from conexionBD import Conexion
import json
import datetime

class Puntaje:
    @staticmethod
    def actualizar_puntaje(id_estudiante, id_ejercicio, id_opcion):
        con = Conexion()
        cursor = con.cursor()
        try:
            # 1. Verificar si la opción es correcta y obtener la competencia del ejercicio
            sql = """
                SELECT o.es_correcta, e.id_competencia
                FROM opciones_ejercicio o
                JOIN ejercicios e ON o.id_ejercicio = e.id_ejercicio
                WHERE o.id_opcion = %s;
            """
            cursor.execute(sql, (id_opcion,))
            resultado = cursor.fetchone()

            if not resultado:
                return json.dumps({'status': False, 'message': 'Opción o ejercicio no encontrado'})

            es_correcta = resultado['es_correcta']
            id_competencia = resultado['id_competencia']
            puntos = 1 if es_correcta else 0

            # 2. Revisar si ya existe un puntaje para ese estudiante y competencia
            sql = """
                SELECT id_puntaje, puntaje
                FROM puntajes
                WHERE id_estudiante = %s AND id_competencia = %s;
            """
            cursor.execute(sql, (id_estudiante, id_competencia))
            existente = cursor.fetchone()

            if existente:
                # 🔹 Puntaje acumulativo
                nuevo_puntaje = existente['puntaje'] + puntos
                sql = """
                    UPDATE puntajes
                    SET puntaje = %s, fecha_registro = %s
                    WHERE id_puntaje = %s;
                """
                cursor.execute(sql, (nuevo_puntaje, datetime.datetime.now(), existente['id_puntaje']))
            else:
                # 3. Crear nuevo puntaje
                sql = """
                    INSERT INTO puntajes (puntaje, fecha_registro, id_competencia, id_estudiante)
                    VALUES (%s, %s, %s, %s);
                """
                cursor.execute(sql, (puntos, datetime.datetime.now(), id_competencia, id_estudiante))

            con.commit()
            return json.dumps({'status': True, 'message': 'Puntaje actualizado correctamente'})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

    # 4. Listar todos los puntajes
    @staticmethod
    def listar():
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                SELECT p.id_puntaje, p.puntaje,
                       TO_CHAR(p.fecha_registro, 'YYYY-MM-DD HH24:MI:SS') AS fecha_registro,
                       c.descripcion AS competencia,
                       e.id_estudiante, u.nombre, u.apellidos
                FROM puntajes p
                JOIN competencias c ON p.id_competencia = c.id_competencia
                JOIN estudiante e ON p.id_estudiante = e.id_estudiante
                JOIN usuarios u ON e.id_usuario = u.id_usuario
                ORDER BY p.fecha_registro DESC;
            """
            cursor.execute(sql)
            datos = cursor.fetchall()
            return json.dumps({'status': True, 'data': datos})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

    # 5. Puntajes por estudiante
    @staticmethod
    def obtener_por_estudiante(id_estudiante):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                SELECT p.id_puntaje, p.puntaje,
                       TO_CHAR(p.fecha_registro, 'YYYY-MM-DD HH24:MI:SS') AS fecha_registro,
                       c.descripcion AS competencia
                FROM puntajes p
                JOIN competencias c ON p.id_competencia = c.id_competencia
                WHERE p.id_estudiante = %s
                ORDER BY p.fecha_registro DESC;
            """
            cursor.execute(sql, (id_estudiante,))
            datos = cursor.fetchall()
            return json.dumps({'status': True, 'data': datos})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()
