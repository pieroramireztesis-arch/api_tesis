# ws_tutor.py
import os
import pickle
import numpy as np
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from conexionBD import Conexion

ws_tutor = Blueprint("ws_tutor", __name__, url_prefix="/tutor")

# Carpeta base: API_COMERCIAL
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
# URL base del proyecto WEB (donde están las imágenes en /static)
WEB_BASE_URL = "http://192.168.1.13:5000"

# Carpeta donde se guardarán los desarrollos de los alumnos
DESARROLLOS_FOLDER = os.path.join(BASE_DIR, "static", "desarrollos_alumno")
os.makedirs(DESARROLLOS_FOLDER, exist_ok=True)

# ================================
#  Parámetros usados por el modelo
# ================================
UMBRAL_APROBADO = 60.0  # igual que en train_model.py

# ================================
#  Carga del modelo de Tutor (ML)
# ================================
MODEL_PATH = os.path.join(BASE_DIR, "modelo_tutor.pkl")
MODELO_TUTOR = None
ENCODER_NIVEL = None

try:
    with open(MODEL_PATH, "rb") as f:
        data = pickle.load(f)

        # Soporta tanto (modelo, encoder) como {"modelo":..., "encoder":...}
        if isinstance(data, dict):
            MODELO_TUTOR = data.get("modelo")
            ENCODER_NIVEL = data.get("encoder")
        else:
            MODELO_TUTOR, ENCODER_NIVEL = data

    print("✅ Modelo de tutor cargado desde:", MODEL_PATH)
    try:
        print("👉 n_features_in_ del modelo cargado:", MODELO_TUTOR.n_features_in_)
    except Exception:
        pass
except Exception as e:
    print("⚠️ No se pudo cargar modelo_tutor.pkl:", e)
    MODELO_TUTOR = None
    ENCODER_NIVEL = None


# =========================================
#  FUNCIONES AUXILIARES PARA EL MODELO ML
# =========================================
def calcular_features_competencia(cursor, id_estudiante, id_competencia):
    """
    Calcula las MISMAS features que se usaron para entrenar el modelo:
      - total_intentos
      - promedio_puntaje
      - min_puntaje
      - max_puntaje
      - tasa_aprobados
    """
    cursor.execute(
        """
        SELECT
            COUNT(*)                        AS total_intentos,
            AVG(puntaje)                    AS promedio_puntaje,
            MIN(puntaje)                    AS min_puntaje,
            MAX(puntaje)                    AS max_puntaje,
            SUM(
                CASE
                    WHEN puntaje >= %s THEN 1
                    ELSE 0
                END
            ) AS num_aprobados
        FROM puntajes
        WHERE id_estudiante = %s
          AND id_competencia = %s
        """,
        (UMBRAL_APROBADO, id_estudiante, id_competencia),
    )
    row = cursor.fetchone()

    if not row:
        return None

    total_intentos = row.get("total_intentos") or 0
    promedio = row.get("promedio_puntaje")
    min_p = row.get("min_puntaje")
    max_p = row.get("max_puntaje")
    num_aprobados = row.get("num_aprobados") or 0

    if (
        total_intentos == 0
        or promedio is None
        or min_p is None
        or max_p is None
    ):
        return None

    total_intentos = float(total_intentos)
    promedio = float(promedio)
    min_p = float(min_p)
    max_p = float(max_p)

    # Normalizar al rango 0..100
    promedio = max(0.0, min(100.0, promedio))
    min_p = max(0.0, min(100.0, min_p))
    max_p = max(0.0, min(100.0, max_p))

    tasa_aprobados = float(num_aprobados) / total_intentos

    X = np.array([[total_intentos, promedio, min_p, max_p, tasa_aprobados]], dtype=float)
    return X


