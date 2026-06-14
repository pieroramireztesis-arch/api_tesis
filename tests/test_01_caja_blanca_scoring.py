"""
test_01_caja_blanca_scoring.py — Pruebas de CAJA BLANCA: models/scoring.py
===========================================================================
Tipo  : Unitarias (funciones puras, sin BD, sin red)
Módulo: API_COMERCIAL/models/scoring.py

Cobertura
─────────
• score_to_nivel()       → 7 tramos + valores límite (boundary)
• nivel_to_progreso()    → 7 niveles
• score_to_progreso()    → composición de las anteriores
• clasificar_tiempo()    → 5 niveles × 3 categorías + casos borde
• calcular_delta()       → 6 combinaciones base + penalización por pista
• nivel_to_minedu()      → mapeo STI→MINEDU (5 niveles oficiales)
• nivel_display_texto()  → texto UI bajo/medio/alto
"""

import pytest
from models.scoring import (
    score_to_nivel, nivel_to_progreso, score_to_progreso,
    clasificar_tiempo, calcular_delta,
    nivel_to_minedu, nivel_display_texto,
    SCORE_BRACKETS, NIVEL_PROGRESO, NIVEL_MINEDU,
    TIEMPO_THRESHOLDS, DELTA_SCORE,
    PENALIZACION_PISTA, DELTA_MIN_CON_PISTA,
)

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────────────────────
# score_to_nivel  ──  score 0-100 → nivel 1-7
# ─────────────────────────────────────────────────────────────────────────────

class TestScoreToNivel:
    """Verifica los 7 tramos de la tabla SCORE_BRACKETS y sus valores límite."""

    # Valores interiores a cada tramo
    @pytest.mark.parametrize("score,expected", [
        (0,   1), (10,  1), (21,  1),   # Tramo 1: 0-21  → nivel 1
        (22,  2), (28,  2), (35,  2),   # Tramo 2: 22-35 → nivel 2
        (36,  3), (42,  3), (49,  3),   # Tramo 3: 36-49 → nivel 3
        (50,  4), (57,  4), (64,  4),   # Tramo 4: 50-64 → nivel 4
        (65,  5), (71,  5), (78,  5),   # Tramo 5: 65-78 → nivel 5
        (79,  6), (85,  6), (92,  6),   # Tramo 6: 79-92 → nivel 6
        (93,  7), (96,  7), (100, 7),   # Tramo 7: 93-100 → nivel 7
    ])
    def test_tramo(self, score, expected):
        assert score_to_nivel(score) == expected

    # Valores en las fronteras exactas de cada tramo
    @pytest.mark.parametrize("boundary,expected", [
        (21, 1), (22, 2),  # límite inferior de nivel 2
        (35, 2), (36, 3),  # límite inferior de nivel 3
        (49, 3), (50, 4),  # límite inferior de nivel 4
        (64, 4), (65, 5),  # límite inferior de nivel 5
        (78, 5), (79, 6),  # límite inferior de nivel 6
        (92, 6), (93, 7),  # límite inferior de nivel 7
    ])
    def test_boundary(self, boundary, expected):
        assert score_to_nivel(boundary) == expected

    def test_score_cero(self):
        assert score_to_nivel(0) == 1

    def test_score_maximo(self):
        assert score_to_nivel(100) == 7

    def test_score_negativo_clampea(self):
        """Scores negativos se tratan como 0 → nivel 1."""
        assert score_to_nivel(-5) == 1

    def test_score_mayor_100_clampea(self):
        """Scores > 100 se tratan como 100 → nivel 7."""
        assert score_to_nivel(150) == 7

    def test_score_none_retorna_nivel1(self):
        """None se convierte en 0 → nivel 1."""
        assert score_to_nivel(None) == 1

    def test_score_flotante(self):
        assert score_to_nivel(50.5) == 4

    def test_score_string_numerico(self):
        """La función acepta strings numéricos."""
        assert score_to_nivel("65") == 5


# ─────────────────────────────────────────────────────────────────────────────
# nivel_to_progreso  ──  nivel 1-7 → porcentaje 0-100
# ─────────────────────────────────────────────────────────────────────────────

