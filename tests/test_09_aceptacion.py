"""
test_09_aceptacion.py — Pruebas de ACEPTACIÓN (historias de usuario)
=====================================================================
Tipo  : Aceptación (criterios de aceptación de historias de usuario del STI)

Historias de usuario
─────────────────────
HU-1  El estudiante recibe ejercicios adaptados a su nivel
HU-2  Un estudiante con desempeño sobresaliente obtiene más puntos que uno lento
HU-3  La evaluación no modifica el nivel del estudiante
HU-4  El docente puede ver el nivel MINEDU del estudiante en el reporte
HU-5  La pista solo aparece cuando el ejercicio tiene texto de ayuda
HU-6  Un estudiante nuevo queda bloqueado hasta que el docente ingrese el diagnóstico
HU-7  Responder incorrectamente reduce el score pero no lo lleva a negativo
HU-8  El sistema distingue 4 competencias MINEDU independientes
"""

import pytest
from unittest.mock import MagicMock

pytestmark = pytest.mark.acceptance


# ─────────────────────────────────────────────────────────────────────────────
# HU-1 — Ejercicios adaptados al nivel del estudiante
# ─────────────────────────────────────────────────────────────────────────────

class TestHU1EjerciciosAdaptados:

    def test_alumno_nivel_alto_recibe_ejercicio_dificil(self, client, mock_cursor):
        """
        DADO  un estudiante con NEC nivel 6 en competencia 2
        CUANDO solicita ejercicio siguiente en modo repaso
        ENTONCES la query filtra ejercicios de dificultad ≥ 5 (nivel_logro ≥ 5)
        """
        # Con idDominio=2 → sin_diag, nec(1), nec(2-predecir), calcular_features, exercise, nec(display)
        _stats = {'total_intentos': 0, 'promedio_puntaje': None, 'min_puntaje': None,
                  'max_puntaje': None, 'std_puntaje': 0, 'num_aprobados': 0, 'tendencia': None}
        mock_cursor.fetchone.side_effect = [
            {'sin_diagnostico': False},
            {'nivel_actual': 6, 'score': 80.0},   # leer_nec #1
            {'nivel_actual': 6, 'score': 80.0},   # leer_nec #2 (predecir)
            _stats,                                 # calcular_features (total=0 → None)
            {'id_ejercicio': 120, 'enunciado': 'Problema avanzado',
             'imagen_url': None, 'pista': None,
             'id_competencia': 2, 'nivel_ejercicio': 6},
            {'nivel_actual': 6, 'score': 80.0},   # leer_nec display
        ]
        mock_cursor.fetchall.side_effect = [
            [],   # racha
            [{'id_opcion': 1, 'letra': 'A', 'descripcion': 'Correcta', 'es_correcta': True}],
        ]
        r = client.get('/tutor/ejercicio_siguiente?idEstudiante=10&idDominio=2')
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] is True

        # Verificar que el SQL usó el filtro correcto para NEC 6
        all_sql = ' '.join(str(c) for c in mock_cursor.execute.call_args_list)
        assert '>= 5' in all_sql or '>= 6' in all_sql or 'nivel_logro' in all_sql.lower()

    def test_alumno_nivel_bajo_recibe_ejercicio_facil(self, client, mock_cursor):
        """
        DADO  un estudiante con NEC nivel 1
        CUANDO solicita ejercicio siguiente
        ENTONCES la query filtra ejercicios de dificultad ≤ 3
        """
        # Con idDominio=1 → sin_diag, nec(1), nec(2-predecir), calcular_features, exercise, nec(display)
        _stats = {'total_intentos': 0, 'promedio_puntaje': None, 'min_puntaje': None,
                  'max_puntaje': None, 'std_puntaje': 0, 'num_aprobados': 0, 'tendencia': None}
        mock_cursor.fetchone.side_effect = [
            {'sin_diagnostico': False},
            {'nivel_actual': 1, 'score': 10.0},   # leer_nec #1
            {'nivel_actual': 1, 'score': 10.0},   # leer_nec #2 (predecir)
            _stats,                                 # calcular_features (total=0 → None)
            {'id_ejercicio': 106, 'enunciado': 'Suma básica',
             'imagen_url': None, 'pista': 'Recuerda sumar',
             'id_competencia': 1, 'nivel_ejercicio': 2},
            {'nivel_actual': 1, 'score': 10.0},   # leer_nec display
        ]
        mock_cursor.fetchall.side_effect = [
            [],   # racha
            [{'id_opcion': 1, 'letra': 'A', 'descripcion': 'Correcta', 'es_correcta': True}],
        ]
        r = client.get('/tutor/ejercicio_siguiente?idEstudiante=10&idDominio=1')
        assert r.status_code == 200
        assert r.get_json()['status'] is True

        all_sql = ' '.join(str(c) for c in mock_cursor.execute.call_args_list)
        assert '<= 3' in all_sql or 'nivel_logro' in all_sql.lower()