def _clasificar_nivel_desde_valor(valor_num):
    """
    Convierte un valor 0-100 en 'bajo' / 'medio' / 'alto'.
    Usado para el nivel inicial manual cargado por el docente.
    """
    if valor_num is None:
        return None
    try:
        v = float(valor_num)
    except Exception:
        return None

    if v < 40:
        return "bajo"
    elif v < 70:
        return "medio"
    else:
        return "alto"


def predecir_nivel_competencia(cursor, id_estudiante, id_competencia):
    """
    Usa el MODELO_TUTOR para predecir el nivel de dominio de un estudiante
    en una competencia específica.

    Si el modelo aún no tiene datos suficientes (no hay puntajes), usa
    el nivel inicial manual almacenado en la tabla ESTUDIANTE
    (operaciones_basicas, ecuaciones, funciones, geometria) según el área
    de la competencia.
    """
    nivel_texto = None

    # 1) Intentar con el modelo ML si está disponible y hay historial
    if MODELO_TUTOR is not None:
        X = calcular_features_competencia(cursor, id_estudiante, id_competencia)
        if X is not None:
            try:
                y_pred_encoded = MODELO_TUTOR.predict(X)[0]
                if ENCODER_NIVEL is not None:
                    nivel_texto = ENCODER_NIVEL.inverse_transform([y_pred_encoded])[0]
                else:
                    nivel_texto = str(y_pred_encoded)
            except Exception as e:
                print("Error en predicción ML, se usará nivel inicial manual:", e)

    # 2) Fallback: usar nivel inicial manual registrado por el docente
    if nivel_texto is None:
        cursor.execute(
            """
            SELECT
                c.area,
                e.operaciones_basicas,
                e.ecuaciones,
                e.funciones,
                e.geometria
            FROM competencias c,
                 estudiante e
            WHERE c.id_competencia = %s
              AND e.id_estudiante = %s
            """,
            (id_competencia, id_estudiante),
        )
        row = cursor.fetchone()

        if row:
            area = row.get("area")
            valor_area = None

            if area == "operaciones_basicas":
                valor_area = row.get("operaciones_basicas")
            elif area == "ecuaciones":
                valor_area = row.get("ecuaciones")
            elif area == "funciones":
                valor_area = row.get("funciones")
            elif area == "geometria":
                valor_area = row.get("geometria")

            nivel_texto = _clasificar_nivel_desde_valor(valor_area)

    return nivel_texto  # "bajo", "medio" o "alto" o None


def actualizar_nivel_estudiante_competencia(
    cursor, id_estudiante, id_competencia, nivel_texto
):
    """
    Actualiza la tabla nivel_estudiante_competencia con la predicción
    del modelo, y calcula también un nivel global para el estudiante.
    """
    if nivel_texto is None:
        return None, None

    # Mapeamos el texto a un nivel numérico (1 a 7, por ejemplo)
    if nivel_texto == "bajo":
        nivel_int = 2
    elif nivel_texto == "medio":
        nivel_int = 4
    else:  # "alto"
        nivel_int = 6

    # Recalculamos métricas de la competencia
    cursor.execute(
        """
        SELECT
            COUNT(*)      AS total_intentos,
            AVG(puntaje)  AS promedio_puntaje
        FROM puntajes
        WHERE id_estudiante = %s
          AND id_competencia = %s
        """,
        (id_estudiante, id_competencia),
    )
    row = cursor.fetchone() or {}
    total_intentos = row.get("total_intentos") or 0
    promedio_puntaje = row.get("promedio_puntaje") or 0.0

    # Insert/Update en nivel_estudiante_competencia
    cursor.execute(
        """
        INSERT INTO nivel_estudiante_competencia
            (id_estudiante, id_competencia, nivel_actual,
             promedio_puntaje, ejercicios_considerados, fecha_ultimo_update)
        VALUES (%s, %s, %s, %s, %s, NOW())
        ON CONFLICT (id_estudiante, id_competencia)
        DO UPDATE SET
            nivel_actual            = EXCLUDED.nivel_actual,
            promedio_puntaje        = EXCLUDED.promedio_puntaje,
            ejercicios_considerados = EXCLUDED.ejercicios_considerados,
            fecha_ultimo_update     = EXCLUDED.fecha_ultimo_update
        """,
        (
            id_estudiante,
            id_competencia,
            nivel_int,
            float(promedio_puntaje),
            int(total_intentos),
        ),
    )

    # Calculamos un nivel global promedio para el estudiante
    cursor.execute(
        """
        SELECT AVG(nivel_actual) AS promedio_nivel
        FROM nivel_estudiante_competencia
        WHERE id_estudiante = %s
        """,
        (id_estudiante,),
    )
    row = cursor.fetchone() or {}
    prom_nivel = row.get("promedio_nivel")

    if prom_nivel is None:
        nivel_global = None
    else:
        prom_nivel = float(prom_nivel)
        if prom_nivel < 3:
            nivel_global = "bajo"
        elif prom_nivel < 5:
            nivel_global = "medio"
        else:
            nivel_global = "alto"

    return nivel_int, nivel_global


