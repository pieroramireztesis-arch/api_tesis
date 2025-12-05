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
        return jsonify({"status": False, "error": "idEstudiante es obligatorio"}), 400

    con = Conexion()
    cursor = con.cursor()

    try:
        # ===========================================================
        # 1) Últimos 5 ejercicios respondidos → evitar repetición inmediata
        # ===========================================================
        cursor.execute("""
            SELECT id_ejercicio
            FROM respuestas_estudiantes
            WHERE id_estudiante = %s
            ORDER BY id_respuesta DESC
            LIMIT 5
        """, (id_estudiante,))
        recientes = [r["id_ejercicio"] for r in cursor.fetchall()]

        # ===========================================================
        # 2) Ejercicios con 3 intentos incorrectos → NO repetir jamás
        # ===========================================================
        cursor.execute("""
            SELECT r.id_ejercicio
            FROM respuestas_estudiantes r
            JOIN opciones_ejercicio o ON o.id_opcion = r.id_opcion
            WHERE r.id_estudiante = %s
            GROUP BY r.id_ejercicio
            HAVING SUM(CASE WHEN o.es_correcta THEN 1 ELSE 0 END) = 0
               AND COUNT(*) >= 3
        """, (id_estudiante,))
        bloqueados = [r["id_ejercicio"] for r in cursor.fetchall()]

        # ===========================================================
        # 3) Construir filtros de selección
        # ===========================================================
        filtros = []
        params = []

        if id_dominio:
            filtros.append("e.id_competencia = %s")
            params.append(id_dominio)

        filtros.append("""
            NOT EXISTS(
                SELECT 1
                FROM respuestas_estudiantes r
                JOIN opciones_ejercicio o ON o.id_opcion = r.id_opcion
                WHERE r.id_ejercicio = e.id_ejercicio
                  AND r.id_estudiante = %s
                  AND o.es_correcta = TRUE
            )
        """)
        params.append(id_estudiante)

        if recientes:
            filtros.append("e.id_ejercicio NOT IN (" + ",".join(["%s"] * len(recientes)) + ")")
            params.extend(recientes)

        if bloqueados:
            filtros.append("e.id_ejercicio NOT IN (" + ",".join(["%s"] * len(bloqueados)) + ")")
            params.extend(bloqueados)

        if ajuste == "mas_facil":
            filtros.append("c.nivel <= 2")
        elif ajuste == "mas_dificil":
            filtros.append("c.nivel >= 3")

        where = " AND ".join(filtros)
        if where:
            where = "WHERE " + where

        # ===========================================================
        # 4) Buscar ejercicio NUEVO (ideal)
        # ===========================================================
        cursor.execute(f"""
            SELECT e.id_ejercicio,
                   e.descripcion AS enunciado,
                   e.imagen_url,
                   c.id_competencia,
                   c.descripcion AS competencia
            FROM ejercicios e
            JOIN competencias c ON c.id_competencia = e.id_competencia
            {where}
            ORDER BY RANDOM()
            LIMIT 1
        """, tuple(params))

        ejercicio = cursor.fetchone()

        # ===========================================================
        # 5) Si NO hay ejercicios nuevos → permitir reforzar antiguos
        # ===========================================================
        if not ejercicio:
            cursor.execute("""
                SELECT e.id_ejercicio, e.descripcion AS enunciado,
                       e.imagen_url, c.id_competencia, c.descripcion AS competencia
                FROM ejercicios e
                JOIN competencias c ON c.id_competencia = e.id_competencia
                WHERE e.id_ejercicio NOT IN (
                    SELECT r.id_ejercicio
                    FROM respuestas_estudiantes r
                    JOIN opciones_ejercicio o ON o.id_opcion = r.id_opcion
                    WHERE r.id_estudiante = %s
                      AND o.es_correcta = TRUE
                )
                AND e.id_ejercicio NOT IN (
                    SELECT id_ejercicio
                    FROM respuestas_estudiantes
                    WHERE id_estudiante = %s
                    ORDER BY id_respuesta DESC
                    LIMIT 5
                )
                ORDER BY RANDOM()
                LIMIT 1
            """, (id_estudiante, id_estudiante))

            ejercicio = cursor.fetchone()

            if not ejercicio:
                return jsonify({
                    "status": True,
                    "sinEjercicios": True,
                    "mensaje": "No hay más ejercicios disponibles. ¡Buen trabajo!"
                })

        id_ejercicio = ejercicio["id_ejercicio"]

        # ===========================================================
        # 6) NORMALIZAR IMAGEN → SIEMPRE POR PUERTO 5000 (WEB_BASE_URL)
        # ===========================================================
        imagen_rel = ejercicio["imagen_url"]
        imagen_url_abs = None

        if imagen_rel:
            imagen_rel = imagen_rel.strip()

            if imagen_rel.startswith("http://") or imagen_rel.startswith("https://"):
                imagen_url_abs = imagen_rel
            else:
                # igual lógica que /tutor/sugerencias, pero usando WEB_BASE_URL
                if imagen_rel.startswith("static/"):
                    imagen_rel = "/" + imagen_rel

                if not imagen_rel.startswith("/static/"):
                    if imagen_rel.startswith("/"):
                        imagen_rel = "/static" + imagen_rel
                    else:
                        imagen_rel = "/static/" + imagen_rel

                base = WEB_BASE_URL.rstrip("/")        # 👈👈 AQUÍ EL CAMBIO CLAVE
                imagen_url_abs = base + imagen_rel

        # ===========================================================
        # 7) Cargar opciones del ejercicio
        # ===========================================================
        cursor.execute("""
            SELECT id_opcion, letra, descripcion
            FROM opciones_ejercicio
            WHERE id_ejercicio = %s
            ORDER BY letra
        """, (id_ejercicio,))

        opciones = [
            {"idOpcion": o["id_opcion"], "letra": o["letra"], "texto": o["descripcion"]}
            for o in cursor.fetchall()
        ]

        return jsonify({
            "status": True,
            "sinEjercicios": False,
            "idEjercicio": ejercicio["id_ejercicio"],
            "idCompetencia": ejercicio["id_competencia"],
            "enunciado": ejercicio["enunciado"],
            "imagenUrl": imagen_url_abs,
            "opciones": opciones,
            "pista": None,
            "requiereDesarrollo": False
        })

    except Exception as e:
        print("ERROR en ejercicio_siguiente:", e)
        return jsonify({"status": False, "error": str(e)}), 500

    finally:
        cursor.close()
        con.close()



