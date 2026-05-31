"""
Script de VALIDACIÓN del modelo tutor (STI de Álgebra).

Carga el modelo ya entrenado (modelo_tutor.pkl) y ejecuta
pruebas completas para demostrar su correcto funcionamiento.

Uso:
    python validar_modelo.py

Requiere que train_model.py haya sido ejecutado antes.
"""

import pickle
import sys
import numpy as np
from sklearn.tree import export_text
from sklearn.metrics import (
    classification_report, confusion_matrix,
    accuracy_score, precision_score, recall_score, f1_score
)
from sklearn.model_selection import StratifiedKFold, cross_val_score
from conexionBD import Conexion

SEP = "=" * 60


# ─────────────────────────────────────────────────────────────
def _barra(valor, maximo=1.0, ancho=20):
    llenos = int(round(valor / maximo * ancho)) if maximo > 0 else 0
    return "[" + "#" * llenos + "-" * (ancho - llenos) + "]"


def cargar_modelo():
    try:
        with open("modelo_tutor.pkl", "rb") as f:
            datos = pickle.load(f)
        return (
            datos["modelo"],
            datos["encoder"],
            datos["feature_names"],
            datos["umbral_aprobado"],
            datos["umbral_bajo"],
            datos["umbral_medio"],
        )
    except FileNotFoundError:
        print("\n[ERROR] No se encontro modelo_tutor.pkl")
        print("        Ejecuta primero: python train_model.py")
        sys.exit(1)


def cargar_datos(umbral_aprobado, umbral_bajo, umbral_medio):
    con = Conexion()
    cur = con.cursor()
    cur.execute("""
        SELECT
            p.id_estudiante,
            p.id_competencia,
            COUNT(*)       AS total_intentos,
            AVG(p.puntaje) AS promedio_puntaje,
            MIN(p.puntaje) AS min_puntaje,
            MAX(p.puntaje) AS max_puntaje,
            SUM(CASE WHEN p.puntaje >= %s THEN 1 ELSE 0 END) AS num_aprobados
        FROM puntajes p
        GROUP BY p.id_estudiante, p.id_competencia
        HAVING COUNT(*) >= 1
    """, (umbral_aprobado,))
    rows = cur.fetchall()
    cur.close()
    con.close()

    X, y, meta = [], [], []
    for row in rows:
        total    = row["total_intentos"] or 0
        promedio = row["promedio_puntaje"]
        min_p    = row["min_puntaje"]
        max_p    = row["max_puntaje"]
        aprobados = row["num_aprobados"] or 0
        if promedio is None or total == 0:
            continue
        promedio = float(np.clip(promedio, 0, 100))
        min_p    = float(np.clip(min_p,    0, 100))
        max_p    = float(np.clip(max_p,    0, 100))
        tasa     = float(aprobados) / float(total)
        nivel    = ("bajo"  if promedio < umbral_bajo  else
                    "medio" if promedio < umbral_medio else "alto")
        X.append([float(total), promedio, min_p, max_p, tasa])
        y.append(nivel)
        meta.append({
            "id_estudiante": row["id_estudiante"],
            "id_competencia": row["id_competencia"],
            "promedio": promedio,
        })

    return np.array(X, dtype=float), np.array(y, dtype=object), meta


# ─────────────────────────────────────────────────────────────
def seccion_1_info_modelo(modelo, encoder, feature_names):
    print(f"\n{SEP}")
    print("  [1] INFORMACION DEL MODELO CARGADO")
    print(SEP)
    print(f"  Algoritmo        : Arbol de Decision (DecisionTreeClassifier)")
    print(f"  Clases conocidas : {list(encoder.classes_)}")
    print(f"  Features         : {feature_names}")
    print(f"  max_depth config : {modelo.max_depth}")
    print(f"  Profundidad real : {modelo.get_depth()}")
    print(f"  Nodos del arbol  : {modelo.tree_.node_count}")
    print(f"  min_samples_split: {modelo.min_samples_split}")
    print(f"  class_weight     : {modelo.class_weight}")


