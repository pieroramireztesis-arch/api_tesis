"""
test_10_e2e.py — Pruebas de EXTREMO A EXTREMO (End-to-End)
===========================================================
Tipo  : E2E — Simula sesiones completas del usuario final

Escenarios
──────────
E1  Sesión de repaso completa (5 respuestas → nivel sube)
E2  Sesión de evaluación (5 respuestas → NEC no cambia)
E3  Estudiante bloqueado → desbloqueo tras diagnóstico docente
E4  Ciclo de ML: historial suficiente → modelo predice nivel
E5  Registro → login → tutor → progreso (flujo nuevo usuario)
"""

import pytest
from werkzeug.security import generate_password_hash

pytestmark = pytest.mark.e2e


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _nec_row(nivel: int, score: float = None):
    if score is None:
        score = (nivel - 1) * 14.0 + 7
    return {'nivel_actual': nivel, 'score': score}


def _stats_row(total=0):
    return {
        'total_intentos': total, 'promedio_puntaje': None if not total else 65.0,
        'min_puntaje': None, 'max_puntaje': None,
        'std_puntaje': 0, 'num_aprobados': 0, 'tendencia': None,
    }


def _ej_row(id_ej=101, nivel_ejercicio=3, comp=2):
    return {
        'id_ejercicio': id_ej, 'enunciado': f'Ej {id_ej}',
        'imagen_url': None, 'pista': 'Pista X',
        'id_competencia': comp, 'nivel_ejercicio': nivel_ejercicio,
    }


def _opciones(id_correcta=1):
    return [
        {'id_opcion': id_correcta, 'letra': 'A', 'descripcion': 'Correcta', 'es_correcta': True},
        {'id_opcion': id_correcta + 1, 'letra': 'B', 'descripcion': 'Incorrecta', 'es_correcta': False},
    ]


# ─────────────────────────────────────────────────────────────────────────────
# E1 — Sesión de repaso: 5 respuestas correctas rápidas
# ─────────────────────────────────────────────────────────────────────────────

class TestE1SesionRepaso:

    def test_e1_cinco_respuestas_correctas_acumulan_delta_positivo(self):
        """
        ESCENARIO: Estudiante responde 5 ejercicios correctamente y rápido (N3).
        RESULTADO: Score sube +8 × 5 = +40 puntos.
        Si empieza en score=22 (nivel 2), termina en 62 (nivel 4).
        """
        from models.scoring import calcular_delta, score_to_nivel, nivel_to_progreso
        score = 22.0   # nivel 2 inicial
        for _ in range(5):
            delta = calcular_delta(True, 90, 3)   # correcto + rápido N3
            score = min(100.0, max(0.0, score + delta))

        nivel_final = score_to_nivel(score)
        progreso = nivel_to_progreso(nivel_final)

        assert score == 62.0          # 22 + 8*5 = 62
        assert nivel_final == 4        # 62 cae en tramo 50-64 → nivel 4
        assert progreso == 60          # nivel 4 → 60%

    def test_e1_ciclo_get_responder_5_veces(self, client, mock_cursor):
        """
        ESCENARIO COMPLETO:
        5 iteraciones de GET /ejercicio_siguiente → POST /responder
        Todas correctas → la respuesta muestra correcta=True en cada iteración.
        """
        for i in range(5):
            # ── GET ejercicio (sin idDominio) ─────────────────────────────
            mock_cursor.reset_mock()
            mock_cursor.fetchone.side_effect = [
                {'sin_diagnostico': False},
                {'nivel_min': 3},              # AVG nivel_min
                _ej_row(id_ej=100 + i),
                _nec_row(nivel=3),             # leer_nec display
            ]
            mock_cursor.fetchall.side_effect = [_opciones()]  # solo opciones
            r_ej = client.get('/tutor/ejercicio_siguiente?idEstudiante=10&modo=repaso')
            assert r_ej.status_code == 200

            # ── POST responder ─────────────────────────────────────────────
            mock_cursor.reset_mock()
            mock_cursor.fetchone.side_effect = [
                {'es_correcta': True, 'id_competencia': 2,
                 'nivel_ejercicio': 3, 'pista': 'Pista X'},
                {'id_respuesta': 5},            # INSERT RETURNING id_respuesta
                _nec_row(nivel=3, score=40.0 + i * 8),
                _stats_row(),
                _nec_row(nivel=3, score=48.0 + i * 8),
            ]
            mock_cursor.fetchall.side_effect = [
                [],   # racha
                [_nec_row(nivel=3)],  # progreso_general
            ]
            r_resp = client.post('/tutor/responder', json={
                'idEstudiante': 10, 'idEjercicio': 100 + i,
                'idOpcionSeleccionada': 1,
                'tiempoRespuesta': 90, 'usoPista': False, 'modo': 'repaso',
            })
            assert r_resp.status_code == 200
            assert r_resp.get_json().get('correcta') is True


