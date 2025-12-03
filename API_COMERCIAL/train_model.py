"""
Script de entrenamiento para el módulo Tutor (STI).

Construye un modelo de estudiante simplificado a nivel
(id_estudiante, id_competencia), usando el historial de puntajes
de la tabla PUNTAJES.

El modelo:
- Usa un Árbol de Decisión para clasificar el NIVEL de dominio:
    "bajo" / "medio" / "alto"
- Usa como features:
    total_intentos, promedio, mínimo, máximo, tasa_aprobados
- Guarda (modelo, encoder, feature_names) en modelo_tutor.pkl

Ejecución:
    python train_model.py
"""

import pickle
import numpy as np

from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

from conexionBD import Conexion


# --------------------------------------------------------------------
# 0. Parámetros pedagógicos (puedes ajustarlos según MINEDU)
# --------------------------------------------------------------------
UMBRAL_APROBADO = 60.0     # puntaje considerado "aprobado"
UMBRAL_BAJO = 40.0         # promedio < 40  -> bajo
UMBRAL_MEDIO = 70.0        # 40 ≤ prom < 70 -> medio, resto -> alto


# --------------------------------------------------------------------
# 1. CARGA DE DATOS DESDE LA BD
# --------------------------------------------------------------------
def cargar_datos_desde_bd():
    """
    Construye el dataset a nivel (id_estudiante, id_competencia).

    Features (X):
        - total_intentos
        - promedio_puntaje (0..100)
        - min_puntaje
        - max_puntaje
        - tasa_aprobados = num_intentos_con_puntaje>=UMBRAL_APROBADO / total_intentos

    Etiqueta (y, nivel):
        - "bajo"  si promedio < UMBRAL_BAJO
        - "medio" si UMBRAL_BAJO <= promedio < UMBRAL_MEDIO
        - "alto"  si promedio >= UMBRAL_MEDIO
    """

    con = Conexion()
    cur = con.cursor()

    # IMPORTANTE: esta consulta solo usa agregaciones "clásicas"
    # que sirven en PostgreSQL, MySQL, etc.
    cur.execute(
        """
        SELECT
            p.id_estudiante,
            p.id_competencia,
            COUNT(*)                        AS total_intentos,
            AVG(p.puntaje)                  AS promedio_puntaje,
            MIN(p.puntaje)                  AS min_puntaje,
            MAX(p.puntaje)                  AS max_puntaje,
            SUM(
                CASE
                    WHEN p.puntaje >= %s THEN 1
                    ELSE 0
                END
            ) AS num_aprobados
        FROM puntajes p
        GROUP BY p.id_estudiante, p.id_competencia
        HAVING COUNT(*) >= 1
        """,
        (UMBRAL_APROBADO,),
    )

    rows = cur.fetchall()
    cur.close()
    con.close()

    X = []
    y = []

    for row in rows:
        # Si usas DictCursor, esto funciona.
        # Si usas cursor normal, row será tupla -> habría que ajustar índices.
        total_intentos = row["total_intentos"] or 0
        promedio = row["promedio_puntaje"]
        min_p = row["min_puntaje"]
        max_p = row["max_puntaje"]
        num_aprobados = row["num_aprobados"] or 0

        # Validaciones básicas
        if promedio is None or total_intentos is None or total_intentos == 0:
            continue

        promedio = float(promedio)
        min_p = float(min_p)
        max_p = float(max_p)

        # Normalizar por seguridad al rango 0..100
        promedio = max(0.0, min(100.0, promedio))
        min_p = max(0.0, min(100.0, min_p))
        max_p = max(0.0, min(100.0, max_p))

        # Tasa de intentos aprobados (0..1)
        tasa_aprobados = float(num_aprobados) / float(total_intentos)

        # Etiquetado de nivel según el promedio
        if promedio < UMBRAL_BAJO:
            nivel = "bajo"
        elif promedio < UMBRAL_MEDIO:
            nivel = "medio"
        else:
            nivel = "alto"

        X.append([
            float(total_intentos),
            promedio,
            min_p,
            max_p,
            tasa_aprobados,
        ])
        y.append(nivel)

    X = np.array(X, dtype=float)
    y = np.array(y, dtype=object)

    print("✅ Datos cargados desde BD:")
    print("   - Total filas (muestras):", len(X))
    if len(X) > 0:
        print("   - Ejemplo de X[0]:", X[0])
        print("   - Ejemplo de y[0]:", y[0])

    return X, y


