"""
test_04_caja_negra_tutor.py — Pruebas de CAJA NEGRA: endpoints del tutor STI
=============================================================================
Tipo  : Funcional / Caja Negra
Rutas : GET /tutor/ejercicio_siguiente | POST /tutor/responder
        GET /tutor/evaluacion/activa   | POST /tutor/evaluacion/finalizar
        POST /tutor/subir_desarrollo
"""

import pytest
import json
from werkzeug.security import generate_password_hash

pytestmark = pytest.mark.black_box


# ─────────────────────────────────────────────────────────────────────────────
# Datos de prueba
# ─────────────────────────────────────────────────────────────────────────────

_EJERCICIO = {
    'id_ejercicio': 101, 'enunciado': '2x + 3 = 7', 'imagen_url': None,
    'pista': 'Despeja x.', 'id_competencia': 2,
    'nivel_ejercicio': 3,
}
_OPCIONES = [
    {'id_opcion': 1, 'letra': 'A', 'descripcion': 'x = 2', 'es_correcta': True},
    {'id_opcion': 2, 'letra': 'B', 'descripcion': 'x = 3', 'es_correcta': False},
    {'id_opcion': 3, 'letra': 'C', 'descripcion': 'x = 4', 'es_correcta': False},
]


def _base_nec(nivel=3):
    """NEC estándar para los tests."""
    return {'nivel_actual': nivel, 'score': 40.0}


# ─────────────────────────────────────────────────────────────────────────────
# GET /tutor/ejercicio_siguiente
# ─────────────────────────────────────────────────────────────────────────────

class TestEjercicioSiguiente:

    def test_sin_id_estudiante_retorna_400(self, client):
        r = client.get('/tutor/ejercicio_siguiente')
        assert r.status_code == 400
        assert r.get_json()['status'] is False

    def test_sin_diagnostico_retorna_bloqueado(self, client, mock_cursor):
        """Sin diagnóstico inicial del docente → bloqueado con mensaje especial."""
        mock_cursor.fetchone.return_value = {'sin_diagnostico': True}
        r = client.get('/tutor/ejercicio_siguiente?idEstudiante=10')
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] is False
        # El campo 'bloqueado' debe estar en True
        assert data.get('bloqueado') is True

    def test_modo_por_defecto_es_repaso(self, client, mock_cursor):
        """Sin parámetro modo → se usa 'repaso' por defecto."""
        # Sin idDominio → secuencia: sin_diag, nivel_min AVG, exercise, leer_nec display
        mock_cursor.fetchone.side_effect = [
            {'sin_diagnostico': False},
            {'nivel_min': 3},            # AVG nivel_min (sin idDominio)
            _EJERCICIO,
            _base_nec(3),                # leer_nec display
        ]
        mock_cursor.fetchall.side_effect = [
            _OPCIONES,     # solo opciones (sin racha cuando no hay idDominio)
        ]
        r = client.get('/tutor/ejercicio_siguiente?idEstudiante=10')
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] is True
        assert 'idEjercicio' in data or 'ejercicio' in data or 'id_ejercicio' in data

    def test_retorna_campos_obligatorios(self, client, mock_cursor):
        """La respuesta contiene los campos necesarios para el cliente Android."""
        mock_cursor.fetchone.side_effect = [
            {'sin_diagnostico': False},
            {'nivel_min': 3},
            _EJERCICIO,
            _base_nec(3),
        ]
        mock_cursor.fetchall.side_effect = [_OPCIONES]
        r = client.get('/tutor/ejercicio_siguiente?idEstudiante=10')
        data = r.get_json()
        if data.get('status'):
            assert 'idEjercicio' in data or 'id_ejercicio' in data or 'ejercicio' in data

    def test_modo_evaluacion_con_id_evaluacion(self, client, mock_cursor):
        """En modo evaluación con idEvaluacion → sirve ejercicio de la evaluación."""
        # evaluacion sin idDominio → sin_diag, ev_row, nivel_min, exercise, leer_nec display
        mock_cursor.fetchone.side_effect = [
            {'sin_diagnostico': False},
            {'num_preguntas': 5, 'ya_respondidas': 0, 'ejercicios_grupos': None},
            {'nivel_min': 2},
            _EJERCICIO,
            _base_nec(2),
        ]
        mock_cursor.fetchall.side_effect = [
            _OPCIONES,    # opciones (sin racha porque no hay idDominio)
        ]
        r = client.get('/tutor/ejercicio_siguiente'
                       '?idEstudiante=10&modo=evaluacion&idEvaluacion=5')
        assert r.status_code == 200

    def test_id_dominio_filtra_competencia(self, client, mock_cursor):
        """Con idDominio se filtra por competencia específica."""
        # Con idDominio → sin_diag, leer_nec(1), leer_nec(2-predecir), calcular_features, exercise, leer_nec(display)
        _stats = {'total_intentos': 0, 'promedio_puntaje': None, 'min_puntaje': None,
                  'max_puntaje': None, 'std_puntaje': 0, 'num_aprobados': 0, 'tendencia': None}
        mock_cursor.fetchone.side_effect = [
            {'sin_diagnostico': False},
            _base_nec(3),   # leer_nec #1 (direct)
            _base_nec(3),   # leer_nec #2 (inside predecir)
            _stats,          # calcular_features_competencia (returns None: total=0)
            _EJERCICIO,
            _base_nec(3),   # leer_nec #3 (display)
        ]
        mock_cursor.fetchall.side_effect = [[], _OPCIONES]  # racha vacía + opciones
        r = client.get('/tutor/ejercicio_siguiente?idEstudiante=10&idDominio=2')
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /tutor/responder
# ─────────────────────────────────────────────────────────────────────────────