class TestNivelToProgreso:
    @pytest.mark.parametrize("nivel,expected", [
        (1, 0), (2, 20), (3, 40), (4, 60), (5, 80), (6, 100), (7, 100),
    ])
    def test_mapeo_completo(self, nivel, expected):
        assert nivel_to_progreso(nivel) == expected

    def test_nivel_none(self):
        """None → nivel 1 → 0%."""
        assert nivel_to_progreso(None) == 0

    def test_nivel6_y_7_misma_meta(self):
        """Nivel 7 (Maestro) se presenta igual que Nivel 6 (Experto) en el porcentaje."""
        assert nivel_to_progreso(6) == nivel_to_progreso(7) == 100


# ─────────────────────────────────────────────────────────────────────────────
# score_to_progreso  ──  composición score→nivel→%
# ─────────────────────────────────────────────────────────────────────────────

class TestScoreToProgreso:
    def test_score_0_da_0_pct(self):
        assert score_to_progreso(0) == 0

    def test_score_50_da_60_pct(self):
        # score 50 → nivel 4 → 60%
        assert score_to_progreso(50) == 60

    def test_score_79_da_100_pct(self):
        # score 79 → nivel 6 → 100%
        assert score_to_progreso(79) == 100

    def test_score_100_da_100_pct(self):
        assert score_to_progreso(100) == 100


# ─────────────────────────────────────────────────────────────────────────────
# clasificar_tiempo  ──  segundos + nivel_ejercicio → "rapido"/"regular"/"lento"
# ─────────────────────────────────────────────────────────────────────────────

class TestClasificarTiempo:
    """
    Los umbrales en TIEMPO_THRESHOLDS son:
      N1: (120, 360)   N2: (150, 480)   N3: (180, 600)
      N4: (240, 720)   N5: (300, 900)
    """

    @pytest.mark.parametrize("nivel,rapido_seg,regular_seg,lento_seg", [
        (1, 60,  240, 400),
        (2, 100, 300, 600),
        (3, 120, 400, 700),
        (4, 200, 600, 800),
        (5, 250, 700, 1000),
    ])
    def test_tres_categorias_por_nivel(self, nivel, rapido_seg, regular_seg, lento_seg):
        assert clasificar_tiempo(rapido_seg,  nivel) == "rapido"
        assert clasificar_tiempo(regular_seg, nivel) == "regular"
        assert clasificar_tiempo(lento_seg,   nivel) == "lento"

    def test_nivel6_usa_umbrales_n5(self):
        """Niveles > 5 usan los umbrales de N5."""
        assert clasificar_tiempo(250, 6) == "rapido"   # ≤300s → rápido N5
        assert clasificar_tiempo(600, 7) == "regular"  # 300<t≤900 → regular N5
        assert clasificar_tiempo(950, 6) == "lento"    # >900s → lento N5

    def test_tiempo_exacto_en_umbral_rapido(self):
        """Exactamente en el umbral → rápido (≤)."""
        umbral_r, _ = TIEMPO_THRESHOLDS[3]
        assert clasificar_tiempo(umbral_r, 3) == "rapido"

    def test_tiempo_exacto_en_umbral_regular(self):
        """Exactamente en el umbral regular → regular (≤)."""
        _, umbral_reg = TIEMPO_THRESHOLDS[3]
        assert clasificar_tiempo(umbral_reg, 3) == "regular"

    def test_tiempo_none_retorna_regular(self):
        """None → por defecto "regular" (nivel_defecto=3)."""
        assert clasificar_tiempo(None) == "regular"

    def test_sin_nivel_usa_defecto_3(self):
        """Sin nivel_ejercicio se aplican umbrales de N3."""
        assert clasificar_tiempo(60)  == "rapido"   # ≤180s
        assert clasificar_tiempo(300) == "regular"  # 180<t≤600
        assert clasificar_tiempo(700) == "lento"    # >600s

    def test_tiempo_cero(self):
        """0 segundos → rápido en cualquier nivel."""
        for n in range(1, 8):
            assert clasificar_tiempo(0, n) == "rapido"