# ================================
#  GET /tutor/ejercicio_siguiente
# ================================
@ws_tutor.route("/ejercicio_siguiente", methods=["GET"])
def ejercicio_siguiente():
    id_estudiante = request.args.get("idEstudiante", type=int)
    id_dominio = request.args.get("idDominio", type=int)
    ajuste = request.args.get("ajuste", type=str)

    if not id_estudiante:
        return (
            jsonify({"error": "idEstudiante es obligatorio", "status": False}),
            400,
        )

    con = Conexion()
    cursor = con.cursor()

    try:
        where = []
        params = []

        # filtro por dominio (competencia)
        if id_dominio:
            where.append("e.id_competencia = %s")
            params.append(id_dominio)

        # filtro por nivel según ajuste
        if ajuste == "mas_dificil":
            where.append("c.nivel >= 2")
        elif ajuste == "mas_facil":
            where.append("c.nivel = 1")

        # no repetir ejercicios ya respondidos
        where.append(
            """
            NOT EXISTS(
                SELECT 1
                FROM respuestas_estudiantes r
                WHERE r.id_ejercicio = e.id_ejercicio
                  AND r.id_estudiante = %s
            )
        """
        )
        params.append(id_estudiante)

        # solo ejercicios con opciones
        where.append(
            """
            EXISTS(
                SELECT 1
                FROM opciones_ejercicio oe
                WHERE oe.id_ejercicio = e.id_ejercicio
            )
        """
        )

        where_clause = " AND ".join(where)
        if where_clause:
            where_clause = "WHERE " + where_clause

        sql_ejercicio = f"""
            SELECT 
                e.id_ejercicio,
                e.descripcion      AS enunciado,
                e.imagen_url       AS imagen_url,
                c.id_competencia,
                c.descripcion      AS competencia,
                c.nivel
            FROM ejercicios e
            JOIN competencias c 
              ON e.id_competencia = c.id_competencia
            {where_clause}
            ORDER BY RANDOM()
            LIMIT 1
        """
        cursor.execute(sql_ejercicio, tuple(params))
        ejercicio = cursor.fetchone()

        if not ejercicio:
            return (
                jsonify(
                    {
                        "status": False,
                        "sinEjercicios": True,
                        "mensaje": "No hay más ejercicios disponibles para este estudiante con los filtros dados.",
                    }
                ),
                200,
            )

        id_ejercicio = ejercicio["id_ejercicio"]
        id_competencia = ejercicio["id_competencia"]
        imagen_rel = ejercicio["imagen_url"]

        # ================================
        # Normalizar URL de la imagen
        # Puede venir como:
        #   - 'ejercicios_ayuda/ej_6.jpg'
        #   - 'static/ejercicios_ayuda/ej_6.jpg'
        #   - '/static/ejercicios_ayuda/ej_6.jpg'
        #   - o ya una URL absoluta 'http://...'
        # ================================
        if imagen_rel:
            # Si ya es URL absoluta, la usamos tal cual
            if imagen_rel.startswith("http://") or imagen_rel.startswith("https://"):
                imagen_url_abs = imagen_rel
            else:
                # Asegurar que empiece por /static/...
                # Quitamos espacios
                imagen_rel = imagen_rel.strip()

                # Si comienza por 'static/', le agregamos la barra inicial
                if imagen_rel.startswith("static/"):
                    imagen_rel = "/" + imagen_rel

                # Si NO empieza por '/static/', asumimos que es solo la carpeta/archivo
                if not imagen_rel.startswith("/static/"):
                    # ejemplo: 'ejercicios_ayuda/ej_6.jpg' -> '/static/ejercicios_ayuda/ej_6.jpg'
                    if imagen_rel.startswith("/"):
                        imagen_rel = "/static" + imagen_rel
                    else:
                        imagen_rel = "/static/" + imagen_rel

                # 🚨 Importante: las imágenes de ejercicios viven en el proyecto WEB (puerto 5000)
                base = WEB_BASE_URL.rstrip("/")
                imagen_url_abs = base + imagen_rel

        else:
            imagen_url_abs = None


        # opciones
        cursor.execute(
            """
            SELECT id_opcion, letra, descripcion
            FROM opciones_ejercicio
            WHERE id_ejercicio = %s
            ORDER BY letra
        """,
            (id_ejercicio,),
        )
        opciones_rows = cursor.fetchall()

        if not opciones_rows:
            return (
                jsonify(
                    {
                        "status": False,
                        "sinEjercicios": True,
                        "mensaje": "El ejercicio seleccionado no tiene opciones registradas.",
                    }
                ),
                200,
            )

        opciones = [
            {
                "idOpcion": o["id_opcion"],
                "letra": o["letra"],
                "texto": o["descripcion"],
            }
            for o in opciones_rows
        ]

        # pista opcional
        cursor.execute(
            """
            SELECT mensaje
            FROM recomendaciones
            WHERE id_ejercicio = %s
            ORDER BY fecha DESC
            LIMIT 1
        """,
            (id_ejercicio,),
        )
        rec = cursor.fetchone()
        pista = rec["mensaje"] if rec else None

        data = {
            "status": True,
            "sinEjercicios": False,
            "idEjercicio": id_ejercicio,
            "idCompetencia": id_competencia,
            "enunciado": ejercicio["enunciado"],
            "imagenUrl": imagen_url_abs,
            "opciones": opciones,
            "pista": pista,
            "mensaje": None,
            "requiereDesarrollo": True,
        }

        return jsonify(data), 200

    except Exception as e:
        print("Error en /tutor/ejercicio_siguiente:", str(e))
        return jsonify({"error": str(e), "status": False}), 500
    finally:
        cursor.close()
        con.close()