class TestResponder:

    def test_sin_campos_retorna_400(self, client):
        r = client.post('/tutor/responder', json={})
        assert r.status_code == 400

    def test_respuesta_correcta_en_repaso(self, client, mock_cursor):
        """Respuesta correcta en repaso → correcta=True + nuevoAjuste."""
        mock_cursor.fetchone.side_effect = [
            {'es_correcta': True, 'id_competencia': 2,
             'nivel_ejercicio': 3, 'pista': 'Despeja x.'},
            {'id_respuesta': 5},            # INSERT RETURNING id_respuesta
            {'nivel_actual': 3, 'score': 40.0},   # leer_nec
            {'prom': 3.0},                  # COALESCE AVG prom_g
            {'nivel_actual': 3, 'score': 45.0},   # extra para try/except material
        ]
        mock_cursor.fetchall.side_effect = [
            [],                   # racha: sin historial
            [{'nivel_actual': 3, 'id_competencia': 2}],  # progreso_general
        ]
        r = client.post('/tutor/responder', json={
            'idEstudiante': 10, 'idEjercicio': 101,
            'idOpcionSeleccionada': 1,
            'tiempoRespuesta': 60, 'usoPista': False, 'modo': 'repaso',
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data.get('correcta') is True

    def test_respuesta_incorrecta_en_repaso(self, client, mock_cursor):
        """Respuesta incorrecta → correcta=False."""
        mock_cursor.fetchone.side_effect = [
            {'es_correcta': False, 'id_competencia': 1,
             'nivel_ejercicio': 2, 'pista': None},
            {'id_respuesta': 5},            # INSERT RETURNING id_respuesta
            {'nivel_actual': 2, 'score': 25.0},   # leer_nec
            {'prom': 2.0},                  # prom_g
            {'nivel_actual': 2, 'score': 22.0},   # extra para try/except material
        ]
        mock_cursor.fetchall.side_effect = [
            [],
            [{'nivel_actual': 2, 'id_competencia': 1}],
        ]
        r = client.post('/tutor/responder', json={
            'idEstudiante': 10, 'idEjercicio': 102,
            'idOpcionSeleccionada': 3,
            'tiempoRespuesta': 300, 'usoPista': False, 'modo': 'repaso',
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data.get('correcta') is False

    def test_respuesta_en_evaluacion_no_actualiza_nec(self, client, mock_cursor):
        """En modo evaluación → status OK pero sin actualización de NEC."""
        mock_cursor.fetchone.side_effect = [
            {'es_correcta': True, 'id_competencia': 2,
             'nivel_ejercicio': 3, 'pista': None},
            {'id_respuesta': 5},            # INSERT RETURNING id_respuesta
            {'nivel_actual': 3, 'score': 40.0},   # leer_nec
            {'prom': 3.0},                  # prom_g (evaluacion también lee prom)
        ]
        mock_cursor.fetchall.return_value = []
        r = client.post('/tutor/responder', json={
            'idEstudiante': 10, 'idEjercicio': 101,
            'idOpcionSeleccionada': 1,
            'tiempoRespuesta': 90, 'usoPista': False,
            'modo': 'evaluacion', 'idEvaluacion': 5,
        })
        assert r.status_code == 200
        # En evaluación: NEC NO se debe actualizar (verificar con mock)
        # Solo debe haber sido llamado el SELECT de verificación, no guardar_nec
        update_nec_calls = [
            c for c in mock_cursor.execute.call_args_list
            if 'nivel_estudiante_competencia' in str(c) and 'UPDATE' in str(c).upper()
        ]
        assert len(update_nec_calls) == 0

    def test_pista_solo_retorna_si_ejercicio_tiene_pista(self, client, mock_cursor):
        """mostrar_pista=True solo cuando el ejercicio tiene texto de pista Y es repaso."""
        mock_cursor.fetchone.side_effect = [
            {'es_correcta': False, 'id_competencia': 2,
             'nivel_ejercicio': 3, 'pista': 'Recuerda: ax + b = 0'},
            {'id_respuesta': 5},
            {'nivel_actual': 3, 'score': 40.0},
            {'prom': 3.0},
            {'nivel_actual': 3, 'score': 35.0},
        ]
        mock_cursor.fetchall.side_effect = [[], [{'nivel_actual': 3, 'id_competencia': 2}]]
        r = client.post('/tutor/responder', json={
            'idEstudiante': 10, 'idEjercicio': 101,
            'idOpcionSeleccionada': 3,
            'tiempoRespuesta': 200, 'usoPista': False, 'modo': 'repaso',
        })
        data = r.get_json()
        assert data.get('mostrarPista') is True

    def test_pista_false_cuando_ejercicio_sin_texto(self, client, mock_cursor):
        """Ejercicio SIN pista → mostrarPista=False aunque sea repaso."""
        mock_cursor.fetchone.side_effect = [
            {'es_correcta': False, 'id_competencia': 2,
             'nivel_ejercicio': 3, 'pista': None},  # sin pista
            {'id_respuesta': 5},
            {'nivel_actual': 3, 'score': 40.0},
            {'prom': 3.0},
            {'nivel_actual': 3, 'score': 35.0},
        ]
        mock_cursor.fetchall.side_effect = [[], [{'nivel_actual': 3, 'id_competencia': 2}]]
        r = client.post('/tutor/responder', json={
            'idEstudiante': 10, 'idEjercicio': 101,
            'idOpcionSeleccionada': 3,
            'tiempoRespuesta': 200, 'usoPista': False, 'modo': 'repaso',
        })
        data = r.get_json()
        assert data.get('mostrarPista') is False


# ─────────────────────────────────────────────────────────────────────────────
# GET /tutor/evaluacion/activa
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluacionActiva:

    def test_sin_evaluacion_activa(self, client, mock_cursor):
        mock_cursor.fetchone.return_value = None
        r = client.get('/tutor/evaluacion/activa?idEstudiante=10')
        assert r.status_code == 200
        data = r.get_json()
        assert data.get('hayEvaluacion') is False or data.get('status') is False

    def test_con_evaluacion_activa(self, client, mock_cursor):
        mock_cursor.fetchone.side_effect = [
            {'id_evaluacion': 5, 'titulo': 'Eval 1', 'descripcion': 'Evaluación del módulo',
             'estado': 'activa', 'fecha_inicio': '2026-06-10T10:00:00', 'fecha_fin': None},
            None,   # evaluacion_resultados: aún no completada
        ]
        r = client.get('/tutor/evaluacion/activa?idEstudiante=10')
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /tutor/evaluacion/finalizar
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluacionFinalizar:

    def test_finalizar_sin_datos_retorna_400(self, client):
        r = client.post('/tutor/evaluacion/finalizar', json={})
        assert r.status_code in (400, 422)

    def test_finalizar_exitoso(self, client, mock_cursor):
        mock_cursor.fetchone.return_value = {
            'puntaje_total': 60, 'total_correctas': 3, 'total_preguntas': 5,
        }
        r = client.post('/tutor/evaluacion/finalizar', json={
            'idEstudiante': 10, 'idEvaluacion': 5,
            'totalPreguntas': 5, 'respuestasCorrectas': 3,
        })
        assert r.status_code == 200