# --------------------------------------------------------------------
# 2. ENTRENAMIENTO DEL MODELO
# --------------------------------------------------------------------
def entrenar_modelo():
    X, y = cargar_datos_desde_bd()

    if X.size == 0 or y.size == 0:
        print("⚠️ No hay datos suficientes en la tabla PUNTAJES para entrenar el modelo.")
        return

    print(f"\n📊 Total de muestras para entrenamiento: {len(X)}")
    print("   Clases presentes (niveles):", set(y))

    # Codificación de etiquetas (bajo/medio/alto → 0,1,2,...)
    encoder = LabelEncoder()
    y_encoded = encoder.fit_transform(y)

    # ----------------------------------------------------------------
    # 2.1 Train/Test split
    # ----------------------------------------------------------------
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y_encoded,
            test_size=0.2,
            random_state=42,
            stratify=y_encoded if len(set(y_encoded)) > 1 else None,
        )
    except ValueError:
        # Por si hay muy pocas muestras o solo una clase
        print("⚠️ Muy pocas muestras o solo una clase. Se entrenará con todos los datos.")
        X_train, X_test, y_train, y_test = X, np.empty((0, X.shape[1])), y_encoded, np.array([])

    print(f"\n📚 Tamaño entrenamiento: {len(X_train)} muestras")
    print(f"🧪 Tamaño prueba: {len(X_test)} muestras")

    # ----------------------------------------------------------------
    # 2.2 Definir y entrenar Árbol de Decisión
    # ----------------------------------------------------------------
    feature_names = [
        "total_intentos",
        "promedio_puntaje",
        "min_puntaje",
        "max_puntaje",
        "tasa_aprobados",
    ]

    modelo = DecisionTreeClassifier(
        random_state=42,
        max_depth=6,          # un poco más profundo porque hay más features
        min_samples_split=4,  # para evitar sobreajuste extremo
        class_weight="balanced",  # por si las clases están desbalanceadas
    )

    modelo.fit(X_train, y_train)

    print("\n👉 n_features_in_ del modelo entrenado:", modelo.n_features_in_)
    print("👉 Importancias de las features:")
    for name, imp in zip(feature_names, modelo.feature_importances_):
        print(f"   - {name}: {imp:.3f}")

    # ----------------------------------------------------------------
    # 2.3 Evaluación en conjunto de prueba
    # ----------------------------------------------------------------
    if len(X_test) > 0:
        y_pred = modelo.predict(X_test)

        print("\n📈 RESULTADOS EN CONJUNTO DE PRUEBA:")
        print(
            classification_report(
                y_test,
                y_pred,
                target_names=encoder.classes_.astype(str),
                zero_division=0,
            )
        )

        print("📊 MATRIZ DE CONFUSIÓN (filas = real, columnas = predicho):")
        print(confusion_matrix(y_test, y_pred))
    else:
        print("\n⚠️ No hay suficientes datos para generar un conjunto de prueba.")

    # ----------------------------------------------------------------
    # 2.4 Mostrar reglas del árbol
    # ----------------------------------------------------------------
    print("\n🌳 REGLAS DEL ÁRBOL DE DECISIÓN:")
    reglas = export_text(
        modelo,
        feature_names=feature_names,
        show_weights=True,
    )
    print(reglas)

    # ----------------------------------------------------------------
    # 2.5 Guardar modelo + encoder + nombres de features
    # ----------------------------------------------------------------
    MODEL_FILENAME = "modelo_tutor.pkl"
    with open(MODEL_FILENAME, "wb") as f:
        pickle.dump(
            {
                "modelo": modelo,
                "encoder": encoder,
                "feature_names": feature_names,
                "umbral_aprobado": UMBRAL_APROBADO,
                "umbral_bajo": UMBRAL_BAJO,
                "umbral_medio": UMBRAL_MEDIO,
            },
            f,
        )

    print(f"\n✅ Modelo entrenado y guardado en {MODEL_FILENAME}")
    print("   Clases aprendidas:", list(encoder.classes_))


if __name__ == "__main__":
    entrenar_modelo()