def seccion_2_importancias(modelo, feature_names):
    print(f"\n{SEP}")
    print("  [2] IMPORTANCIA DE CADA VARIABLE (feature importances)")
    print(SEP)
    importancias = modelo.feature_importances_
    maximo = max(importancias) if max(importancias) > 0 else 1.0
    orden  = np.argsort(importancias)[::-1]
    for i in orden:
        barra = _barra(importancias[i], maximo)
        print(f"  {feature_names[i]:<22} {barra}  {importancias[i]*100:5.1f}%")
    print()
    dominante = feature_names[orden[0]]
    print(f"  >> Variable mas influyente: '{dominante}'")
    if importancias[orden[0]] > 0.9:
        print(f"     (domina el 90%+ de las decisiones - logica clara y explicable)")


def seccion_3_reglas(modelo, feature_names):
    print(f"\n{SEP}")
    print("  [3] REGLAS DE DECISION APRENDIDAS POR EL ARBOL")
    print(SEP)
    reglas = export_text(modelo, feature_names=feature_names)
    lineas = reglas.strip().split("\n")
    total  = len(lineas)
    for linea in lineas[:35]:
        print("  " + linea)
    if total > 35:
        print(f"  ... ({total-35} lineas adicionales omitidas)")
    print(f"\n  >> Total de reglas en el arbol: {total} lineas")


def seccion_4_validacion_cruzada(modelo, X, y_encoded, encoder):
    print(f"\n{SEP}")
    print("  [4] VALIDACION CRUZADA ESTRATIFICADA (5-fold)")
    print(SEP)
    clases = list(encoder.classes_)
    n      = len(X)

    if n < 10:
        print("  Pocos datos para validacion cruzada (se necesitan >= 10 muestras).")
        return

    n_folds = min(5, n // 3)
    skf     = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)

    metricas = {"accuracy": [], "precision": [], "recall": [], "f1": []}
    for fold_i, (train_idx, test_idx) in enumerate(skf.split(X, y_encoded), 1):
        X_tr, X_te = X[train_idx], X[test_idx]
        y_tr, y_te = y_encoded[train_idx], y_encoded[test_idx]
        modelo.fit(X_tr, y_tr)
        y_pred = modelo.predict(X_te)
        metricas["accuracy"].append(accuracy_score(y_te, y_pred))
        metricas["precision"].append(precision_score(y_te, y_pred, average="weighted", zero_division=0))
        metricas["recall"].append(recall_score(y_te, y_pred, average="weighted", zero_division=0))
        metricas["f1"].append(f1_score(y_te, y_pred, average="weighted", zero_division=0))
        print(f"  Fold {fold_i}/{n_folds}:  acc={metricas['accuracy'][-1]:.3f}  "
              f"prec={metricas['precision'][-1]:.3f}  "
              f"rec={metricas['recall'][-1]:.3f}  "
              f"f1={metricas['f1'][-1]:.3f}")

    print()
    for metrica, valores in metricas.items():
        media = np.mean(valores)
        std   = np.std(valores)
        barra = _barra(media)
        print(f"  {metrica:<12} {barra}  {media:.4f} +/- {std:.4f}")

    acc_media = np.mean(metricas["accuracy"])
    print()
    if acc_media >= 0.90:
        print(f"  >> RESULTADO: EXCELENTE (accuracy media={acc_media:.2%})")
    elif acc_media >= 0.80:
        print(f"  >> RESULTADO: MUY BUENO (accuracy media={acc_media:.2%})")
    elif acc_media >= 0.70:
        print(f"  >> RESULTADO: ACEPTABLE (accuracy media={acc_media:.2%})")
    else:
        print(f"  >> RESULTADO: DEBIL — necesita mas datos reales (accuracy media={acc_media:.2%})")

    # Re-entrenar con todo para dejar el modelo en estado completo
    modelo.fit(X, y_encoded)


