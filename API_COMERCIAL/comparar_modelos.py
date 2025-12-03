# comparar_modelos.py
"""
Script para comparar tres modelos de clasificación:
    - Árbol de Decisión
    - Regresión Logística
    - KNN (k=3)

Usa los datos cargados desde la BD mediante datos_ml.cargar_datos_desde_bd().

Ejecución:
    (venv) python comparar_modelos.py
"""

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
)
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier

from datos_ml import cargar_datos_desde_bd


def comparar_modelos():
    # 1) Cargar datos desde BD
    X, y = cargar_datos_desde_bd()

    if X.size == 0 or y.size == 0:
        print("⚠️ No hay datos suficientes en puntajes para entrenar los modelos.")
        return

    print("✅ Datos listos para entrenamiento:")
    print("   - X.shape:", X.shape)
    print("   - y.shape:", y.shape)
    print()

    # 2) Codificar etiquetas (bajo/medio/alto) a valores numéricos
    encoder = LabelEncoder()
    y_encoded = encoder.fit_transform(y)
    clases = list(encoder.classes_)
    print("🧾 Clases (etiquetas):", clases)
    print()

    # 3) Separar en entrenamiento y prueba
    # Si hay muy pocas muestras, usamos un test_size un poco mayor
    test_size = 0.25 if len(X) > 4 else 0.33

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y_encoded,
        test_size=test_size,
        random_state=42,
        stratify=y_encoded,  # mantiene proporción de clases
    )

    print(f"📚 Tamaño entrenamiento: {len(X_train)}")
    print(f"🧪 Tamaño prueba: {len(X_test)}")
    print()

    # 4) Definir los tres modelos a comparar
    modelos = {
        "Árbol de Decisión": DecisionTreeClassifier(
            random_state=42,
            max_depth=5,  # profundidad moderada
        ),
        "Regresión Logística": LogisticRegression(
            max_iter=1000,
            multi_class="auto",
        ),
        "KNN (k=3)": KNeighborsClassifier(
            n_neighbors=3
        ),
    }

    resultados = []

    # 5) Entrenar y evaluar cada modelo
    for nombre, modelo in modelos.items():
        print("=======================================")
        print(f"🔷 Modelo: {nombre}")
        print("=======================================")

        try:
            modelo.fit(X_train, y_train)
            y_pred = modelo.predict(X_test)

            acc = accuracy_score(y_test, y_pred)
            resultados.append((nombre, acc))

            print(f"✅ Accuracy: {acc:.4f}")
            print()
            print("📊 Classification report:")
            print(
                classification_report(
                    y_test,
                    y_pred,
                    target_names=clases,
                    digits=4,
                )
            )
            print("📊 Matriz de confusión (filas = real, columnas = predicho):")
            print(confusion_matrix(y_test, y_pred))
            print()

            # Solo el árbol tiene feature_importances_
            if hasattr(modelo, "feature_importances_"):
                print("🌳 Importancia de las features (Árbol de Decisión):")
                nombres_features = [
                    "total_intentos",
                    "promedio_puntaje",
                    "min_puntaje",
                    "max_puntaje",
                    "tasa_aprobados",
                ]
                for nombre_f, imp in zip(
                    nombres_features, modelo.feature_importances_
                ):
                    print(f"   - {nombre_f}: {imp:.3f}")
                print()

        except Exception as e:
            print(f"❌ Error entrenando el modelo {nombre}: {e}")
            print()

    # 6) Resumen final de accuracy
    print("=======================================")
    print("🏁 RESUMEN DE ACCURACY POR MODELO")
    print("=======================================")
    for nombre, acc in resultados:
        print(f"- {nombre}: {acc:.4f}")

    if resultados:
        mejor = max(resultados, key=lambda t: t[1])
        print()
        print(
            f"✅ Mejor modelo según accuracy: {mejor[0]} "
            f"(accuracy = {mejor[1]:.4f})"
        )


if __name__ == "__main__":
    comparar_modelos()
