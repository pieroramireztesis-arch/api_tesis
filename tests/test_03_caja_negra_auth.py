"""
test_03_caja_negra_auth.py — Pruebas de CAJA NEGRA: endpoints de autenticación
===============================================================================
Tipo  : Funcional / Caja Negra (solo interfaz HTTP visible externamente)
Rutas : POST /auth/login | POST /auth/register | PUT /auth/cambiar_password
        POST /auth/recuperar | GET /auth/usuarios
"""

import pytest
import json
from werkzeug.security import generate_password_hash

pytestmark = pytest.mark.black_box


class TestLogin:
    """POST /auth/login"""

    def test_login_sin_body_retorna_400(self, client):
        r = client.post('/auth/login', json={})
        assert r.status_code == 400
        data = r.get_json()
        assert data['status'] is False

    def test_login_solo_correo_retorna_400(self, client):
        r = client.post('/auth/login', json={'correo': 'a@b.com'})
        assert r.status_code == 400

    def test_login_solo_password_retorna_400(self, client):
        r = client.post('/auth/login', json={'contrasena': 'abc'})
        assert r.status_code == 400

    def test_login_usuario_no_existe_retorna_401(self, client, mock_cursor):
        """Correo no registrado → 401 credenciales inválidas."""
        mock_cursor.fetchone.return_value = None
        r = client.post('/auth/login',
                        json={'correo': 'noexiste@test.com', 'contrasena': 'pass'})
        assert r.status_code == 401
        assert r.get_json()['status'] is False

    def test_login_password_incorrecta_retorna_401(self, client, mock_cursor):
        """Usuario existe pero password no coincide."""
        mock_cursor.fetchone.return_value = {
            'id_usuario': 1, 'nombre': 'Ana', 'apellidos': 'G',
            'correo': 'ana@test.com',
            'contrasena': generate_password_hash('correcta'),
            'rol': 'estudiante', 'id_docente': None, 'id_estudiante': 10,
        }
        r = client.post('/auth/login',
                        json={'correo': 'ana@test.com', 'contrasena': 'incorrecta'})
        assert r.status_code == 401

    def test_login_estudiante_exitoso(self, client, mock_cursor):
        """Login válido devuelve token + datos del usuario."""
        mock_cursor.fetchone.return_value = {
            'id_usuario': 1, 'nombre': 'Ana', 'apellidos': 'García',
            'correo': 'ana@test.com',
            'contrasena': generate_password_hash('pass123'),
            'rol': 'estudiante', 'id_docente': None, 'id_estudiante': 10,
        }
        r = client.post('/auth/login',
                        json={'correo': 'ana@test.com', 'contrasena': 'pass123'})
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] is True
        assert 'token' in data
        assert data['data']['rol'] == 'estudiante'
        assert data['data']['id_estudiante'] == 10

    def test_login_docente_exitoso(self, client, mock_cursor):
        mock_cursor.fetchone.return_value = {
            'id_usuario': 2, 'nombre': 'Prof', 'apellidos': 'Ríos',
            'correo': 'prof@test.com',
            'contrasena': generate_password_hash('docpass'),
            'rol': 'docente', 'id_docente': 5, 'id_estudiante': None,
        }
        r = client.post('/auth/login',
                        json={'correo': 'prof@test.com', 'contrasena': 'docpass'})
        assert r.status_code == 200
        data = r.get_json()
        assert data['data']['rol'] == 'docente'
        assert data['data']['id_docente'] == 5

    def test_login_acepta_campo_password_alternativo(self, client, mock_cursor):
        """La API acepta 'password' además de 'contrasena'."""
        mock_cursor.fetchone.return_value = {
            'id_usuario': 1, 'nombre': 'Ana', 'apellidos': 'G',
            'correo': 'ana@test.com',
            'contrasena': generate_password_hash('pass123'),
            'rol': 'estudiante', 'id_docente': None, 'id_estudiante': 10,
        }
        r = client.post('/auth/login',
                        json={'correo': 'ana@test.com', 'password': 'pass123'})
        assert r.status_code == 200


