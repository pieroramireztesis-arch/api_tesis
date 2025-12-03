from conexionBD import Conexion
import json

class Competencia:
    def __init__(self, id_competencia=None, descripcion=None, nivel=None):
        self.id_competencia = id_competencia
        self.descripcion = descripcion
        self.nivel = nivel

    # Crear competencia
    def crear(self):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                INSERT INTO competencias (descripcion, nivel)
                VALUES (%s, %s) RETURNING id_competencia;
            """
            cursor.execute(sql, (self.descripcion, self.nivel))
            nuevo_id = cursor.fetchone()['id_competencia']
            con.commit()
            return json.dumps({'status': True, 'id_competencia': nuevo_id, 'message': 'Competencia creada'})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

    # Listar competencias
    @staticmethod
    def listar():
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = "SELECT * FROM competencias;"
            cursor.execute(sql)
            datos = cursor.fetchall()
            return json.dumps({'status': True, 'data': datos})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

    # Obtener competencia por id
    @staticmethod
    def obtener(id_competencia):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = "SELECT * FROM competencias WHERE id_competencia = %s;"
            cursor.execute(sql, (id_competencia,))
            datos = cursor.fetchone()
            if datos:
                return json.dumps({'status': True, 'data': datos})
            else:
                return json.dumps({'status': False, 'message': 'Competencia no encontrada'})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

    # Actualizar competencia
    def actualizar(self):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                UPDATE competencias
                SET descripcion = %s, nivel = %s
                WHERE id_competencia = %s;
            """
            cursor.execute(sql, (self.descripcion, self.nivel, self.id_competencia))
            con.commit()
            return json.dumps({'status': True, 'message': 'Competencia actualizada'})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

    # Eliminar competencia
    @staticmethod
    def eliminar(id_competencia):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = "DELETE FROM competencias WHERE id_competencia = %s;"
            cursor.execute(sql, (id_competencia,))
            con.commit()
            return json.dumps({'status': True, 'message': 'Competencia eliminada'})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()
