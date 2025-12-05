from flask import Blueprint, request, jsonify
from models.HistorialMaterial import HistorialMaterial
import json

ws_historial_material = Blueprint(
    "ws_historial_material",
    __name__,
    url_prefix="/historial-material"
)


# ================================
# REGISTRAR VISUALIZACIÓN
# ================================
@ws_historial_material.route("", methods=["POST"])
def registrar_historial():
    data = request.get_json()

    id_estudiante = data.get("id_estudiante")
    id_material = data.get("id_material")
    tiempo_visualizacion = data.get("tiempo_visualizacion")

    return jsonify(json.loads(
        HistorialMaterial.registrar(id_estudiante, id_material, tiempo_visualizacion)
    ))


# ================================
# LISTAR HISTORIAL DEL ESTUDIANTE
# ================================
@ws_historial_material.route("/<int:id_estudiante>", methods=["GET"])
def listar_historial(id_estudiante):
    return jsonify(json.loads(
        HistorialMaterial.listar_por_estudiante(id_estudiante)
    ))