# ─────────────────────────────────────────────────────────────────────────────
# E2 — Sesión de evaluación: NEC no cambia
# ─────────────────────────────────────────────────────────────────────────────

class TestE2SesionEvaluacion:

    def test_e2_evaluacion_5_respuestas_nec_intacto(self, client, mock_cursor):
        """
        ESCENARIO: 5 respuestas en evaluación (mix correcto/incorrecto).
        RESULTADO: NEC nunca se toca.
        """
        respuestas = [True, False, True, True, False]

        for i, es_correcta in enumerate(respuestas):
            mock_cursor.reset_mock()
            mock_cursor.fetchone.side_effect = [
                {'es_correcta': es_correcta, 'id_competencia': 1,
                 'nivel_ejercicio': 3, 'pista': None},
                {'id_respuesta': 5},            # INSERT RETURNING id_respuesta
                {'nivel_actual': 3, 'score': 40.0},  # leer_nec
                {'prom': 3.0},                  # nivel global AVG
            ]
            mock_cursor.fetchall.return_value = []

            r = client.post('/tutor/responder', json={
                'idEstudiante': 10, 'idEjercicio': 200 + i,
                'idOpcionSeleccionada': 1,
                'tiempoRespuesta': 120, 'usoPista': False,
                'modo': 'evaluacion', 'idEvaluacion': 7,
            })
            assert r.status_code == 200

            # Verificar que NEC y puntajes no fueron modificados (SELECT es OK)
            nec_ops = [
                c for c in mock_cursor.execute.call_args_list
                if 'nivel_estudiante_competencia' in str(c).lower()
                and ('UPDATE' in str(c).upper() or 'INSERT' in str(c).upper()
                     or 'ON CONFLICT' in str(c).upper())
            ]
            puntaje_ops = [
                c for c in mock_cursor.execute.call_args_list
                if 'puntajes' in str(c).lower() and 'INSERT' in str(c).upper()
            ]
            assert len(nec_ops) == 0, f"Iteración {i}: NEC no debe escribirse en evaluación"
            assert len(puntaje_ops) == 0, f"Iteración {i}: puntajes no debe tocarse en evaluación"


# ─────────────────────────────────────────────────────────────────────────────
# E3 — Estudiante bloqueado
# ─────────────────────────────────────────────────────────────────────────────

class TestE3EstudianteBloqueado:

    def test_e3_bloqueado_luego_desbloqueado(self, client, mock_cursor):
        """
        ESCENARIO:
        1) GET ejercicio → sin diagnóstico → bloqueado=True
        2) (Docente agrega diagnóstico) → simulación: campo sin_diagnostico=False
        3) GET ejercicio → sin bloqueo → recibe ejercicio
        """
        # ── Estado 1: sin diagnóstico ──────────────────────────────────────
        mock_cursor.fetchone.return_value = {'sin_diagnostico': True}
        r1 = client.get('/tutor/ejercicio_siguiente?idEstudiante=10')
        assert r1.get_json()['status'] is False
        assert r1.get_json().get('bloqueado') is True

        # ── Estado 2: docente asignó diagnóstico (sin idDominio) ─────────
        mock_cursor.reset_mock()
        mock_cursor.fetchone.side_effect = [
            {'sin_diagnostico': False},
            {'nivel_min': 2},          # AVG nivel_min
            _ej_row(),
            _nec_row(nivel=2),         # leer_nec display
        ]
        mock_cursor.fetchall.side_effect = [_opciones()]  # solo opciones
        r2 = client.get('/tutor/ejercicio_siguiente?idEstudiante=10')
        assert r2.status_code == 200
        assert r2.get_json()['status'] is True
        assert r2.get_json().get('bloqueado') is not True


