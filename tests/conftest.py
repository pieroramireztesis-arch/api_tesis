"""
conftest.py — Configuración global de pruebas para TutorMath API REST
======================================================================
Estrategia de mocking
─────────────────────
• Inyecta 'conexionBD' falso en sys.modules ANTES de importar la app Flask.
• Todos los ws/* que hagan 'from conexionBD import Conexion' recibirán
  _FakeConexion, que devuelve _DB_CURSOR (MagicMock reconfigurable).
• Cada test puede reasignar .fetchone/.fetchall con side_effect o return_value.
• El fixture mock_cursor resetea el mock antes/después de cada test.

Tests de BD real
────────────────
• Los tests marcados @pytest.mark.db usan la BD real y están OMITIDOS por defecto.
  Ejecutar con:  pytest -m db --real-db
"""

import sys
import os
import json
import pytest
from unittest.mock import MagicMock
from werkzeug.security import generate_password_hash

# ──────────────────────────────────────────────────────────────────────────────
# 1. PYTHONPATH → los tests encuentran la app
# ──────────────────────────────────────────────────────────────────────────────
ROOT    = os.path.dirname(__file__)                        # …/tests/
API_DIR = os.path.abspath(os.path.join(ROOT, '..', 'API_COMERCIAL'))
sys.path.insert(0, API_DIR)

# ──────────────────────────────────────────────────────────────────────────────
# 2. Mock de conexionBD ANTES de cualquier import de la app
# ──────────────────────────────────────────────────────────────────────────────
_DB_CURSOR = MagicMock(name='db_cursor')
_DB_CURSOR.fetchone.return_value  = None
_DB_CURSOR.fetchall.return_value  = []
_DB_CURSOR.rowcount               = 1
_DB_CURSOR.description            = []

_DB_CONN = MagicMock(name='db_conn')
_DB_CONN.cursor.return_value = _DB_CURSOR
_DB_CONN.commit   = MagicMock()
_DB_CONN.rollback = MagicMock()
_DB_CONN.close    = MagicMock()


class _FakeConexion:
    """Sustituye conexionBD.Conexion durante toda la suite de tests."""
    def __init__(self):
        pass
    def cursor(self):
        return _DB_CURSOR
    def commit(self):
        pass
    def rollback(self):
        pass
    def close(self):
        pass


_conexion_mod        = MagicMock()
_conexion_mod.Conexion = _FakeConexion
sys.modules['conexionBD'] = _conexion_mod

# psycopg2 puede no estar disponible en el entorno de CI/tests
sys.modules.setdefault('psycopg2',         MagicMock())
sys.modules.setdefault('psycopg2.extras',  MagicMock())

# ──────────────────────────────────────────────────────────────────────────────
# 3. Importar la Flask app (usa el mock arriba)
# ──────────────────────────────────────────────────────────────────────────────
from app import app as _flask_app  # noqa: E402  (_migrar_columnas usa el mock)

_flask_app.config.update({
    'TESTING':        True,
    'JWT_SECRET_KEY': 'test-jwt-tutormath-2026',
})

# ──────────────────────────────────────────────────────────────────────────────
# 4. Fixtures globales
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope='session')
def app():
    return _flask_app


@pytest.fixture(scope='session')
def client(app):
    return app.test_client()


@pytest.fixture(scope='session')
def auth_token(app):
    """JWT válido para id_usuario='1' (estudiante de prueba)."""
    with app.app_context():
        from flask_jwt_extended import create_access_token
        return create_access_token(
            identity='1',
            additional_claims={'rol': 'estudiante', 'correo': 'test@test.com'},
        )


@pytest.fixture(scope='session')
def auth_headers(auth_token):
    return {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type':  'application/json',
    }


@pytest.fixture
def mock_cursor():
    """
    Devuelve _DB_CURSOR con estado limpio.
    Reseteado automáticamente antes y después de cada test.
    """
    _DB_CURSOR.reset_mock()
    _DB_CURSOR.fetchone.return_value  = None
    _DB_CURSOR.fetchone.side_effect   = None
    _DB_CURSOR.fetchall.return_value  = []
    _DB_CURSOR.fetchall.side_effect   = None
    _DB_CURSOR.rowcount               = 1
    yield _DB_CURSOR
    _DB_CURSOR.reset_mock()


# ──────────────────────────────────────────────────────────────────────────────
# 5. Datos de prueba reutilizables
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope='session')
def usuario_estudiante():
    return {
        'id_usuario':   1,
        'nombre':       'Ana',
        'apellidos':    'García',
        'correo':       'ana@test.com',
        'contrasena':   generate_password_hash('pass123'),
        'rol':          'estudiante',
        'id_docente':   None,
        'id_estudiante': 10,
    }


@pytest.fixture(scope='session')
def usuario_docente():
    return {
        'id_usuario':   2,
        'nombre':       'Prof',
        'apellidos':    'Ríos',
        'correo':       'prof@test.com',
        'contrasena':   generate_password_hash('docpass'),
        'rol':          'docente',
        'id_docente':   5,
        'id_estudiante': None,
    }


@pytest.fixture(scope='session')
def ejercicio_ejemplo():
    return {
        'id_ejercicio':   101,
        'enunciado':      '¿Cuánto es 2x + 3 = 7?',
        'imagen_url':     None,
        'pista':          'Despeja x.',
        'id_competencia': 2,
        'nivel_logro':    3,
        'nivel':          1,
    }


@pytest.fixture(scope='session')
def opciones_ejemplo():
    return [
        {'id_opcion': 1, 'texto': 'x = 2', 'es_correcta': True},
        {'id_opcion': 2, 'texto': 'x = 3', 'es_correcta': False},
        {'id_opcion': 3, 'texto': 'x = 4', 'es_correcta': False},
        {'id_opcion': 4, 'texto': 'x = 1', 'es_correcta': False},
    ]


# ──────────────────────────────────────────────────────────────────────────────
# 6. Helpers de petición HTTP
# ──────────────────────────────────────────────────────────────────────────────

def _get(client, path, params=None, headers=None):
    return client.get(path, query_string=params or {}, headers=headers or {})


def _post(client, path, data, headers=None):
    return client.post(path, json=data, headers=headers or {})


def _put(client, path, data, headers=None):
    return client.put(path, json=data, headers=headers or {})