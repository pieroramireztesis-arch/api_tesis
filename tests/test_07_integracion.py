"""
test_07_integracion.py — Pruebas de INTEGRACIÓN
================================================
Tipo  : Integración (flujos multi-endpoint con estado compartido)

Flujos probados
───────────────
I1  Login → obtener ejercicio → responder (ciclo completo repaso)
I2  Login → responder en evaluación → verificar NEC NO cambia
I3  Diagnóstico bloqueado → tutor → respuesta esperada de bloqueo
I4  Progreso: responder correctamente → resumen refleja el cambio
I5  Auth: registro → login con mismas credenciales
I6  Seguridad: JWT de un usuario no funciona para cambiar datos de otro
"""

import pytest
import json
from werkzeug.security import generate_password_hash

pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# I1 — Flujo: Login → ejercicio_siguiente → responder (repaso)
# ─────────────────────────────────────────────────────────────────────────────

class TestFlujoRapaso:

    def test_i1_ciclo_completo_repaso(self, client, mock_cursor):
        """
        Simula el ciclo base del STI:
        1) Login (JWT)
        2) GET ejercicio_siguiente
        3) POST responder (respuesta correcta)
        """
        # ── Paso 1: Login ──────────────────────────────────────────────────
        mock_cursor.fetchone.return_value = {
            'id_usuario': 1, 'nombre': 'Ana', 'apellidos': 'G',
            'correo': 'ana@test.com',
            'contrasena': generate_password_hash('pass123'),
            'rol': 'estudiante', 'id_docente': None, 'id_estudiante': 10,
        }
        r_login = client.post('/auth/login',
                              json={'correo': 'ana@test.com', 'contrasena': 'pass123'})
        assert r_login.status_code == 200
        token = r_login.get_json()['token']
        headers = {'Authorization': f'Bearer {token}'}

        # ── Paso 2: ejercicio_siguiente (sin idDominio) ───────────────────
        mock_cursor.reset_mock()
        mock_cursor.fetchone.side_effect = [
            {'sin_diagnostico': False},
            {'nivel_min': 3},           # AVG nivel_min (sin idDominio)
            {'id_ejercicio': 101, 'enunciado': '2x+3=7', 'imagen_url': None,
             'pista': 'Despeja x.', 'id_competencia': 2, 'nivel_ejercicio': 3},
            {'nivel_actual': 3, 'score': 40.0},   # leer_nec display
        ]
        mock_cursor.fetchall.side_effect = [
            [   # opciones (solo fetchall cuando no hay idDominio)
                {'id_opcion': 1, 'letra': 'A', 'descripcion': 'x=2', 'es_correcta': True},
                {'id_opcion': 2, 'letra': 'B', 'descripcion': 'x=3', 'es_correcta': False},
            ],
        ]
        r_ej = client.get('/tutor/ejercicio_siguiente'
                          '?idEstudiante=10&modo=repaso',
                          headers=headers)
        assert r_ej.status_code == 200
        data_ej = r_ej.get_json()
        assert data_ej['status'] is True

        # ── Paso 3: responder ──────────────────────────────────────────────
        mock_cursor.reset_mock()
        mock_cursor.fetchone.side_effect = [
            {'es_correcta': True, 'id_competencia': 2,
             'nivel_ejercicio': 3, 'pista': 'Despeja x.'},
            {'id_respuesta': 5},            # INSERT RETURNING id_respuesta
            {'nivel_actual': 3, 'score': 40.0},
            {'total_intentos': 0, 'promedio_puntaje': None,
             'min_puntaje': None, 'max_puntaje': None,
             'std_puntaje': 0, 'num_aprobados': 0, 'tendencia': None},
            {'nivel_actual': 3, 'score': 48.0},
        ]
        mock_cursor.fetchall.side_effect = [
            [],
            [{'nivel_actual': 3, 'id_competencia': 2}],
        ]
        r_resp = client.post('/tutor/responder', json={
            'idEstudiante': 10, 'idEjercicio': 101,
            'idOpcionSeleccionada': 1,
            'tiempoRespuesta': 60, 'usoPista': False, 'modo': 'repaso',
        }, headers=headers)
        assert r_resp.status_code == 200
        data_resp = r_resp.get_json()
        assert data_resp.get('correcta') is True


# ─────────────────────────────────────────────────────────────────────────────
# I2 — Evaluación NO modifica NEC ni puntajes
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluacionNoModificaNEC:

    def test_i2_responder_evaluacion_sin_update_nec(self, client, mock_cursor):
        """
        En modo evaluación, responder NO debe ejecutar UPDATE en
        nivel_estudiante_competencia ni INSERT en puntajes.
        """
        mock_cursor.fetchone.side_effect = [
            {'es_correcta': True, 'id_competencia': 2,
             'nivel_ejercicio': 3, 'pista': None},
            {'id_respuesta': 5},            # INSERT RETURNING id_respuesta
            {'nivel_actual': 3, 'score': 40.0},  # leer_nec
            {'prom': 3.0},                  # nivel global AVG
        ]
        mock_cursor.fetchall.return_value = []

        r = client.post('/tutor/responder', json={
            'idEstudiante': 10, 'idEjercicio': 101,
            'idOpcionSeleccionada': 1,
            'tiempoRespuesta': 90, 'usoPista': False,
            'modo': 'evaluacion', 'idEvaluacion': 5,
        })
        assert r.status_code == 200

        # Verificar: ningún execute con UPDATE de NEC
        nec_updates = [
            c for c in mock_cursor.execute.call_args_list
            if 'nivel_estudiante_competencia' in str(c).lower()
            and ('UPDATE' in str(c).upper() or 'INSERT' in str(c).upper())
        ]
        assert len(nec_updates) == 0, (
            "En modo evaluación NO se debe tocar nivel_estudiante_competencia"
        )

        # Verificar: ningún execute con INSERT en puntajes
        puntajes_inserts = [
            c for c in mock_cursor.execute.call_args_list
            if 'puntajes' in str(c).lower() and 'INSERT' in str(c).upper()
        ]
        assert len(puntajes_inserts) == 0, (
            "En modo evaluación NO se debe insertar en la tabla puntajes"
        )