# =========================================
#  FUNCION AUX: Actualizar progreso_estudiante
# =========================================
def actualizar_progreso_estudiante(con, cursor, id_estudiante):
    """
    Calcula el promedio de puntajes por competencia MINEDU y actualiza
    la tabla ESTUDIANTE.

    Mapa de áreas -> columnas de la tabla estudiante:
      - 'cantidad'                        -> operaciones_basicas
      - 'regularidad_equivalencia_cambio' -> ecuaciones
      - 'forma_movimiento_localizacion'   -> funciones
      - 'gestion_datos_incertidumbre'     -> geometria
    """

    cursor.execute(
        """
        SELECT c.area,
               AVG(p.puntaje) AS promedio
        FROM puntajes p
        JOIN competencias c ON c.id_competencia = p.id_competencia
        WHERE p.id_estudiante = %s
          AND c.area IS NOT NULL
        GROUP BY c.area
        """,
        (id_estudiante,),
    )
    rows = cursor.fetchall()

    cant = reg = forma = datos = None

    for row in rows:
        area = row["area"]
        promedio = row["promedio"]
        promedio_int = int(round(promedio)) if promedio is not None else None

        if area == "cantidad":
            cant = promedio_int
        elif area == "regularidad_equivalencia_cambio":
            reg = promedio_int
        elif area == "forma_movimiento_localizacion":
            forma = promedio_int
        elif area == "gestion_datos_incertidumbre":
            datos = promedio_int

    valores = [v for v in [cant, reg, forma, datos] if v is not None]
    progreso_general = int(round(sum(valores) / len(valores))) if valores else None

    cursor.execute(
        """
        UPDATE estudiante
        SET operaciones_basicas = COALESCE(%s, operaciones_basicas),
            ecuaciones          = COALESCE(%s, ecuaciones),
            funciones           = COALESCE(%s, funciones),
            geometria           = COALESCE(%s, geometria),
            progreso_general    = COALESCE(%s, progreso_general)
        WHERE id_estudiante = %s
        """,
        (cant, reg, forma, datos, progreso_general, id_estudiante),
    )