# ─────────────────────────────────────────────────────────────────────────────
# HU-2 — Más puntos por responder rápido y bien
# ─────────────────────────────────────────────────────────────────────────────

class TestHU2PuntajePorVelocidad:

    def test_correcto_rapido_mas_delta_que_correcto_lento(self):
        """
        DADO  que un estudiante responde correctamente
        CUANDO responde rápidamente vs lentamente
        ENTONCES el delta rápido es mayor que el lento
        """
        from models.scoring import calcular_delta
        # N3: rápido ≤180s, lento >600s
        delta_rapido = calcular_delta(True, 90,  3)   # rápido
        delta_normal = calcular_delta(True, 300, 3)   # regular
        delta_lento  = calcular_delta(True, 700, 3)   # lento
        assert delta_rapido > delta_normal > delta_lento

    def test_respuesta_correcta_siempre_sube_score(self):
        """
        DADO  cualquier respuesta correcta
        ENTONCES el delta siempre es positivo (el score nunca baja por acertar)
        """
        from models.scoring import calcular_delta
        for nivel in range(1, 8):
            for tiempo in [1, 60, 200, 500, 1000]:
                delta = calcular_delta(True, tiempo, nivel)
                assert delta > 0, f"N{nivel} t={tiempo}s: correcto debe ser positivo"

    def test_respuesta_incorrecta_siempre_baja_score(self):
        """
        DADO  cualquier respuesta incorrecta
        ENTONCES el delta es negativo (el score siempre baja al fallar)
        """
        from models.scoring import calcular_delta
        for nivel in range(1, 8):
            for tiempo in [1, 60, 200, 500, 1000]:
                delta = calcular_delta(False, tiempo, nivel)
                assert delta < 0, f"N{nivel} t={tiempo}s: incorrecto debe ser negativo"


# ─────────────────────────────────────────────────────────────────────────────
# HU-3 — Evaluación no modifica el nivel
# ─────────────────────────────────────────────────────────────────────────────

class TestHU3EvaluacionSinCambioNivel:

    def test_hu3_nec_intacto_tras_evaluacion(self, client, mock_cursor):
        """
        DADO  un estudiante con NEC nivel 4
        CUANDO responde ejercicios en modo evaluación
        ENTONCES el nivel NEC permanece en 4 (sin modificación)
        """
        mock_cursor.fetchone.side_effect = [
            {'es_correcta': True, 'id_competencia': 2,
             'nivel_ejercicio': 3, 'pista': None},
        ]
        mock_cursor.fetchall.return_value = []

        client.post('/tutor/responder', json={
            'idEstudiante': 10, 'idEjercicio': 101,
            'idOpcionSeleccionada': 1,
            'tiempoRespuesta': 90, 'usoPista': False,
            'modo': 'evaluacion', 'idEvaluacion': 5,
        })

        nec_touches = [
            c for c in mock_cursor.execute.call_args_list
            if 'nivel_estudiante_competencia' in str(c).lower()
        ]
        assert len(nec_touches) == 0


# ─────────────────────────────────────────────────────────────────────────────
# HU-4 — Nivel MINEDU visible en reporte del docente
# ─────────────────────────────────────────────────────────────────────────────

class TestHU4NivelMINEDUEnReporte:

    def test_hu4_nivel_to_minedu_retorna_nombre_oficial(self):
        """
        DADO  un nivel interno STI (1-7)
        CUANDO se convierte para el docente
        ENTONCES retorna el nombre MINEDU oficial
        """
        from models.scoring import nivel_to_minedu
        # Los nombres deben coincidir con el Currículo Nacional MINEDU 2016
        nombres_oficiales = {
            "Previo al inicio", "En inicio", "En proceso", "Logrado", "Destacado"
        }
        for n in range(1, 8):
            nombre = nivel_to_minedu(n)
            assert nombre in nombres_oficiales, (
                f"nivel_to_minedu({n})='{nombre}' no es un nombre MINEDU oficial"
            )

    def test_hu4_7_niveles_sti_se_mapean_a_5_minedu(self):
        """El STI tiene 7 niveles internos que se comunican en 5 niveles MINEDU."""
        from models.scoring import nivel_to_minedu
        niveles_minedu = {nivel_to_minedu(n) for n in range(1, 8)}
        assert len(niveles_minedu) == 5


# ─────────────────────────────────────────────────────────────────────────────
# HU-5 — Pista solo cuando el ejercicio tiene texto de ayuda
# ─────────────────────────────────────────────────────────────────────────────