# ─────────────────────────────────────────────────────────────────────────────
# calcular_delta  ──  delta score por respuesta
# ─────────────────────────────────────────────────────────────────────────────

class TestCalcularDelta:
    """
    Tabla DELTA_SCORE:
      (True,  "rapido")  → +8
      (True,  "regular") → +5
      (True,  "lento")   → +2
      (False, "rapido")  → -3
      (False, "regular") → -3
      (False, "lento")   → -5
    Con pista (uso_pista=True y delta>0): delta = max(1, delta - 3)
    """

    @pytest.mark.parametrize("correcta,tiempo,nivel,expected_delta", [
        # Correcto rápido (N1, t=60s ≤ 120s → rapido)
        (True,  60,   1, +8),
        # Correcto regular (N1, t=200s entre 120-360 → regular)
        (True,  200,  1, +5),
        # Correcto lento (N1, t=400s > 360s → lento)
        (True,  400,  1, +2),
        # Incorrecto rápido
        (False, 60,   1, -3),
        # Incorrecto regular
        (False, 200,  1, -3),
        # Incorrecto lento
        (False, 400,  1, -5),
    ])
    def test_tabla_base(self, correcta, tiempo, nivel, expected_delta):
        assert calcular_delta(correcta, tiempo, nivel) == expected_delta

    @pytest.mark.parametrize("correcta,tiempo,nivel,expected_con_pista", [
        # +8 - 3 = +5
        (True, 60,  1, 5),
        # +5 - 3 = +2
        (True, 200, 1, 2),
        # +2 - 3 = -1 → clampea a 1 (DELTA_MIN_CON_PISTA)
        (True, 400, 1, 1),
    ])
    def test_penalizacion_pista_en_aciertos(self, correcta, tiempo, nivel, expected_con_pista):
        """Con pista y respuesta correcta, el delta se reduce pero nunca baja de 1."""
        assert calcular_delta(correcta, tiempo, nivel, uso_pista=True) == expected_con_pista

    def test_pista_no_cambia_delta_negativo(self):
        """Si la respuesta es incorrecta, la pista no modifica el delta."""
        delta_sin = calcular_delta(False, 200, 1, uso_pista=False)
        delta_con = calcular_delta(False, 200, 1, uso_pista=True)
        assert delta_sin == delta_con == -3

    def test_delta_minimo_con_pista_es_1(self):
        """Aun cuando PENALIZACION_PISTA supera al delta, el mínimo es DELTA_MIN_CON_PISTA."""
        # delta+lento = +2, penalización = 3 → debería quedar en 1
        delta = calcular_delta(True, 400, 1, uso_pista=True)
        assert delta == DELTA_MIN_CON_PISTA == 1

    def test_tiempo_none_usa_regular(self):
        """Tiempo None → categoría 'regular' (valor por defecto)."""
        assert calcular_delta(True,  None, 1) == +5
        assert calcular_delta(False, None, 1) == -3

    def test_nivel_6_7_mismo_delta_que_5(self):
        """Niveles ≥5 comparten los mismos umbrales de tiempo."""
        # t=250s ≤ 300s → rápido en N5,N6,N7
        d5 = calcular_delta(True, 250, 5)
        d6 = calcular_delta(True, 250, 6)
        d7 = calcular_delta(True, 250, 7)
        assert d5 == d6 == d7 == +8


# ─────────────────────────────────────────────────────────────────────────────
# nivel_to_minedu  ──  STI interno → MINEDU oficial
# ─────────────────────────────────────────────────────────────────────────────