# ================================
#  POST /tutor/responder
# ================================
@ws_tutor.route("/responder", methods=["POST"])
def responder():
    data = request.get_json() or {}

    id_estudiante = data.get("idEstudiante")
    id_ejercicio = data.get("idEjercicio")
    id_opcion_sel = data.get("idOpcionSeleccionada")
    tiempo_respuesta = data.get("tiempoRespuesta")
    uso_pista = bool(data.get("usoPista", False))
    ajuste_anterior = data.get("ajuste")

    if not id_estudiante or not id_ejercicio or not id_opcion_sel:
        return jsonify({"error": "Faltan campos obligatorios"}), 400

    con = Conexion()
    cursor = con.cursor()

    try:
        # 1) Verificar opción elegida
        cursor.execute(
            """
            SELECT 
                o.es_correcta, 
                e.id_competencia,
                c.nivel AS nivel_competencia
            FROM opciones_ejercicio o
            JOIN ejercicios e ON e.id_ejercicio = o.id_ejercicio
            JOIN competencias c ON e.id_competencia = c.id_competencia
            WHERE o.id_opcion = %s
        """,
            (id_opcion_sel,),
        )
        row = cursor.fetchone()

        if not row:
            return jsonify({"error": "Opción no encontrada"}), 404

        es_correcta = bool(row["es_correcta"])
        id_competencia = row["id_competencia"]
        nivel_competencia = row["nivel_competencia"]

        # 2) Registrar respuesta
        cursor.execute(
            """
            INSERT INTO respuestas_estudiantes
                (respuesta_texto, respuesta_imagen, fecha,
                 tiempo_respuesta, uso_pista,
                 id_estudiante, id_ejercicio, id_opcion, desarrollo_url)
            VALUES (%s, %s, CURRENT_TIMESTAMP,
                    %s, %s,
                    %s, %s, %s, %s)
            RETURNING id_respuesta
        """,
            (
                None,
                None,
                float(tiempo_respuesta) if tiempo_respuesta else None,
                uso_pista,
                id_estudiante,
                id_ejercicio,
                id_opcion_sel,
                None,
            ),
        )
        id_respuesta = cursor.fetchone()["id_respuesta"]

        # 3) Puntaje simple (0 o 100)
        puntaje = 100 if es_correcta else 0
        cursor.execute(
            """
            INSERT INTO puntajes (puntaje, id_competencia, id_estudiante)
            VALUES (%s, %s, %s)
        """,
            (puntaje, id_competencia, id_estudiante),
        )

        # 4) Registrar progreso
        nivel_actual_str = f"Nivel {nivel_competencia}" if nivel_competencia else None
        estado = "correcto" if es_correcta else "incorrecto"
        if uso_pista:
            estado += "_con_pista"

        cursor.execute(
            """
            INSERT INTO progreso
                (nivel_actual, estado, tiempo_respuesta, id_estudiante, id_ejercicio)
            VALUES (%s, %s, %s, %s, %s)
        """,
            (
                nivel_actual_str,
                estado,
                float(tiempo_respuesta) if tiempo_respuesta else None,
                id_estudiante,
                id_ejercicio,
            ),
        )

        # 5) Actualizar progreso general del estudiante (por áreas)
        actualizar_progreso_estudiante(con, cursor, id_estudiante)

        # 6) Predicción con el modelo ML
        nivel_ml_texto = None
        nivel_competencia_int = None
        nivel_global_texto = None

        try:
            nivel_ml_texto = predecir_nivel_competencia(
                cursor, id_estudiante, id_competencia
            )
        except Exception as e:
            print("⚠️ Error en predecir_nivel_competencia:", e)
            nivel_ml_texto = None

        # Intentar actualizar tabla nivel_estudiante_competencia;
        # si algo falla, seguimos con la lógica por tiempo/pista.
        if nivel_ml_texto is not None:
            try:
                nivel_competencia_int, nivel_global_texto = (
                    actualizar_nivel_estudiante_competencia(
                        cursor, id_estudiante, id_competencia, nivel_ml_texto
                    )
                )

                if nivel_ml_texto == "alto":
                    nuevo_ajuste = "mas_dificil"
                    mostrar_pista = False
                    mensaje = "Vas muy bien, subimos un poco la dificultad."
                elif nivel_ml_texto == "medio":
                    nuevo_ajuste = "igual"
                    mostrar_pista = uso_pista or not es_correcta
                    mensaje = "Mantendremos el nivel actual y reforzaremos."
                else:  # "bajo"
                    nuevo_ajuste = "mas_facil"
                    mostrar_pista = True
                    mensaje = "Bajaremos un poco la dificultad para reforzar la competencia."

            except Exception as e:
                print("⚠️ Error actualizando nivel_estudiante_competencia:", e)
                nivel_ml_texto = None  # forzar uso de la lógica clásica

        if nivel_ml_texto is None:
            # Fallback: lógica antigua basada en tiempo y pista
            RAPIDO = 45
            LENTO = 90
            t = tiempo_respuesta or 0

            if es_correcta:
                if not uso_pista and t <= RAPIDO:
                    nuevo_ajuste = "mas_dificil"
                    mostrar_pista = False
                    mensaje = "¡Excelente! Resolveremos algo más desafiante."
                elif uso_pista or t > LENTO:
                    nuevo_ajuste = "igual"
                    mostrar_pista = False
                    mensaje = "Muy bien, seguiremos con un nivel similar."
                else:
                    nuevo_ajuste = "mas_dificil"
                    mostrar_pista = False
                    mensaje = "Buen trabajo, aumentaremos la dificultad."
            else:
                if uso_pista or t > LENTO:
                    nuevo_ajuste = "mas_facil"
                    mostrar_pista = True
                    mensaje = "Veremos un ejercicio un poco más sencillo."
                else:
                    nuevo_ajuste = "igual"
                    mostrar_pista = True
                    mensaje = "Intentemos un nivel similar con pista."
        con.commit()

        return jsonify(
            {
                "correcta": es_correcta,
                "mostrarPista": mostrar_pista,
                "mensaje": mensaje,
                "nuevoAjuste": nuevo_ajuste,
                "idRespuesta": id_respuesta,
                "nivelMLCompetencia": nivel_ml_texto,
                "nivelCompetenciaInt": nivel_competencia_int,
                "nivelGlobal": nivel_global_texto,
            }
        ), 200

    except Exception as e:
        con.rollback()
        print("Error en /tutor/responder:", e)
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        con.close()


