# API_COMERCIAL/ws/ejercicio.py
from flask import Blueprint, jsonify, request
from conexionBD import Conexion
import json

ws_ejercicio = Blueprint("ws_ejercicio", __name__, url_prefix="/ejercicios")


# ============================
#  GET /ejercicios
#  Lista TODOS los ejercicios
# ============================
@ws_ejercicio.route("", methods=["GET"])
def listar_ejercicios():
    """
    Devuelve TODOS los ejercicios, de TODAS las competencias.
    Pensado para pruebas de API o listados generales.
    """
    con = Conexion()
    cursor = con.cursor()

    try:
        cursor.execute(
            """
            SELECT 
                e.id_ejercicio,
                e.descripcion,
                e.imagen_url,
                e.respuesta_correcta,
                e.pista,
                c.id_competencia,
                c.descripcion AS competencia,
                c.area,
                c.nivel
            FROM ejercicios e
            JOIN competencias c
              ON e.id_competencia = c.id_competencia
            ORDER BY e.id_ejercicio DESC
            """
        )
        rows = cursor.fetchall()

        data = [
            {
                "idEjercicio": r["id_ejercicio"],
                "enunciado": r["descripcion"],
                "imagenUrl": r["imagen_url"],
                "respuestaCorrecta": r["respuesta_correcta"],
                "pista": r["pista"],
                "idCompetencia": r["id_competencia"],
                "competencia": r["competencia"],
                "area": r["area"],
                "nivelCompetencia": r["nivel"],
            }
            for r in rows
        ]

        return jsonify({"status": True, "data": data}), 200

    except Exception as e:
        print("Error en GET /ejercicios:", e)
        return jsonify({"status": False, "message": str(e)}), 500

    finally:
        cursor.close()
        con.close()


# ============================
#  GET /ejercicios/<id>
#  Detalle de un ejercicio
# ============================
@ws_ejercicio.route("/<int:id_ejercicio>", methods=["GET"])
def obtener_ejercicio(id_ejercicio: int):
    """
    Devuelve el detalle de un ejercicio específico, incluidas sus opciones.
    """
    con = Conexion()
    cursor = con.cursor()

    try:
        cursor.execute(
            """
            SELECT 
                e.id_ejercicio,
                e.descripcion,
                e.imagen_url,
                e.respuesta_correcta,
                e.pista,
                c.id_competencia,
                c.descripcion AS competencia,
                c.area,
                c.nivel
            FROM ejercicios e
            JOIN competencias c
              ON e.id_competencia = c.id_competencia
            WHERE e.id_ejercicio = %s
            """,
            (id_ejercicio,),
        )
        ej = cursor.fetchone()

        if not ej:
            return jsonify({"status": False, "message": "Ejercicio no encontrado"}), 404

        cursor.execute(
            """
            SELECT id_opcion, letra, descripcion, es_correcta
            FROM opciones_ejercicio
            WHERE id_ejercicio = %s
            ORDER BY letra
            """,
            (id_ejercicio,),
        )
        opciones_rows = cursor.fetchall()

        opciones = [
            {
                "idOpcion": o["id_opcion"],
                "letra": o["letra"],
                "texto": o["descripcion"],
                "esCorrecta": o["es_correcta"],
            }
            for o in opciones_rows
        ]

        data = {
            "idEjercicio": ej["id_ejercicio"],
            "enunciado": ej["descripcion"],
            "imagenUrl": ej["imagen_url"],
            "respuestaCorrecta": ej["respuesta_correcta"],
            "pista": ej["pista"],
            "idCompetencia": ej["id_competencia"],
            "competencia": ej["competencia"],
            "area": ej["area"],
            "nivelCompetencia": ej["nivel"],
            "opciones": opciones,
        }

        return jsonify({"status": True, "data": data}), 200

    except Exception as e:
        print("Error en GET /ejercicios/<id>:", e)
        return jsonify({"status": False, "message": str(e)}), 500

    finally:
        cursor.close()
        con.close()