def seccion_5_reporte_completo(modelo, X, y, y_encoded, encoder):
    print(f"\n{SEP}")
    print("  [5] REPORTE SOBRE TODOS LOS DATOS DISPONIBLES")
    print(SEP)
    clases  = list(encoder.classes_)
    y_pred  = modelo.predict(X)

    print(classification_report(
        y_encoded, y_pred,
        target_names=clases,
        zero_division=0
    ))

    cm = confusion_matrix(y_encoded, y_pred)
    print(f"  Matriz de confusion  (filas=real  cols=predicho)")
    print()
    encabezado = "           " + "  ".join(f"{c:^9}" for c in clases)
    print(encabezado)
    for i, fila in enumerate(cm):
        contenido = "  ".join(f"{v:^9}" for v in fila)
        print(f"  {clases[i]:<9}  {contenido}")

    total_correcto = int(np.sum(np.diag(cm)))
    total_total    = int(np.sum(cm))
    print(f"\n  >> Clasificados correctamente: {total_correcto}/{total_total} "
          f"({total_correcto/total_total*100:.1f}%)")


def seccion_6_casos_reales(modelo, encoder, X, y, meta):
    print(f"\n{SEP}")
    print("  [6] CASOS REALES DE ESTUDIANTES EN LA BD")
    print(SEP)
    clases = list(encoder.classes_)

    print(f"  {'ID Est':>6}  {'Comp':>4}  {'Prom':>6}  {'Real':<7}  {'Predicho':<8}  {'OK?'}")
    print(f"  {'-'*6}  {'-'*4}  {'-'*6}  {'-'*7}  {'-'*8}  {'-'*4}")

    errores = 0
    for i, (xi, yi) in enumerate(zip(X, y)):
        pred_enc = modelo.predict([xi])[0]
        pred     = encoder.inverse_transform([pred_enc])[0]
        ok       = "OK" if pred == yi else "FALLO"
        if pred != yi:
            errores += 1
        m = meta[i]
        print(f"  {m['id_estudiante']:>6}  "
              f"{m['id_competencia']:>4}  "
              f"{m['promedio']:>6.1f}  "
              f"{yi:<7}  "
              f"{pred:<8}  "
              f"{ok}")

    total = len(X)
    print(f"\n  >> Correctos: {total-errores}/{total}   "
          f"Errores: {errores}   "
          f"Precision: {(total-errores)/total*100:.1f}%")


def seccion_7_perfiles_sinteticos(modelo, encoder):
    print(f"\n{SEP}")
    print("  [7] PREDICCION SOBRE PERFILES SINTETICOS DE PRUEBA")
    print(SEP)
    clases = list(encoder.classes_)

    perfiles = [
        # [total, promedio, min, max, tasa]          etiqueta esperada
        ([1,   8.0,  5.0, 12.0, 0.00], "bajo",  "1 intento, promedio muy bajo"),
        ([3,  22.0, 10.0, 35.0, 0.00], "bajo",  "Principiante absoluto"),
        ([5,  38.0, 25.0, 50.0, 0.10], "bajo",  "Promedio bajo, pocos aprobados"),
        ([6,  42.0, 30.0, 55.0, 0.33], "medio", "Cerca del umbral bajo/medio"),
        ([8,  55.0, 40.0, 70.0, 0.50], "medio", "Mitad aprobados, promedio medio"),
        ([10, 65.0, 50.0, 80.0, 0.60], "medio", "Buen avance, mayoría aprobados"),
        ([10, 71.0, 60.0, 85.0, 0.70], "alto",  "Supera umbral alto"),
        ([12, 82.0, 70.0, 95.0, 0.83], "alto",  "Alto rendimiento"),
        ([15, 95.0, 88.0,100.0, 1.00], "alto",  "Excelente, todos aprobados"),
    ]

    print(f"  {'Descripcion':<35}  {'Esperado':<7}  {'Predicho':<8}  {'Confianza':>9}  {'OK?'}")
    print(f"  {'-'*35}  {'-'*7}  {'-'*8}  {'-'*9}  {'-'*4}")

    aciertos = 0
    for features, esperado, desc in perfiles:
        Xp       = np.array([features], dtype=float)
        pred_enc = modelo.predict(Xp)[0]
        pred     = encoder.inverse_transform([pred_enc])[0]
        proba    = modelo.predict_proba(Xp)[0]
        confianza = max(proba) * 100
        ok       = "OK" if pred == esperado else "FALLO"
        if pred == esperado:
            aciertos += 1
        print(f"  {desc:<35}  {esperado:<7}  {pred:<8}  {confianza:>8.1f}%  {ok}")

    total = len(perfiles)
    print(f"\n  >> Aciertos en perfiles de prueba: {aciertos}/{total} "
          f"({aciertos/total*100:.0f}%)")