# ============================================
#  POST /tutor/subir_desarrollo
# ============================================
@ws_tutor.route("/subir_desarrollo", methods=["POST"])
def subir_desarrollo():
    print(">>> /tutor/subir_desarrollo: petición recibida")

    id_respuesta = request.form.get("idRespuesta", type=int)
    archivo = request.files.get("archivo")

    print("   idRespuesta en form:", id_respuesta)
    print("   archivos recibidos:", list(request.files.keys()))

    if not id_respuesta or not archivo:
        print("   Faltan datos, no se sube nada")
        return (
            jsonify(
                {
                    "status": False,
                    "message": "idRespuesta y archivo son obligatorios",
                }
            ),
            400,
        )

    ext = os.path.splitext(archivo.filename)[1].lower()
    filename = secure_filename(f"resp_{id_respuesta}{ext}")
    ruta_fisica = os.path.join(DESARROLLOS_FOLDER, filename)
    print("   Guardando archivo en:", ruta_fisica)

    try:
        # Guarda el archivo en el disco
        archivo.save(ruta_fisica)

        # Ruta relativa dentro del proyecto
        ruta_relativa = f"/static/desarrollos_alumno/{filename}"

        # URL absoluta con host + puerto del API
        base = request.host_url.rstrip("/")
        url_abs = base + ruta_relativa

        # Guarda la URL COMPLETA en la BD
        con = Conexion()
        cursor = con.cursor()
        cursor.execute(
            """
            UPDATE respuestas_estudiantes
            SET desarrollo_url = %s
            WHERE id_respuesta = %s
        """,
            (url_abs, id_respuesta),
        )
        con.commit()
        cursor.close()
        con.close()

        print("   Archivo guardado OK. URL:", url_abs)

        return (
            jsonify(
                {
                    "status": True,
                    "message": "Desarrollo subido correctamente",
                    "desarrolloUrl": url_abs,
                }
            ),
            200,
        )

    except Exception as e:
        print("!! Error en /tutor/subir_desarrollo:", e)
        return (
            jsonify(
                {
                    "status": False,
                    "message": str(e),
                }
            ),
            500,
        )


