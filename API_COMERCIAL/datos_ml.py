# datos_ml.py
"""
Módulo de utilidades para cargar los datos de entrenamiento
desde la base de datos y construir el dataset (X, y).

Se agrupa la información a nivel de:
    (id_estudiante, id_competencia)

Features (columnas de X):
    - total_intentos
    - promedio_puntaje
    - min_puntaje
    - max_puntaje
    - tasa_aprobados

Etiqueta (y):
    - 'bajo'  si promedio < 40
    - 'medio' si 40 <= promedio < 70
    - 'alto'  si promedio >= 70
"""

import numpy as np
from conexionBD import Conexion


def cargar_datos_desde_bd():
    """
    Lee los datos de la tabla PUNTAJES y construye X, y.

    Devuelve:
        X: np.array de shape (n_muestras, 5)
        y: np.array de shape (n_muestras,)
    """
    con = Conexion()
    cur = con.cursor()

    cur.execute(
        """
        SELECT
            p.id_estudiante,
            p.id_competencia,
            COUNT(*)                             AS total_intentos,
            AVG(p.puntaje)                       AS promedio_puntaje,
            MIN(p.puntaje)                       AS min_puntaje,
            MAX(p.puntaje)                       AS max_puntaje,
            AVG(CASE WHEN p.puntaje >= 70
                     THEN 1 ELSE 0 END)         AS tasa_aprobados
        FROM puntajes p
        GROUP BY p.id_estudiante, p.id_competencia
        HAVING COUNT(*) >= 1
        """
    )

    rows = cur.fetchall()
    cur.close()
    con.close()

    X = []
    y = []

    for row in rows:
        total_intentos = row["total_intentos"] or 0
        prom = row["promedio_puntaje"]
        min_p = row["min_puntaje"]
        max_p = row["max_puntaje"]
        tasa = row["tasa_aprobados"]

        # Si no hay promedio, no usamos esta fila
        if prom is None:
            continue

        prom = float(prom)
        min_p = float(min_p) if min_p is not None else 0.0
        max_p = float(max_p) if max_p is not None else 0.0
        tasa = float(tasa) if tasa is not None else 0.0

        # Normalizamos el promedio al rango 0..100 por seguridad
        if prom < 0:
            prom = 0.0
        if prom > 100:
            prom = 100.0

        # Etiqueta segun el promedio
        if prom < 40:
            nivel = "bajo"
        elif prom < 70:
            nivel = "medio"
        else:
            nivel = "alto"

        X.append(
            [
                float(total_intentos),
                prom,
                min_p,
                max_p,
                tasa,
            ]
        )
        y.append(nivel)

    X = np.array(X, dtype=float)
    y = np.array(y, dtype=object)

    print("✅ Datos cargados desde BD (datos_ml.cargar_datos_desde_bd):")
    print("   - X.shape:", X.shape)
    print("   - y.shape:", y.shape)
    if len(X) > 0:
        print("   - Ejemplo X[0]:", X[0])
        print("   - Ejemplo y[0]:", y[0])
    print()

    return X, y


if __name__ == "__main__":
    # Pequeña prueba rápida si ejecutas:
    #   python datos_ml.py
    X, y = cargar_datos_desde_bd()
    print("Total de muestras:", len(X))