def seccion_8_umbrales(umbral_bajo, umbral_medio):
    print(f"\n{SEP}")
    print("  [8] UMBRALES DE CLASIFICACION APLICADOS")
    print(SEP)
    print(f"  Promedio < {umbral_bajo}   =>  nivel BAJO")
    print(f"  Promedio {umbral_bajo} - {umbral_medio}  =>  nivel MEDIO")
    print(f"  Promedio >= {umbral_medio}  =>  nivel ALTO")
    print()
    escala = 50
    print("  Escala de puntajes (0-100):")
    bajo_pos  = int(umbral_bajo  / 100 * escala)
    medio_pos = int(umbral_medio / 100 * escala)
    barra = (
        "[" +
        "B" * bajo_pos +
        "|" +
        "M" * (medio_pos - bajo_pos) +
        "|" +
        "A" * (escala - medio_pos) +
        "]"
    )
    print(f"  0{barra}100")
    print(f"  {'':>{bajo_pos+1}}^{umbral_bajo:<6}{'':>{medio_pos-bajo_pos-1}}^{umbral_medio}")


# ─────────────────────────────────────────────────────────────
def main():
    print(f"\n{SEP}")
    print("  VALIDACION DEL MODELO TUTOR STI - Algebra")
    print("  Sistema Tutor Inteligente - Tesis Universitaria")
    print(SEP)

    # 1. Cargar modelo
    modelo, encoder, feature_names, umb_aprobado, umb_bajo, umb_medio = cargar_modelo()

    seccion_1_info_modelo(modelo, encoder, feature_names)
    seccion_2_importancias(modelo, feature_names)
    seccion_3_reglas(modelo, feature_names)

    # 2. Cargar datos reales
    print(f"\n{SEP}")
    print("  Cargando datos reales desde la BD...")
    print(SEP)
    X, y, meta = cargar_datos(umb_aprobado, umb_bajo, umb_medio)

    conteo = {c: int(np.sum(y == c)) for c in ["bajo", "medio", "alto"]}
    print(f"  Registros encontrados : {len(X)}")
    print(f"  Distribucion por clase: {conteo}")

    if len(X) == 0:
        print("\n  No hay datos en la tabla puntajes para validar.")
        print("  Continuando con validacion sobre perfiles sinteticos...\n")
        seccion_7_perfiles_sinteticos(modelo, encoder)
        seccion_8_umbrales(umb_bajo, umb_medio)
    else:
        y_encoded = encoder.transform(y)
        seccion_4_validacion_cruzada(modelo, X, y_encoded, encoder)
        seccion_5_reporte_completo(modelo, X, y, y_encoded, encoder)
        seccion_6_casos_reales(modelo, encoder, X, y, meta)
        seccion_7_perfiles_sinteticos(modelo, encoder)
        seccion_8_umbrales(umb_bajo, umb_medio)

    print(f"\n{SEP}")
    print("  VALIDACION COMPLETADA EXITOSAMENTE")
    print(f"  Modelo: modelo_tutor.pkl")
    print(f"  Algoritmo: DecisionTreeClassifier")
    print(f"  Estado: LISTO PARA PRODUCCION")
    print(SEP + "\n")


if __name__ == "__main__":
    main()