# ================================
#  GET /tutor/nivel_actual
# ================================
@ws_tutor.route("/nivel_actual", methods=["GET"])
def nivel_actual():
    id_estudiante = request.args.get("idEstudiante", type=int)
    id_competencia = request.args.get("idCompetencia", type=int)

    if not id_estudiante or not id_competencia:
        return (
            jsonify(
                {
                    "status": False,
                    "error": "idEstudiante e idCompetencia son obligatorios",
                }
            ),
            400,
        )

    con = Conexion()
    cursor = con.cursor()

    try:
        nivel_ml = predecir_nivel_competencia(cursor, id_estudiante, id_competencia)

        cursor.execute(
            """
            SELECT
                COUNT(*)       AS total_intentos,
                AVG(puntaje)   AS promedio_puntaje
            FROM puntajes
            WHERE id_estudiante = %s
              AND id_competencia = %s
            """,
            (id_estudiante, id_competencia),
        )
        row = cursor.fetchone() or {}
        total_intentos = row.get("total_intentos") or 0
        promedio_puntaje = row.get("promedio_puntaje") or 0.0

        return jsonify(
            {
                "status": True,
                "idEstudiante": id_estudiante,
                "idCompetencia": id_competencia,
                "nivelML": nivel_ml,
                "totalIntentos": int(total_intentos),
                "promedioPuntaje": float(promedio_puntaje),
            }
        ), 200

    except Exception as e:
        print("Error en /tutor/nivel_actual:", e)
        return jsonify({"status": False, "error": str(e)}), 500
    finally:
        cursor.close()
        con.close()