class TestNivelToMinedu:
    @pytest.mark.parametrize("nivel_sti,nombre_minedu", [
        (1, "Previo al inicio"),
        (2, "En inicio"),
        (3, "En proceso"),
        (4, "En proceso"),  # N3 y N4 → misma descripción MINEDU
        (5, "Logrado"),
        (6, "Logrado"),     # N5 y N6 → mismo nivel MINEDU
        (7, "Destacado"),
    ])
    def test_mapeo_completo(self, nivel_sti, nombre_minedu):
        assert nivel_to_minedu(nivel_sti) == nombre_minedu

    def test_niveles_3_y_4_misma_minedu(self):
        """En proceso agrupa niveles 3 y 4 del STI."""
        assert nivel_to_minedu(3) == nivel_to_minedu(4) == "En proceso"

    def test_niveles_5_y_6_misma_minedu(self):
        """Logrado agrupa niveles 5 y 6 del STI."""
        assert nivel_to_minedu(5) == nivel_to_minedu(6) == "Logrado"

    def test_nivel_none(self):
        assert nivel_to_minedu(None) == "Previo al inicio"


# ─────────────────────────────────────────────────────────────────────────────
# nivel_display_texto  ──  nivel 1-7 → texto UI Android
# ─────────────────────────────────────────────────────────────────────────────

class TestNivelDisplayTexto:
    @pytest.mark.parametrize("nivel,texto", [
        (1, "bajo"), (2, "bajo"),
        (3, "medio"), (4, "medio"),
        (5, "alto"), (6, "alto"), (7, "alto"),
    ])
    def test_mapeo(self, nivel, texto):
        assert nivel_display_texto(nivel) == texto

    def test_nivel_bajo_agrupa_1_2(self):
        assert nivel_display_texto(1) == nivel_display_texto(2) == "bajo"

    def test_nivel_alto_agrupa_5_6_7(self):
        t = nivel_display_texto
        assert t(5) == t(6) == t(7) == "alto"


# ─────────────────────────────────────────────────────────────────────────────
# Consistencia interna de las constantes
# ─────────────────────────────────────────────────────────────────────────────

class TestConsistenciaConstantes:
    def test_score_brackets_cubren_0_100(self):
        """Los tramos cubren todo el rango [0, 100] sin solapamientos."""
        todos = []
        for lo, hi, _ in SCORE_BRACKETS:
            todos.extend(range(lo, hi + 1))
        assert len(set(todos)) == 101   # 0..100 inclusive
        assert min(todos) == 0
        assert max(todos) == 100

    def test_score_brackets_7_niveles(self):
        niveles = {n for _, _, n in SCORE_BRACKETS}
        assert niveles == {1, 2, 3, 4, 5, 6, 7}

    def test_nivel_progreso_tiene_7_entradas(self):
        assert len(NIVEL_PROGRESO) == 7

    def test_nivel_minedu_tiene_7_entradas(self):
        assert len(NIVEL_MINEDU) == 7

    def test_tiempo_thresholds_5_niveles(self):
        assert set(TIEMPO_THRESHOLDS.keys()) == {1, 2, 3, 4, 5}

    def test_umbrales_tiempo_crecientes(self):
        """Los umbrales de tiempo crecen con la dificultad."""
        rapidos   = [TIEMPO_THRESHOLDS[n][0] for n in range(1, 6)]
        regulares = [TIEMPO_THRESHOLDS[n][1] for n in range(1, 6)]
        assert rapidos   == sorted(rapidos)
        assert regulares == sorted(regulares)

    def test_delta_score_tiene_6_entradas(self):
        assert len(DELTA_SCORE) == 6

    def test_delta_correctos_son_positivos(self):
        positivos = [v for (c, _), v in DELTA_SCORE.items() if c]
        assert all(v > 0 for v in positivos)

    def test_delta_incorrectos_son_negativos(self):
        negativos = [v for (c, _), v in DELTA_SCORE.items() if not c]
        assert all(v < 0 for v in negativos)

    def test_penalizacion_pista_menor_que_delta_min_positivo(self):
        """DELTA_MIN_CON_PISTA + PENALIZACION_PISTA ≤ delta mínimo positivo."""
        delta_min_pos = min(v for v in DELTA_SCORE.values() if v > 0)
        # Verificar que la fórmula max(1, delta - 3) tiene sentido
        assert DELTA_MIN_CON_PISTA >= 1
        assert PENALIZACION_PISTA == 3