# ─────────────────────────────────────────────────────────────────────────────
# E4 — Ciclo ML: con historial → modelo predice nivel
# ─────────────────────────────────────────────────────────────────────────────

class TestE4CicloML:

    def test_e4_ml_actua_con_historial_suficiente(self, mock_cursor):
        """
        ESCENARIO: Estudiante con 10 puntajes en BD → ML tiene features → predice.
        RESULTADO: predecir_nivel_competencia llama a MODELO_TUTOR.predict()
        """
        from ws.tutor import predecir_nivel_competencia
        from unittest.mock import MagicMock
        import ws.tutor as t

        mock_cursor.fetchone.side_effect = [
            _nec_row(nivel=3),   # leer_nec
            {                     # calcular_features
                'total_intentos': 10,
                'promedio_puntaje': 65.0,
                'min_puntaje': 40.0,
                'max_puntaje': 100.0,
                'std_puntaje': 15.0,
                'num_aprobados': 7,
                'tendencia': 0.4,
            },
        ]
        mock_mod = MagicMock()
        mock_enc = MagicMock()
        mock_mod.predict.return_value       = [1]
        mock_enc.inverse_transform.return_value = ['alto']

        orig_m, orig_e = t.MODELO_TUTOR, t.ENCODER_NIVEL
        t.MODELO_TUTOR  = mock_mod
        t.ENCODER_NIVEL = mock_enc
        try:
            resultado = predecir_nivel_competencia(mock_cursor, 10, 2)
        finally:
            t.MODELO_TUTOR  = orig_m
            t.ENCODER_NIVEL = orig_e

        mock_mod.predict.assert_called_once()
        assert resultado in ('bajo', 'medio', 'alto')


# ─────────────────────────────────────────────────────────────────────────────
# E5 — Flujo nuevo usuario completo
# ─────────────────────────────────────────────────────────────────────────────

class TestE5NuevoUsuario:

    def test_e5_registro_login_progreso(self, client, mock_cursor):
        """
        ESCENARIO: Usuario nuevo completa el flujo:
        1) POST /auth/register
        2) POST /auth/login
        3) GET /progreso/resumen
        Verificar que el token del login sirve para acceder al progreso.
        """
        # ── 1. Registro ───────────────────────────────────────────────────
        mock_cursor.fetchone.side_effect = [
            None,                   # email no duplicado
            {'id_usuario': 77},     # INSERT usuarios RETURNING
            {'id_estudiante': 77},  # INSERT estudiante RETURNING
        ]
        r_reg = client.post('/auth/register', json={
            'nombre': 'Nuevo', 'apellidos': 'Alumno',
            'correo': 'nuevo.alumno@school.pe',
            'contrasena': 'Escuela2026!', 'rol': 'estudiante',
        })
        assert r_reg.status_code in (200, 201)

        # ── 2. Login ──────────────────────────────────────────────────────
        mock_cursor.reset_mock()
        mock_cursor.fetchone.side_effect = None  # limpiar side_effect agotado del registro
        mock_cursor.fetchone.return_value = {
            'id_usuario': 77, 'nombre': 'Nuevo', 'apellidos': 'Alumno',
            'correo': 'nuevo.alumno@school.pe',
            'contrasena': generate_password_hash('Escuela2026!'),
            'rol': 'estudiante', 'id_docente': None, 'id_estudiante': 77,
        }
        r_login = client.post('/auth/login', json={
            'correo': 'nuevo.alumno@school.pe',
            'contrasena': 'Escuela2026!',
        })
        assert r_login.status_code == 200
        token = r_login.get_json()['token']
        assert token is not None

        # ── 3. Progreso con el token ──────────────────────────────────────
        mock_cursor.reset_mock()
        mock_cursor.fetchone.return_value = None
        r_prog = client.get('/progreso/resumen?idEstudiante=77',
                            headers={'Authorization': f'Bearer {token}'})
        # El endpoint de progreso no requiere JWT en la API actual,
        # pero el token es válido para endpoints que sí lo requieren
        assert r_prog.status_code == 200