# ================================
#  GET /tutor/sugerencias/...
# ================================
@ws_tutor.route("/sugerencias/<int:id_estudiante>/<int:id_competencia>", methods=["GET"])
def sugerencias_ejercicios(id_estudiante: int, id_competencia: int):
    """
    Devuelve una lista de ejercicios recomendados para un estudiante
    en una competencia específica.
    """
    limite = request.args.get("limite", default=5, type=int)

    con = Conexion()
    cursor = con.cursor()

    try:
        # 1) Obtener nivel ML del estudiante en esa competencia
        nivel_ml = predecir_nivel_competencia(cursor, id_estudiante, id_competencia)

        filtro_nivel = ""
        if nivel_ml == "bajo":
            filtro_nivel = "AND c.nivel <= 3"
        elif nivel_ml == "medio":
            filtro_nivel = "AND c.nivel BETWEEN 3 AND 5"
        elif nivel_ml == "alto":
            filtro_nivel = "AND c.nivel >= 5"

        # 2) Seleccionar ejercicios no resueltos por el estudiante
        sql = f"""
            SELECT 
                e.id_ejercicio,
                e.descripcion      AS enunciado,
                e.imagen_url       AS imagen_url,
                c.id_competencia,
                c.descripcion      AS competencia,
                c.area,
                c.nivel
            FROM ejercicios e
            JOIN competencias c
              ON e.id_competencia = c.id_competencia
            WHERE e.id_competencia = %s
              AND NOT EXISTS (
                    SELECT 1
                    FROM respuestas_estudiantes r
                    WHERE r.id_ejercicio = e.id_ejercicio
                      AND r.id_estudiante = %s
              )
              {filtro_nivel}
            ORDER BY RANDOM()
            LIMIT %s
        """
        cursor.execute(sql, (id_competencia, id_estudiante, limite))
        ejercicios = cursor.fetchall()

        if not ejercicios:
            return jsonify(
                {
                    "status": True,
                    "nivelML": nivel_ml,
                    "ejercicios": [],
                    "mensaje": "No se encontraron ejercicios recomendados para esta competencia.",
                }
            ), 200

        ids_ejercicios = [e["id_ejercicio"] for e in ejercicios]

        # 3) Cargar opciones
        cursor.execute(
            """
            SELECT id_opcion, letra, descripcion, id_ejercicio
            FROM opciones_ejercicio
            WHERE id_ejercicio = ANY(%s)
            ORDER BY id_ejercicio, letra
            """,
            (ids_ejercicios,),
        )
        opciones_rows = cursor.fetchall()

        opciones_por_ejercicio = {}
        for o in opciones_rows:
            ide = o["id_ejercicio"]
            opciones_por_ejercicio.setdefault(ide, []).append(
                {
                    "idOpcion": o["id_opcion"],
                    "letra": o["letra"],
                    "texto": o["descripcion"],
                }
            )

        # 4) Armar DTO con URL ABSOLUTA para la imagen
        ejercicios_dto = []
        # Usamos la misma base del proyecto WEB para las imágenes de ejercicios
        base = WEB_BASE_URL.rstrip("/")


        for e in ejercicios:
            ide = e["id_ejercicio"]
            imagen_rel = e["imagen_url"]

            if imagen_rel:
                if imagen_rel.startswith("http://") or imagen_rel.startswith("https://"):
                    imagen_url_abs = imagen_rel
                else:
                    imagen_rel = imagen_rel.strip()

                    if imagen_rel.startswith("static/"):
                        imagen_rel = "/" + imagen_rel

                    if not imagen_rel.startswith("/static/"):
                        if imagen_rel.startswith("/"):
                            imagen_rel = "/static" + imagen_rel
                        else:
                            imagen_rel = "/static/" + imagen_rel

                    imagen_url_abs = base + imagen_rel
            else:
                imagen_url_abs = None

            ejercicios_dto.append(
                {
                    "idEjercicio": ide,
                    "idCompetencia": e["id_competencia"],
                    "enunciado": e["enunciado"],
                    "imagenUrl": imagen_url_abs,
                    "opciones": opciones_por_ejercicio.get(ide, []),
                    "pista": None,
                }
            )


        return jsonify(
            {
                "status": True,
                "nivelML": nivel_ml,
                "ejercicios": ejercicios_dto,
            }
        ), 200

    except Exception as e:
        print("Error en /tutor/sugerencias:", e)
        return jsonify({"status": False, "error": str(e)}), 500

    finally:
        cursor.close()
        con.close()
