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

UMBRAL_APROBADO = 60.0
UMBRAL_BAJO     = 40.0
UMBRAL_MEDIO    = 70.0


def cargar_datos_desde_bd():
    con = Conexion()
    cur = con.cursor()

    cur.execute("""
        SELECT
            p.id_estudiante,
            p.id_competencia,
            COUNT(*)        AS total_intentos,
            AVG(p.puntaje)  AS promedio_puntaje,
            MIN(p.puntaje)  AS min_puntaje,
            MAX(p.puntaje)  AS max_puntaje,
            SUM(CASE WHEN p.puntaje >= %s THEN 1 ELSE 0 END) AS num_aprobados
        FROM puntajes p
        GROUP BY p.id_estudiante, p.id_competencia
        HAVING COUNT(*) >= 1
    """, (UMBRAL_APROBADO,))

    rows = cur.fetchall()
    cur.close()
    con.close()

    X = []
    y = []

    for row in rows:
        total     = row["total_intentos"] or 0
        promedio  = row["promedio_puntaje"]
        min_p     = row["min_puntaje"]
        max_p     = row["max_puntaje"]
        aprobados = row["num_aprobados"] or 0

        if promedio is None or total == 0:
            continue

        promedio = max(0.0, min(100.0, float(promedio)))
        min_p    = max(0.0, min(100.0, float(min_p)))
        max_p    = max(0.0, min(100.0, float(max_p)))
        tasa     = float(aprobados) / float(total)

        if promedio < UMBRAL_BAJO:
            nivel = "bajo"
        elif promedio < UMBRAL_MEDIO:
            nivel = "medio"
        else:
            nivel = "alto"

        X.append([float(total), promedio, min_p, max_p, tasa])
        y.append(nivel)

    # ✅ NUEVO: si hay muy pocas muestras de alguna clase,
    # agregamos datos sintéticos balanceados para que el modelo
    # aprenda todos los niveles
    conteo = {"bajo": 0, "medio": 0, "alto": 0}
    for nivel in y:
        conteo[nivel] += 1

    print("📊 Distribución real de datos:", conteo)

    # Si alguna clase tiene menos de 5 muestras, agregar sintéticos
    MIN_MUESTRAS = 10

    if conteo["alto"] < MIN_MUESTRAS:
        print(f"⚠️ Pocos datos 'alto' ({conteo['alto']}). Agregando sintéticos...")
        for _ in range(MIN_MUESTRAS - conteo["alto"]):
            total_s   = np.random.randint(5, 20)
            promedio_s = np.random.uniform(70, 100)
            min_s      = np.random.uniform(60, 80)
            max_s      = np.random.uniform(85, 100)
            tasa_s     = np.random.uniform(0.7, 1.0)
            X.append([float(total_s), promedio_s, min_s, max_s, tasa_s])
            y.append("alto")

    if conteo["medio"] < MIN_MUESTRAS:
        print(f"⚠️ Pocos datos 'medio' ({conteo['medio']}). Agregando sintéticos...")
        for _ in range(MIN_MUESTRAS - conteo["medio"]):
            total_s   = np.random.randint(3, 15)
            promedio_s = np.random.uniform(40, 70)
            min_s      = np.random.uniform(20, 50)
            max_s      = np.random.uniform(60, 85)
            tasa_s     = np.random.uniform(0.3, 0.7)
            X.append([float(total_s), promedio_s, min_s, max_s, tasa_s])
            y.append("medio")

    if conteo["bajo"] < MIN_MUESTRAS:
        print(f"⚠️ Pocos datos 'bajo' ({conteo['bajo']}). Agregando sintéticos...")
        for _ in range(MIN_MUESTRAS - conteo["bajo"]):
            total_s   = np.random.randint(1, 10)
            promedio_s = np.random.uniform(0, 40)
            min_s      = np.random.uniform(0, 30)
            max_s      = np.random.uniform(20, 50)
            tasa_s     = np.random.uniform(0.0, 0.3)
            X.append([float(total_s), promedio_s, min_s, max_s, tasa_s])
            y.append("bajo")

    X = np.array(X, dtype=float)
    y = np.array(y, dtype=object)

    print(f"✅ Total muestras (reales + sintéticas): {len(X)}")
    return X, y


def entrenar_modelo():
    X, y = cargar_datos_desde_bd()

    if X.size == 0:
        print("⚠️ No hay datos para entrenar.")
        return

    encoder   = LabelEncoder()
    y_encoded = encoder.fit_transform(y)

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=0.2, random_state=42,
            stratify=y_encoded if len(set(y_encoded)) > 1 else None
        )
    except ValueError:
        X_train, X_test = X, np.empty((0, X.shape[1]))
        y_train, y_test = y_encoded, np.array([])

    feature_names = [
        "total_intentos", "promedio_puntaje",
        "min_puntaje", "max_puntaje", "tasa_aprobados"
    ]

    modelo = DecisionTreeClassifier(
        random_state=42,
        max_depth=6,
        min_samples_split=4,
        class_weight="balanced"
    )
    modelo.fit(X_train, y_train)

    print("\n👉 n_features_in_:", modelo.n_features_in_)
    print("👉 Clases aprendidas:", list(encoder.classes_))
    print("👉 Importancias:")
    for name, imp in zip(feature_names, modelo.feature_importances_):
        print(f"   {name}: {imp:.3f}")

    if len(X_test) > 0:
        y_pred = modelo.predict(X_test)
        print("\n📈 Reporte en prueba:")
        print(classification_report(
            y_test, y_pred,
            target_names=encoder.classes_.astype(str),
            zero_division=0
        ))

    # Guardar
    with open("modelo_tutor.pkl", "wb") as f:
        pickle.dump({
            "modelo":          modelo,
            "encoder":         encoder,
            "feature_names":   feature_names,
            "umbral_aprobado": UMBRAL_APROBADO,
            "umbral_bajo":     UMBRAL_BAJO,
            "umbral_medio":    UMBRAL_MEDIO,
        }, f)

    print("\n✅ modelo_tutor.pkl guardado correctamente.")
    print("   Clases:", list(encoder.classes_))


if __name__ == "__main__":
    entrenar_modelo()