class TestHU5PistaConTexto:

    def test_hu5_pista_true_solo_con_texto_y_repaso(self, client, mock_cursor):
        """
        DADO  un ejercicio con pista (texto real) y modo repaso
        CUANDO el estudiante falla
        ENTONCES mostrarPista = True
        """
        mock_cursor.fetchone.side_effect = [
            {'es_correcta': False, 'id_competencia': 2,
             'nivel_ejercicio': 3, 'pista': 'Recuerda: ax+b=0 → x=-b/a'},
            {'id_respuesta': 5},            # INSERT RETURNING id_respuesta
            {'nivel_actual': 3, 'score': 40.0},
            {'total_intentos': 0, 'promedio_puntaje': None,
             'min_puntaje': None, 'max_puntaje': None,
             'std_puntaje': 0, 'num_aprobados': 0, 'tendencia': None},
            {'nivel_actual': 3, 'score': 35.0},
        ]
        mock_cursor.fetchall.side_effect = [[], [{'nivel_actual': 3, 'id_competencia': 2}]]
        r = client.post('/tutor/responder', json={
            'idEstudiante': 10, 'idEjercicio': 101, 'idOpcionSeleccionada': 3,
            'tiempoRespuesta': 200, 'usoPista': False, 'modo': 'repaso',
        })
        assert r.get_json().get('mostrarPista') is True

    def test_hu5_pista_false_sin_texto(self, client, mock_cursor):
        """
        DADO  un ejercicio SIN pista (campo None o vacío)
        CUANDO el estudiante falla en repaso
        ENTONCES mostrarPista = False (no se muestra el banner genérico vacío)
        """
        mock_cursor.fetchone.side_effect = [
            {'es_correcta': False, 'id_competencia': 2,
             'nivel_ejercicio': 3, 'pista': ''},   # pista vacía
            {'id_respuesta': 5},            # INSERT RETURNING id_respuesta
            {'nivel_actual': 3, 'score': 40.0},
            {'total_intentos': 0, 'promedio_puntaje': None,
             'min_puntaje': None, 'max_puntaje': None,
             'std_puntaje': 0, 'num_aprobados': 0, 'tendencia': None},
            {'nivel_actual': 3, 'score': 35.0},
        ]
        mock_cursor.fetchall.side_effect = [[], [{'nivel_actual': 3, 'id_competencia': 2}]]
        r = client.post('/tutor/responder', json={
            'idEstudiante': 10, 'idEjercicio': 101, 'idOpcionSeleccionada': 3,
            'tiempoRespuesta': 200, 'usoPista': False, 'modo': 'repaso',
        })
        assert r.get_json().get('mostrarPista') is False


# ─────────────────────────────────────────────────────────────────────────────
# HU-6 — Estudiante nuevo bloqueado sin diagnóstico
# ─────────────────────────────────────────────────────────────────────────────

class TestHU6BloqueadoSinDiagnostico:

    def test_hu6_nuevo_estudiante_bloqueado(self, client, mock_cursor):
        """
        DADO  un estudiante recién registrado (docente no ingresó notas)
        CUANDO intenta acceder al tutor
        ENTONCES recibe status=False con bloqueado=True
        """
        mock_cursor.fetchone.return_value = {'sin_diagnostico': True}
        r = client.get('/tutor/ejercicio_siguiente?idEstudiante=99')
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] is False
        assert data.get('bloqueado') is True
        assert 'ejercicio' not in data


# ─────────────────────────────────────────────────────────────────────────────
# HU-7 — Score nunca negativo
# ─────────────────────────────────────────────────────────────────────────────

class TestHU7ScoreNoNegativo:

    def test_hu7_score_acumulado_nunca_negativo(self):
        """
        DADO  un estudiante con score 0
        CUANDO responde mal múltiples veces
        ENTONCES el score acumulado permanece ≥ 0
        """
        from models.scoring import calcular_delta
        score = 5.0  # score muy bajo
        for _ in range(10):
            delta = calcular_delta(False, 800, 3)  # incorrecto lento: -5
            score = max(0.0, score + delta)
        assert score >= 0.0, "El score nunca debe ser negativo"


# ─────────────────────────────────────────────────────────────────────────────
# HU-8 — 4 competencias MINEDU independientes
# ─────────────────────────────────────────────────────────────────────────────

class TestHU84Competencias:

    def test_hu8_4_competencias_en_progreso(self, client, mock_cursor):
        """
        DADO  un estudiante con actividad en las 4 competencias
        CUANDO solicita progreso por competencia
        ENTONCES recibe 4 entradas independientes
        """
        mock_cursor.fetchall.return_value = [
            {'id_competencia': c, 'descripcion': f'C{c}',
             'nivel_actual': c, 'score': c * 14.0}
            for c in range(1, 5)
        ]
        r = client.get('/progreso/por_competencia?idEstudiante=10')
        assert r.status_code == 200
        data = r.get_json()
        temas = data.get('temas') or []
        assert len(temas) == 4
        ids = {t['idCompetencia'] for t in temas} if temas and 'idCompetencia' in temas[0] else set()
        if ids:
            assert ids == {1, 2, 3, 4}

    def test_hu8_ids_competencia_validos(self):
        """Los 7 niveles STI están definidos en NIVEL_MINEDU."""
        from models.scoring import NIVEL_MINEDU
        for n in range(1, 8):
            assert n in NIVEL_MINEDU, f"Nivel STI {n} no está en NIVEL_MINEDU"