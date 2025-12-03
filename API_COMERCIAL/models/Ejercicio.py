from conexionBD import Conexion
import json
import os

class Ejercicio:

    # ============================
    # LISTAR TODOS
    # ============================
    @staticmethod
    def listar_todos():
        con = Conexion()
        cur = con.cursor()
        try:
            sql = """
                SELECT 
                    id_ejercicio,
                    descripcion,
                    imagen_url,
                    respuesta_correcta,
                    pista,
                    id_competencia
                FROM ejercicios
                ORDER BY id_ejercicio DESC
            """
            cur.execute(sql)
            filas = cur.fetchall()

            return json.dumps({
                "status": True,
                "data": filas
            }, default=str)

        except Exception as e:
            con.rollback()
            return json.dumps({
                "status": False,
                "message": str(e)
            })
        finally:
            cur.close()
            con.close()

    # ============================
    # OBTENER POR ID
    # ============================
    @staticmethod
    def obtener(id_ejercicio: int):
        con = Conexion()
        cur = con.cursor()
        try:
            sql = """
                SELECT 
                    id_ejercicio,
                    descripcion,
                    imagen_url,
                    respuesta_correcta,
                    pista,
                    id_competencia
                FROM ejercicios
                WHERE id_ejercicio = %s
            """
            cur.execute(sql, (id_ejercicio,))
            fila = cur.fetchone()

            if not fila:
                return json.dumps({
                    "status": False,
                    "message": "Ejercicio no encontrado"
                })

            return json.dumps({
                "status": True,
                "data": fila
            }, default=str)

        except Exception as e:
            con.rollback()
            return json.dumps({
                "status": False,
                "message": str(e)
            })
        finally:
            cur.close()
            con.close()

    # ============================
    # CREAR (desde API)
    # ============================
    @staticmethod
    def crear(data: dict):
        """
        Espera en data:
          - descripcion
          - respuesta_correcta (opcional)
          - pista (opcional)
          - id_competencia
          - imagen_ruta (opcional) -> se guarda en imagen_url
        """
        con = Conexion()
        cur = con.cursor()
        try:
            descripcion = data.get("descripcion", "").strip()
            respuesta_correcta = data.get("respuesta_correcta")
            pista = data.get("pista", "").strip()
            id_competencia = data.get("id_competencia")
            imagen_url = data.get("imagen_ruta")  # ruta relativa creada en ws/ejercicio.py

            if not descripcion or not id_competencia:
                return json.dumps({
                    "status": False,
                    "message": "Descripción e id_competencia son obligatorios"
                })

            sql = """
                INSERT INTO ejercicios
                    (descripcion, respuesta_correcta, pista, imagen_url, id_competencia)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id_ejercicio
            """
            cur.execute(sql, (
                descripcion,
                respuesta_correcta,
                pista,
                imagen_url,
                int(id_competencia),
            ))
            fila = cur.fetchone()
            con.commit()

            return json.dumps({
                "status": True,
                "message": "Ejercicio creado correctamente",
                "id_ejercicio": fila["id_ejercicio"]
            })

        except Exception as e:
            con.rollback()
            return json.dumps({
                "status": False,
                "message": str(e)
            })
        finally:
            cur.close()
            con.close()

    # ============================
    # ACTUALIZAR
    # ============================
    @staticmethod
    def actualizar(id_ejercicio: int, data: dict):
        con = Conexion()
        cur = con.cursor()
        try:
            campos = []
            valores = []

            if "descripcion" in data:
                campos.append("descripcion = %s")
                valores.append(data["descripcion"].strip())

            if "respuesta_correcta" in data:
                campos.append("respuesta_correcta = %s")
                valores.append(data["respuesta_correcta"])

            if "pista" in data:
                campos.append("pista = %s")
                valores.append(data["pista"].strip())

            if "id_competencia" in data:
                campos.append("id_competencia = %s")
                valores.append(int(data["id_competencia"]))

            if "imagen_ruta" in data and data["imagen_ruta"]:
                campos.append("imagen_url = %s")
                valores.append(data["imagen_ruta"])

            if not campos:
                return json.dumps({
                    "status": False,
                    "message": "No hay campos para actualizar"
                })

            sql = f"""
                UPDATE ejercicios
                SET {", ".join(campos)}
                WHERE id_ejercicio = %s
            """
            valores.append(id_ejercicio)

            cur.execute(sql, tuple(valores))
            con.commit()

            return json.dumps({
                "status": True,
                "message": "Ejercicio actualizado correctamente"
            })

        except Exception as e:
            con.rollback()
            return json.dumps({
                "status": False,
                "message": str(e)
            })
        finally:
            cur.close()
            con.close()

    # ============================
    # ELIMINAR
    # ============================
    @staticmethod
    def eliminar(id_ejercicio: int):
        con = Conexion()
        cur = con.cursor()
        try:
            # Primero leemos la imagen_url (si quieres borrar el archivo)
            cur.execute(
                "SELECT imagen_url FROM ejercicios WHERE id_ejercicio = %s",
                (id_ejercicio,)
            )
            fila = cur.fetchone()
            imagen_url = fila["imagen_url"] if fila else None

            # Borramos el ejercicio
            cur.execute(
                "DELETE FROM ejercicios WHERE id_ejercicio = %s",
                (id_ejercicio,)
            )
            con.commit()

            # Si quieres, aquí podrías borrar el archivo físico usando os.remove
            # según cómo guardes la ruta (opcional)

            return json.dumps({
                "status": True,
                "message": "Ejercicio eliminado correctamente"
            })

        except Exception as e:
            con.rollback()
            return json.dumps({
                "status": False,
                "message": str(e)
            })
        finally:
            cur.close()
            con.close()
