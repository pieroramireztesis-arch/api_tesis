"""
test_02_caja_blanca_tutor.py — Pruebas de CAJA BLANCA: ws/tutor.py (funciones internas)
=========================================================================================
Tipo  : Componente (funciones con cursor mock, sin HTTP)
Módulo: API_COMERCIAL/ws/tutor.py

Cobertura
─────────
• detectar_racha()                → positiva / negativa / None / sin datos
• leer_nec()                      → alumno con NEC / alumno nuevo (INSERT)
• guardar_nec()                   → llamada correcta al cursor
• actualizar_progreso_estudiante() → cálculo del promedio de 4 competencias
• calcular_features_competencia()  → con datos / sin datos / total=0
• predecir_nivel_competencia()     → sin modelo ML / con modelo ML simulado
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch

# Importar las funciones internas del módulo tutor
from ws.tutor import (
    detectar_racha,
    leer_nec,
    guardar_nec,
    actualizar_progreso_estudiante,
    calcular_features_competencia,
    predecir_nivel_competencia,
    UMBRAL_APROBADO,
)
from models.scoring import score_to_nivel

pytestmark = pytest.mark.component


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: cursor limpio por test
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def cur(mock_cursor):
    return mock_cursor


# ─────────────────────────────────────────────────────────────────────────────
# detectar_racha
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectarRacha:

    def test_racha_positiva_3_correctas(self, cur):
        """Últimas 3 respuestas todas correctas → 'positiva'."""
        cur.fetchall.return_value = [
            {'es_correcta': True},
            {'es_correcta': True},
            {'es_correcta': True},
        ]
        assert detectar_racha(cur, id_estudiante=1, id_competencia=2) == 'positiva'

    def test_racha_negativa_3_incorrectas(self, cur):
        """Últimas 3 respuestas todas incorrectas → 'negativa'."""
        cur.fetchall.return_value = [
            {'es_correcta': False},
            {'es_correcta': False},
            {'es_correcta': False},
        ]
        assert detectar_racha(cur, id_estudiante=1, id_competencia=2) == 'negativa'

    def test_racha_mixta_retorna_none(self, cur):
        """Respuestas mixtas (correcto + incorrecto) → None."""
        cur.fetchall.return_value = [
            {'es_correcta': True},
            {'es_correcta': False},
            {'es_correcta': True},
        ]
        assert detectar_racha(cur, id_estudiante=1, id_competencia=2) is None

    def test_menos_de_n_respuestas_retorna_none(self, cur):
        """Menos de 3 respuestas → sin racha → None."""
        cur.fetchall.return_value = [
            {'es_correcta': True},
            {'es_correcta': True},
        ]
        assert detectar_racha(cur, id_estudiante=1, id_competencia=2) is None

    def test_sin_respuestas_retorna_none(self, cur):
        """Sin respuestas → None."""
        cur.fetchall.return_value = []
        assert detectar_racha(cur, id_estudiante=1, id_competencia=2) is None

    def test_n_personalizado_5(self, cur):
        """Con n=5, necesita exactamente 5 consecutivas para detectar racha."""
        cur.fetchall.return_value = [{'es_correcta': True}] * 5
        assert detectar_racha(cur, 1, 2, n=5) == 'positiva'
        cur.fetchall.return_value = [{'es_correcta': True}] * 4
        assert detectar_racha(cur, 1, 2, n=5) is None


# ─────────────────────────────────────────────────────────────────────────────
# leer_nec
# ─────────────────────────────────────────────────────────────────────────────

class TestLeerNec:

    def test_alumno_con_nec_existente(self, cur):
        """Alumno con registro NEC → retorna nivel y score directamente."""
        cur.fetchone.return_value = {'nivel_actual': 4, 'score': 55.0}
        nivel, score = leer_nec(cur, id_estudiante=10, id_competencia=1)
        assert nivel == 4
        assert score == 55.0

    def test_alumno_nuevo_sin_puntajes(self, cur):
        """Alumno nuevo sin NEC ni puntajes → nivel=1, score=0."""
        # Primera llamada (NEC) → None; Segunda (puntajes) → None
        cur.fetchone.side_effect = [None, None]
        nivel, score = leer_nec(cur, id_estudiante=99, id_competencia=1)
        assert nivel == 1
        assert score == 0.0

    def test_alumno_nuevo_con_puntajes(self, cur):
        """Alumno nuevo sin NEC pero con puntajes → nivel calculado desde avg."""
        # puntaje promedio 50 → nivel 4
        cur.fetchone.side_effect = [None, {'avg_p': 50.0}]
        nivel, score = leer_nec(cur, id_estudiante=99, id_competencia=2)
        assert nivel == score_to_nivel(50.0)
        assert score == 50.0

    def test_nivel_actual_none_en_bd(self, cur):
        """Si nivel_actual en BD es NULL → coerce a 1."""
        cur.fetchone.return_value = {'nivel_actual': None, 'score': 0.0}
        nivel, score = leer_nec(cur, id_estudiante=10, id_competencia=3)
        assert nivel == 1

    def test_nec_nivel_7(self, cur):
        """Nivel máximo (7) retorna correctamente."""
        cur.fetchone.return_value = {'nivel_actual': 7, 'score': 95.0}
        nivel, score = leer_nec(cur, 10, 1)
        assert nivel == 7
        assert score == 95.0


# ─────────────────────────────────────────────────────────────────────────────
# guardar_nec
# ─────────────────────────────────────────────────────────────────────────────

class TestGuardarNec:

    def test_llama_execute_con_parametros_correctos(self, cur):
        guardar_nec(cur, id_estudiante=10, id_competencia=2,
                    nuevo_score=65.0, nuevo_nivel=5)
        cur.execute.assert_called_once()
        call_args = cur.execute.call_args[0]
        # Verifica que los parámetros incluyan los valores correctos
        assert (10, 2, 5, 65.0) == call_args[1]


# ─────────────────────────────────────────────────────────────────────────────
# actualizar_progreso_estudiante
# ─────────────────────────────────────────────────────────────────────────────

class TestActualizarProgresoEstudiante:

    def test_4_competencias_promedio_correcto(self, cur):
        """
        Nivel 1→0%, 2→20%, 3→40%, 4→60%
        Promedio = (0+20+40+60)/4 = 30% → progreso_general=30
        """
        cur.fetchall.return_value = [
            {'nivel_actual': 1, 'id_competencia': 1},
            {'nivel_actual': 2, 'id_competencia': 2},
            {'nivel_actual': 3, 'id_competencia': 3},
            {'nivel_actual': 4, 'id_competencia': 4},
        ]
        actualizar_progreso_estudiante(cur, id_estudiante=10)
        # Verificar que se llamó UPDATE con progreso=30
        update_call = cur.execute.call_args_list[-1]
        assert update_call[0][1] == (30, 10)

    def test_todos_nivel_6_da_100_pct(self, cur):
        cur.fetchall.return_value = [{'nivel_actual': 6, 'id_competencia': i}
                                     for i in range(1, 5)]
        actualizar_progreso_estudiante(cur, id_estudiante=10)
        update_call = cur.execute.call_args_list[-1]
        assert update_call[0][1] == (100, 10)

    def test_sin_competencias_no_actualiza(self, cur):
        """Sin competencias NEC no debe llamar UPDATE."""
        cur.fetchall.return_value = []
        actualizar_progreso_estudiante(cur, id_estudiante=10)
        # execute solo fue llamado para el SELECT, no para UPDATE
        selects_sin_update = [
            c for c in cur.execute.call_args_list
            if 'UPDATE' not in str(c)
        ]
        assert len(cur.execute.call_args_list) == 1  # solo el SELECT


# ─────────────────────────────────────────────────────────────────────────────
# calcular_features_competencia
# ─────────────────────────────────────────────────────────────────────────────

class TestCalcularFeaturesCompetencia:

    def test_sin_datos_retorna_none(self, cur):
        """Sin puntajes → total=0 → retorna None (sin features)."""
        cur.fetchone.return_value = {
            'total_intentos': 0, 'promedio_puntaje': None,
            'min_puntaje': None, 'max_puntaje': None,
            'std_puntaje': 0, 'num_aprobados': 0, 'tendencia': None,
        }
        result = calcular_features_competencia(cur, 10, 1)
        assert result is None

    def test_con_datos_retorna_array_7_features(self, cur):
        """Con datos válidos retorna np.array de shape (1, 7)."""
        cur.fetchone.return_value = {
            'total_intentos': 10,
            'promedio_puntaje': 70.0,
            'min_puntaje': 40.0,
            'max_puntaje': 100.0,
            'std_puntaje': 15.0,
            'num_aprobados': 7,
            'tendencia': 0.5,
        }
        result = calcular_features_competencia(cur, 10, 1)
        assert result is not None
        assert result.shape == (1, 7)

    def test_features_en_rango_valido(self, cur):
        """Los features clampean a [0,100] para promedio, min y max."""
        cur.fetchone.return_value = {
            'total_intentos': 5,
            'promedio_puntaje': 120.0,  # fuera de rango
            'min_puntaje': -10.0,        # fuera de rango
            'max_puntaje': 200.0,        # fuera de rango
            'std_puntaje': 5.0,
            'num_aprobados': 5,
            'tendencia': 1.5,           # fuera de [-1,1]
        }
        result = calcular_features_competencia(cur, 10, 1)
        assert result is not None
        # promedio clampea a 100
        assert result[0][1] == 100.0
        # min clampea a 0
        assert result[0][2] == 0.0
        # max clampea a 100
        assert result[0][3] == 100.0
        # tendencia clampea a 1.0
        assert result[0][6] == 1.0

    def test_tasa_aprobados_calculo(self, cur):
        """tasa = num_aprobados / total_intentos."""
        cur.fetchone.return_value = {
            'total_intentos': 10,
            'promedio_puntaje': 65.0,
            'min_puntaje': 40.0,
            'max_puntaje': 100.0,
            'std_puntaje': 10.0,
            'num_aprobados': 6,
            'tendencia': 0.3,
        }
        result = calcular_features_competencia(cur, 10, 1)
        tasa = result[0][5]
        assert abs(tasa - 0.6) < 1e-6  # 6/10

    def test_fetchone_none_retorna_none(self, cur):
        """Si la BD no devuelve fila → None."""
        cur.fetchone.return_value = None
        result = calcular_features_competencia(cur, 10, 1)
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# predecir_nivel_competencia  (sin/con ML)
# ─────────────────────────────────────────────────────────────────────────────

class TestPredecirNivelCompetencia:

    def test_sin_modelo_retorna_nivel_base(self, cur):
        """Sin modelo ML, retorna directamente el nivel_display del NEC."""
        # NEC nivel 3 → "medio"
        cur.fetchone.return_value = {'nivel_actual': 3, 'score': 42.0}
        # Parchear MODELO_TUTOR a None
        import ws.tutor as tutor_mod
        orig = tutor_mod.MODELO_TUTOR
        tutor_mod.MODELO_TUTOR = None
        try:
            resultado = predecir_nivel_competencia(cur, 10, 1)
        finally:
            tutor_mod.MODELO_TUTOR = orig
        assert resultado == 'medio'

    def test_con_modelo_ajusta_nivel(self, cur):
        """Con ML que predice 'alto' sobre base 'medio' → resultado 'alto'."""
        # NEC nivel 4 → base 'medio'
        cur.fetchone.side_effect = [
            {'nivel_actual': 4, 'score': 55.0},   # leer_nec
            # features call → fetchone para estadísticas
            {
                'total_intentos': 10, 'promedio_puntaje': 80.0,
                'min_puntaje': 60.0,  'max_puntaje': 100.0,
                'std_puntaje': 10.0,  'num_aprobados': 9,
                'tendencia': 0.8,
            },
        ]
        mock_modelo  = MagicMock()
        mock_encoder = MagicMock()
        mock_modelo.predict.return_value    = [1]     # encoded 'alto'
        mock_encoder.inverse_transform.return_value = ['alto']

        import ws.tutor as tutor_mod
        orig_m, orig_e = tutor_mod.MODELO_TUTOR, tutor_mod.ENCODER_NIVEL
        tutor_mod.MODELO_TUTOR  = mock_modelo
        tutor_mod.ENCODER_NIVEL = mock_encoder
        try:
            resultado = predecir_nivel_competencia(cur, 10, 1)
        finally:
            tutor_mod.MODELO_TUTOR  = orig_m
            tutor_mod.ENCODER_NIVEL = orig_e

        # base=medio(1), ml=alto(2): acotado a min(2, 1+1)=2 → 'alto'
        assert resultado == 'alto'

    def test_ml_no_puede_saltar_2_niveles(self, cur):
        """El ML acota el resultado: no puede subir más de +1 sobre el NEC base."""
        # NEC nivel 1 → base 'bajo' (idx=0)
        # ML predice 'alto' (idx=2) → acotado a min(2, 0+1)=1 → 'medio'
        cur.fetchone.side_effect = [
            {'nivel_actual': 1, 'score': 10.0},
            {
                'total_intentos': 5, 'promedio_puntaje': 90.0,
                'min_puntaje': 80.0, 'max_puntaje': 100.0,
                'std_puntaje': 5.0,  'num_aprobados': 5,
                'tendencia': 0.9,
            },
        ]
        mock_modelo  = MagicMock()
        mock_encoder = MagicMock()
        mock_modelo.predict.return_value    = [1]
        mock_encoder.inverse_transform.return_value = ['alto']

        import ws.tutor as tutor_mod
        orig_m, orig_e = tutor_mod.MODELO_TUTOR, tutor_mod.ENCODER_NIVEL
        tutor_mod.MODELO_TUTOR  = mock_modelo
        tutor_mod.ENCODER_NIVEL = mock_encoder
        try:
            resultado = predecir_nivel_competencia(cur, 10, 1)
        finally:
            tutor_mod.MODELO_TUTOR  = orig_m
            tutor_mod.ENCODER_NIVEL = orig_e

        # base=bajo(0), ml_idx acotado a min(2, 0+1)=1 → 'medio'
        assert resultado == 'medio'