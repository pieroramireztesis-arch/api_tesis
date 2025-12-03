from conexionBD import Conexion
import json

class HistorialMaterial:
    @staticmethod
    def registrar(id_estudiante, id_material, estado, tiempo_visto, veces_revisado):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                INSERT INTO historial_material_estudio 
                (id_estudiante, id_material, estado, tiempo_visto, veces_revisado, fecha_revision)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(sql, (id_estudiante, id_material, estado, tiempo_visto, veces_revisado))
            con.commit()
            return json.dumps({"status": True, "message": "Historial registrado correctamente"})
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
            sql = """
                SELECT h.id_historial, h.estado, h.tiempo_visto, h.veces_revisado,
                       TO_CHAR(h.fecha_revision, 'YYYY-MM-DD HH24:MI:SS') AS fecha_revision,
                       u.nombre || ' ' || u.apellidos AS estudiante,
                       m.titulo AS material
                FROM historial_material_estudio h
                JOIN estudiante est ON h.id_estudiante = est.id_estudiante
                JOIN usuarios u ON est.id_usuario = u.id_usuario
                JOIN material_estudio m ON h.id_material = m.id_material
                ORDER BY h.fecha_revision DESC;
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
    def listar(id_estudiante):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                SELECT h.id_historial, h.estado, h.tiempo_visto, h.veces_revisado,
                       TO_CHAR(h.fecha_revision, 'YYYY-MM-DD HH24:MI:SS') AS fecha_revision,
                       m.titulo AS material
                FROM historial_material_estudio h
                JOIN material_estudio m ON h.id_material = m.id_material
                WHERE h.id_estudiante = %s
                ORDER BY h.fecha_revision DESC;
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
    def actualizar(id_historial, data):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                UPDATE historial_material_estudio
                SET estado = %s,
                    tiempo_visto = %s,
                    veces_revisado = %s,
                    fecha_revision = NOW()
                WHERE id_historial = %s
            """
            cursor.execute(sql, (
                data['estado'],
                data['tiempo_visto'],
                data['veces_revisado'],
                id_historial
            ))
            con.commit()
            return json.dumps({"status": True, "message": "Historial actualizado correctamente"})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()

    @staticmethod
    def eliminar(id_historial):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = "DELETE FROM historial_material_estudio WHERE id_historial = %s"
            cursor.execute(sql, (id_historial,))
            con.commit()
            return json.dumps({"status": True, "message": "Historial eliminado correctamente"})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()