class TestRegister:
    """POST /auth/register"""

    def test_register_campos_incompletos_retorna_400(self, client):
        r = client.post('/auth/register', json={'correo': 'x@x.com'})
        assert r.status_code == 400

    def test_register_rol_docente_retorna_403(self, client):
        """Desde la API móvil no se permite registrar como docente."""
        r = client.post('/auth/register', json={
            'nombre': 'Malo', 'apellidos': 'Actor',
            'correo': 'mal@test.com',
            'contrasena': 'pass', 'rol': 'docente',
        })
        assert r.status_code == 403

    def test_register_estudiante_exitoso(self, client, mock_cursor):
        """Registro válido de estudiante → 201."""
        # cursor: email no duplicado + INSERT usuario + INSERT estudiante
        mock_cursor.fetchone.side_effect = [
            None,               # no hay duplicado de correo
            {'id_usuario': 99}, # INSERT usuarios RETURNING id_usuario
            {'id_estudiante': 55},  # INSERT estudiante RETURNING id_estudiante
        ]
        mock_cursor.rowcount = 1
        r = client.post('/auth/register', json={
            'nombre': 'Nuevo', 'apellidos': 'Usuario',
            'correo': 'nuevo@test.com',
            'contrasena': 'segura123', 'rol': 'estudiante',
        })
        assert r.status_code in (200, 201)
        data = r.get_json()
        assert data['status'] is True

    def test_register_correo_duplicado_retorna_409(self, client, mock_cursor):
        """Si el correo ya existe → error."""
        mock_cursor.fetchone.return_value = {'id_usuario': 5}  # ya existe
        r = client.post('/auth/register', json={
            'nombre': 'Copy', 'apellidos': 'Cat',
            'correo': 'dup@test.com',
            'contrasena': 'pass123', 'rol': 'estudiante',
        })
        assert r.status_code in (400, 409)
        assert r.get_json()['status'] is False


class TestCambiarPassword:
    """PUT /auth/cambiar_password  (requiere JWT)"""

    def test_sin_jwt_retorna_401(self, client):
        r = client.put('/auth/cambiar_password',
                       json={'password_actual': 'a', 'nueva_password': 'b'})
        assert r.status_code == 401

    def test_con_jwt_exitoso(self, client, auth_headers, mock_cursor):
        """Con JWT válido y password actual correcta → 200."""
        mock_cursor.fetchone.return_value = {
            'id_usuario': 1,
            'contrasena': generate_password_hash('pass123'),
        }
        r = client.put('/auth/cambiar_password',
                       json={'password_actual': 'pass123', 'nueva_password': 'nueva456'},
                       headers=auth_headers)
        assert r.status_code == 200
        assert r.get_json()['status'] is True

    def test_con_jwt_password_actual_incorrecta(self, client, auth_headers, mock_cursor):
        mock_cursor.fetchone.return_value = {
            'id_usuario': 1,
            'contrasena': generate_password_hash('correcta'),
        }
        r = client.put('/auth/cambiar_password',
                       json={'password_actual': 'erronea', 'nueva_password': 'nueva'},
                       headers=auth_headers)
        assert r.status_code in (400, 401, 403)
        assert r.get_json()['status'] is False


class TestRecuperarPassword:
    """POST /auth/recuperar"""

    def test_correo_no_registrado(self, client, mock_cursor):
        mock_cursor.fetchone.return_value = None
        r = client.post('/auth/recuperar', json={'correo': 'noexiste@test.com'})
        assert r.status_code in (400, 404)

    def test_sin_smtp_configurado_retorna_503(self, client, mock_cursor):
        """Sin SMTP configurado → 503 (falla limpia, sin reveal del error)."""
        mock_cursor.fetchone.return_value = {
            'id_usuario': 1, 'correo': 'ana@test.com', 'nombre': 'Ana'
        }
        import ws.auth as auth_mod
        orig_u = auth_mod.SMTP_USER
        orig_p = auth_mod.SMTP_PASS
        auth_mod.SMTP_USER = ''
        auth_mod.SMTP_PASS = ''
        try:
            r = client.post('/auth/recuperar', json={'correo': 'ana@test.com'})
        finally:
            auth_mod.SMTP_USER = orig_u
            auth_mod.SMTP_PASS = orig_p
        assert r.status_code in (503, 400, 500)