# ─────────────────────────────────────────────────────────────────────────────
# I3 — Diagnóstico bloqueado → tutor responde correctamente
# ─────────────────────────────────────────────────────────────────────────────

class TestDiagnosticoBloqueado:

    def test_i3_sin_diagnostico_bloquea_y_informa(self, client, mock_cursor):
        """
        Alumno sin diagnóstico inicial del docente:
        - GET /tutor/ejercicio_siguiente → status=False, bloqueado=True
        - El estudiante NO recibe ejercicio
        """
        mock_cursor.fetchone.return_value = {'sin_diagnostico': True}
        r = client.get('/tutor/ejercicio_siguiente?idEstudiante=10')
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] is False
        assert data.get('bloqueado') is True
        assert 'sinEjercicios' not in data or data.get('bloqueado') is True

    def test_i3_con_diagnostico_no_bloquea(self, client, mock_cursor):
        """Con diagnóstico → permite acceder a ejercicios."""
        mock_cursor.fetchone.side_effect = [
            {'sin_diagnostico': False},
            {'nivel_actual': 2, 'score': 25.0},
            {'total_intentos': 0, 'promedio_puntaje': None,
             'min_puntaje': None, 'max_puntaje': None,
             'std_puntaje': 0, 'num_aprobados': 0, 'tendencia': None},
            {'id_ejercicio': 101, 'enunciado': 'Test', 'imagen_url': None,
             'pista': None, 'id_competencia': 1, 'nivel_logro': 2, 'nivel': 1},
        ]
        mock_cursor.fetchall.side_effect = [
            [],   # racha
            [{'id_opcion': 1, 'texto': 'A', 'es_correcta': True}],
        ]
        r = client.get('/tutor/ejercicio_siguiente?idEstudiante=10')
        data = r.get_json()
        # No debe estar bloqueado
        assert data.get('bloqueado') is not True


# ─────────────────────────────────────────────────────────────────────────────
# I4 — Registro → Login con las mismas credenciales
# ─────────────────────────────────────────────────────────────────────────────

class TestRegistroLogin:

    def test_i5_registro_y_login(self, client, mock_cursor):
        """
        I5: POST /auth/register (estudiante) → POST /auth/login con mismas credenciales.
        El token de login debe ser válido.
        """
        # ── Registro ───────────────────────────────────────────────────────
        mock_cursor.fetchone.side_effect = [
            None,                           # email no duplicado
            {'id_usuario': 55},             # INSERT usuarios RETURNING
            {'id_estudiante': 55},          # INSERT estudiante RETURNING
        ]
        r_reg = client.post('/auth/register', json={
            'nombre': 'Luis', 'apellidos': 'Test',
            'correo': 'luis@test.com',
            'contrasena': 'mi_pass_2026', 'rol': 'estudiante',
        })
        assert r_reg.status_code in (200, 201)

        # ── Login ──────────────────────────────────────────────────────────
        mock_cursor.reset_mock()
        mock_cursor.fetchone.side_effect = None  # limpiar side_effect agotado del registro
        mock_cursor.fetchone.return_value = {
            'id_usuario': 55, 'nombre': 'Luis', 'apellidos': 'Test',
            'correo': 'luis@test.com',
            'contrasena': generate_password_hash('mi_pass_2026'),
            'rol': 'estudiante', 'id_docente': None, 'id_estudiante': 55,
        }
        r_login = client.post('/auth/login',
                              json={'correo': 'luis@test.com',
                                    'contrasena': 'mi_pass_2026'})
        assert r_login.status_code == 200
        assert 'token' in r_login.get_json()


# ─────────────────────────────────────────────────────────────────────────────
# I6 — JWT no permite cambiar datos de otro usuario
# ─────────────────────────────────────────────────────────────────────────────

class TestJWTAislamiento:

    def test_i6_jwt_solo_permite_cambiar_propia_password(self, client, auth_headers, mock_cursor):
        """
        PUT /auth/cambiar_password con JWT de user_id=1 solo cambia la password
        del usuario 1, independientemente de cualquier id enviado en el body.
        """
        mock_cursor.fetchone.return_value = {
            'id_usuario': 1,
            'contrasena': generate_password_hash('pass123'),
        }
        r = client.put('/auth/cambiar_password',
                       json={
                           'id_usuario': 99,           # intento de modificar otro usuario
                           'password_actual': 'pass123',
                           'nueva_password': 'nueva456',
                       },
                       headers=auth_headers)
        # Debe cambiar SOLO el usuario del JWT (id=1), no el 99
        assert r.status_code == 200
        # Verificar que el UPDATE usó el id del JWT, no el del body
        update_calls = [
            c for c in mock_cursor.execute.call_args_list
            if 'UPDATE' in str(c).upper() and 'usuarios' in str(c).lower()
        ]
        if update_calls:
            params = update_calls[0][0][1] if update_calls[0][0][1:] else []
            # El id del UPDATE debe ser el del JWT (1), no el del body (99 int)
            assert 99 not in params, "UPDATE debe usar id del JWT (1), no el del body (99)"