# =========================================
#  FUNCION AUX: Actualizar progreso_estudiante
# =========================================
def actualizar_progreso_estudiante(con, cursor, id_estudiante):
    """
    Calcula el progreso por competencia y general usando
    LA MISMA LÓGICA que:
      - /progreso/resumen   (API)
      - /progreso/por_competencia (API)
      - ws/reportes.reporte_progreso (WEB)

    Mapa de áreas -> columnas de la tabla estudiante:
      - 'cantidad'                        -> operaciones_basicas
      - 'regularidad_equivalencia_cambio' -> ecuaciones
      - 'forma_movimiento_localizacion'   -> funciones
      - 'gestion_datos_incertidumbre'     -> geometria
    """

    PESO_NUEVO = 1.0
    PESO_REPETIDO = 0.30

    # === Cálculo por competencia (igual que en ws_progreso / ws_reportes) ===
    cursor.execute(
        """
        SELECT
            c.area,
            COUNT(DISTINCT e.id_ejercicio) AS total,

            COUNT(
                DISTINCT CASE WHEN o.es_correcta = TRUE THEN r.id_ejercicio END
            ) AS distintos_correctos,

            COUNT(
                CASE WHEN o.es_correcta = TRUE THEN 1 END
            ) AS correctos_totales

        FROM competencias c
        LEFT JOIN ejercicios e
            ON e.id_competencia = c.id_competencia
        LEFT JOIN respuestas_estudiantes r
            ON r.id_ejercicio = e.id_ejercicio
           AND r.id_estudiante = %s
        LEFT JOIN opciones_ejercicio o
            ON o.id_opcion = r.id_opcion
        WHERE c.id_competencia BETWEEN 1 AND 4
        GROUP BY c.id_competencia, c.area
        ORDER BY c.id_competencia
        """,
        (id_estudiante,),
    )

    rows = cursor.fetchall()

    cant = reg = forma = datos = None

    for row in rows:
        area = row["area"]
        total = row["total"] or 0
        d_correctos = row["distintos_correctos"] or 0
        t_correctos = row["correctos_totales"] or 0

        repetidos = max(0, t_correctos - d_correctos)

        if total > 0:
            puntaje = (
                d_correctos * PESO_NUEVO +
                repetidos * PESO_REPETIDO
            ) / float(total)
        else:
            puntaje = 0.0

        porcentaje = int(round(puntaje * 100))
        porcentaje = max(0, min(100, porcentaje))

        if area == "cantidad":
            cant = porcentaje
        elif area == "regularidad_equivalencia_cambio":
            reg = porcentaje
        elif area == "forma_movimiento_localizacion":
            forma = porcentaje
        elif area == "gestion_datos_incertidumbre":
            datos = porcentaje

    # === Progreso general = promedio de las 4 competencias ===
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
    ajuste_actual = data.get("ajuste")  # opcional

    if not id_estudiante or not id_ejercicio or not id_opcion_sel:
        return jsonify({"status": False, "error": "Faltan campos obligatorios"}), 400

    con = Conexion()
    cursor = con.cursor()

    try:
        # ============================================================
        # 1) Verificar opción seleccionada
        # ============================================================
        cursor.execute("""
            SELECT o.es_correcta,
                   e.id_competencia,
                   c.nivel AS nivel_competencia
            FROM opciones_ejercicio o
            JOIN ejercicios e ON e.id_ejercicio = o.id_ejercicio
            JOIN competencias c ON c.id_competencia = e.id_competencia
            WHERE o.id_opcion = %s
        """, (id_opcion_sel,))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({"status": False, "error": "Opción no válida"}), 404

        es_correcta = bool(row["es_correcta"])
        id_competencia = row["id_competencia"]
        nivel_competencia = row["nivel_competencia"]

        # ============================================================
        # 2) Registrar respuesta base
        # ============================================================
        cursor.execute("""
            INSERT INTO respuestas_estudiantes
                (respuesta_texto, respuesta_imagen, fecha,
                 tiempo_respuesta, uso_pista,
                 id_estudiante, id_ejercicio, id_opcion)
            VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s)
            RETURNING id_respuesta
        """, (
            None,
            None,
            tiempo_respuesta,
            uso_pista,
            id_estudiante,
            id_ejercicio,
            id_opcion_sel
        ))
        id_respuesta = cursor.fetchone()["id_respuesta"]

        # ============================================================
        # 3) Registrar puntaje 0/100
        # ============================================================
        puntaje = 100 if es_correcta else 0
        cursor.execute("""
            INSERT INTO puntajes (puntaje, fecha_registro, id_competencia, id_estudiante)
            VALUES (%s, NOW(), %s, %s)
        """, (puntaje, id_competencia, id_estudiante))

        # ============================================================
        # 4) Registrar progreso
        # ============================================================
        estado = "correcto" if es_correcta else "incorrecto"
        if uso_pista:
            estado += "_con_pista"

        cursor.execute("""
            INSERT INTO progreso
                (nivel_actual, estado, tiempo_respuesta, id_estudiante, id_ejercicio)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            f"Nivel {nivel_competencia}",
            estado,
            tiempo_respuesta,
            id_estudiante,
            id_ejercicio
        ))

        # Actualizar progreso general por competencias MINEDU
        actualizar_progreso_estudiante(con, cursor, id_estudiante)

        # ============================================================
        # 5) ML → Intentar predecir nivel
        # ============================================================
        try:
            nivel_ml = predecir_nivel_competencia(cursor, id_estudiante, id_competencia)
        except:
            nivel_ml = None

        # ============================================================
        # 6) REGLA CTO: Reforzar incorrectos máximo 2 veces
        # ============================================================
        cursor.execute("""
            SELECT COUNT(*)
            FROM respuestas_estudiantes r
            JOIN opciones_ejercicio o ON o.id_opcion = r.id_opcion
            WHERE r.id_estudiante = %s
              AND r.id_ejercicio = %s
              AND o.es_correcta = FALSE
        """, (id_estudiante, id_ejercicio))
        
        intentos_incorrectos = cursor.fetchone()["count"]

        # ============================================================
        # 7) Determinar ajuste final
        # ============================================================
        if not es_correcta and intentos_incorrectos < 2:
            # 🔥 Reforzar dos veces máximo
            nuevo_ajuste = "igual"
            mostrar_pista = True
            mensaje = "Vamos a reforzar este ejercicio una vez más."

        else:
            # Ya no se refuerza → avanzamos con ML o fallback
            if nivel_ml == "alto":
                nuevo_ajuste = "mas_dificil"
                mostrar_pista = False
                mensaje = "Excelente, aumentaremos la dificultad."

            elif nivel_ml == "medio":
                nuevo_ajuste = "igual"
                mostrar_pista = not es_correcta or uso_pista
                mensaje = "Bien, continuamos reforzando este nivel."

            elif nivel_ml == "bajo":
                nuevo_ajuste = "mas_facil"
                mostrar_pista = True
                mensaje = "Bajaremos un poco la dificultad para reforzar."

            else:
                # Fallback sin ML
                if es_correcta:
                    nuevo_ajuste = "mas_dificil"
                    mostrar_pista = False
                    mensaje = "Perfecto, probemos algo más difícil."
                else:
                    nuevo_ajuste = "igual"
                    mostrar_pista = True
                    mensaje = "Intentemos otro ejercicio similar."

        con.commit()

        return jsonify({
            "status": True,
            "correcta": es_correcta,
            "mostrarPista": mostrar_pista,
            "nuevoAjuste": nuevo_ajuste,
            "mensaje": mensaje,
            "nivelML": nivel_ml,
            "intentosIncorrectos": intentos_incorrectos,
            "idRespuesta": id_respuesta
        }), 200

    except Exception as e:
        con.rollback()
        print("ERROR en /tutor/responder:", e)
        return jsonify({"status": False, "error": str(e)}), 500

    finally:
        cursor.close()
        con.close()

# ============================================
#  POST /tutor/subir_desarrollo  (CTO VERSION FINAL)
# ============================================
@ws_tutor.route("/subir_desarrollo", methods=["POST"])
def subir_desarrollo():
    print(">>> /tutor/subir_desarrollo: petición recibida")

    # -------------------------
    # 1) LEER CAMPOS DEL FORM
    # -------------------------
    id_respuesta = request.form.get("idRespuesta", type=int)
    archivo = request.files.get("archivo")

    print("   idRespuesta:", id_respuesta)
    print("   archivo recibido:", archivo.filename if archivo else None)

    if not id_respuesta:
        return jsonify({
            "status": False,
            "message": "idRespuesta es obligatorio"
        }), 400

    if not archivo:
        return jsonify({
            "status": False,
            "message": "No se recibió archivo"
        }), 400

    # -------------------------
    # 2) VALIDAR EXTENSIÓN
    # -------------------------
    nombre_original = archivo.filename
    ext = os.path.splitext(nombre_original)[1].lower()

    extensiones_permitidas = {".jpg", ".jpeg", ".png", ".pdf"}

    if ext not in extensiones_permitidas:
        return jsonify({
            "status": False,
            "message": f"Extensión no permitida ({ext}). Solo: JPG, PNG, PDF"
        }), 400

    # -------------------------
    # 3) VALIDAR EXISTENCIA DE id_respuesta
    # -------------------------
    con = Conexion()
    cursor = con.cursor()

    cursor.execute("""
        SELECT id_respuesta
        FROM respuestas_estudiantes
        WHERE id_respuesta = %s
    """, (id_respuesta,))
    row = cursor.fetchone()

    if not row:
        cursor.close()
        con.close()
        return jsonify({
            "status": False,
            "message": "La respuesta indicada no existe en la base de datos"
        }), 404

    # -------------------------
    # 4) GENERAR NOMBRE SEGURO
    # -------------------------
    filename = secure_filename(f"resp_{id_respuesta}{ext}")
    ruta_fisica = os.path.join(DESARROLLOS_FOLDER, filename)
    ruta_rel = f"/static/desarrollos_alumno/{filename}"

    print("   Guardando en:", ruta_fisica)

    try:
        # -------------------------
        # 5) GUARDAR ARCHIVO EN DISCO
        # -------------------------
        archivo.save(ruta_fisica)

        # -------------------------
        # 6) GENERAR URL PÚBLICA REAL
        # -------------------------
        base = request.host_url.rstrip("/")  # ejemplo: http://192.168.1.13:3008
        url_abs = base + ruta_rel

        print("   Archivo guardado correctamente. URL pública:", url_abs)

        # -------------------------
        # 7) ACTUALIZAR BD
        # -------------------------
        cursor.execute("""
            UPDATE respuestas_estudiantes
            SET desarrollo_url = %s
            WHERE id_respuesta = %s
        """, (url_abs, id_respuesta))

        con.commit()

        return jsonify({
            "status": True,
            "message": "Desarrollo subido correctamente",
            "desarrolloUrl": url_abs
        }), 200

    except Exception as e:
        print("!! ERROR al guardar desarrollo:", e)
        con.rollback()
        return jsonify({
            "status": False,
            "message": f"Error al guardar el archivo: {str(e)}"
        }), 500

    finally:
        cursor.close()
        con.close()

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
                    JOIN opciones_ejercicio o
                      ON o.id_opcion = r.id_opcion
                    WHERE r.id_ejercicio = e.id_ejercicio
                      AND r.id_estudiante = %s
                      AND o.es_correcta = TRUE
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
