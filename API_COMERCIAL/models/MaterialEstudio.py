# models/MaterialEstudio.py
from conexionBD import Conexion
import json

class MaterialEstudio:
    @staticmethod
    def registrar(titulo, tipo, url, tiempo_estimado, id_competencia, nivel=None):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                INSERT INTO material_estudio (titulo, tipo, url, tiempo_estimado, id_competencia, nivel)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (titulo, tipo, url, tiempo_estimado, id_competencia, nivel))
            con.commit()
            return json.dumps({"status": True, "message": "Material registrado correctamente"})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()

    @staticmethod
    def actualizar(id_material, data):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                UPDATE material_estudio
                SET titulo = %s,
                    tipo = %s,
                    url = %s,
                    tiempo_estimado = %s,
                    id_competencia = %s,
                    nivel = %s
                WHERE id_material = %s
            """
            cursor.execute(
                sql,
                (
                    data["titulo"],
                    data["tipo"],
                    data["url"],
                    data["tiempo_estimado"],
                    data["id_competencia"],
                    data.get("nivel"),   # puede venir null
                    id_material,
                ),
            )
            con.commit()
            return json.dumps({"status": True, "message": "Material actualizado correctamente"})
        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()
