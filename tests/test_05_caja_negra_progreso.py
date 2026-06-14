"""
test_05_caja_negra_progreso.py — Pruebas de CAJA NEGRA: endpoints de progreso
==============================================================================
Tipo  : Funcional / Caja Negra
Rutas : GET /progreso/resumen | GET /progreso/por_competencia
        GET /progreso/historial | GET /progreso/chart
        GET /progreso/tiempo_por_nivel | POST /progreso
"""

import pytest
import json

pytestmark = pytest.mark.black_box

ID_EST = 10   # id_estudiante de prueba


# ─────────────────────────────────────────────────────────────────────────────
# GET /progreso/resumen
# ─────────────────────────────────────────────────────────────────────────────

class TestProgresoResumen:

    def test_sin_id_estudiante_retorna_400(self, client):
        r = client.get('/progreso/resumen')
        assert r.status_code == 400

    def test_retorna_estructura_correcta(self, client, mock_cursor):
        mock_cursor.fetchone.side_effect = [
            {'ejercicios_desarrollados': 12},
            {'lecciones_vistas': 5},
            {'avg_nivel': 3.5, 'progreso_general': 40},
        ]
        r = client.get(f'/progreso/resumen?idEstudiante={ID_EST}')
        assert r.status_code == 200
        data = r.get_json()
        assert data.get('status') is True
        assert 'ejerciciosDesarrollados' in data or 'data' in data

    def test_estudiante_nuevo_retorna_ceros(self, client, mock_cursor):
        """Estudiante sin actividad → valores 0 pero sin error."""
        mock_cursor.fetchone.return_value = None
        r = client.get(f'/progreso/resumen?idEstudiante={ID_EST}')
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# GET /progreso/por_competencia
# ─────────────────────────────────────────────────────────────────────────────

class TestProgresoPorCompetencia:

    def test_sin_id_retorna_400(self, client):
        r = client.get('/progreso/por_competencia')
        assert r.status_code == 400

    def test_retorna_4_competencias(self, client, mock_cursor):
        mock_cursor.fetchall.return_value = [
            {'id_competencia': 1, 'descripcion': 'Cantidad',
             'nivel_actual': 3, 'score': 40.0},
            {'id_competencia': 2, 'descripcion': 'Regularidad',
             'nivel_actual': 4, 'score': 55.0},
            {'id_competencia': 3, 'descripcion': 'Forma',
             'nivel_actual': 2, 'score': 25.0},
            {'id_competencia': 4, 'descripcion': 'Gestión',
             'nivel_actual': 5, 'score': 70.0},
        ]
        r = client.get(f'/progreso/por_competencia?idEstudiante={ID_EST}')
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] is True
        temas = data.get('temas') or data.get('data') or []
        assert len(temas) == 4

    def test_porcentaje_entre_0_y_100(self, client, mock_cursor):
        mock_cursor.fetchall.return_value = [
            {'id_competencia': i, 'descripcion': f'C{i}',
             'nivel_actual': i, 'score': (i - 1) * 14.0}
            for i in range(1, 5)
        ]
        r = client.get(f'/progreso/por_competencia?idEstudiante={ID_EST}')
        data = r.get_json()
        temas = data.get('temas') or []
        for t in temas:
            assert 0 <= t['porcentaje'] <= 100


# ─────────────────────────────────────────────────────────────────────────────
# GET /progreso/historial
# ─────────────────────────────────────────────────────────────────────────────

class TestProgresoHistorial:

    def test_sin_id_retorna_400(self, client):
        r = client.get('/progreso/historial')
        assert r.status_code == 400

    def test_paginacion_limite_y_offset(self, client, mock_cursor):
        """Parámetros limite y offset se pasan a la query."""
        mock_cursor.fetchone.return_value = {'total': 20}
        mock_cursor.fetchall.return_value = [
            {'id_progreso': i, 'id_ejercicio': i * 10, 'ejercicio': f'Ej {i}',
             'estado': 'correcto', 'modo': 'repaso',
             'fecha': '2026-06-13T10:00:00', 'id_competencia': 1,
             'desarrollo_url': None, 'intentos_incorrectos': 0}
            for i in range(1, 6)
        ]
        r = client.get(
            f'/progreso/historial?idEstudiante={ID_EST}&limite=5&offset=0')
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] is True
        items = data.get('items') or data.get('data') or data.get('historial') or []
        assert len(items) == 5

    def test_retorna_hay_mas(self, client, mock_cursor):
        """Cuando hay más páginas, el campo hayMas debe ser True."""
        mock_cursor.fetchone.return_value = {'total': 50}
        mock_cursor.fetchall.return_value = [
            {'id_progreso': i, 'id_ejercicio': i * 10, 'ejercicio': f'Ej {i}',
             'estado': 'correcto', 'modo': 'repaso',
             'fecha': '2026-06-13T10:00:00', 'id_competencia': 1,
             'desarrollo_url': None, 'intentos_incorrectos': 0}
            for i in range(1, 11)
        ]
        r = client.get(
            f'/progreso/historial?idEstudiante={ID_EST}&limite=10&offset=0')
        data = r.get_json()
        assert data.get('hayMas') is True

    def test_intentos_incorrectos_nunca_negativos(self, client, mock_cursor):
        """intentosIncorrectos en la respuesta no debe ser negativo."""
        mock_cursor.fetchone.return_value = {'total': 1}
        mock_cursor.fetchall.return_value = [{
            'id_progreso': 1, 'id_ejercicio': 10, 'ejercicio': 'Ej 1',
            'estado': 'incorrecto', 'modo': 'repaso',
            'fecha': '2026-06-13T10:00:00', 'id_competencia': 1,
            'desarrollo_url': None, 'intentos_incorrectos': -1,
        }]
        r = client.get(f'/progreso/historial?idEstudiante={ID_EST}&limite=5&offset=0')
        data = r.get_json()
        items = data.get('items') or data.get('data') or data.get('historial') or []
        for item in items:
            val = item.get('intentosIncorrectos', 0) or 0
            assert val >= 0


# ─────────────────────────────────────────────────────────────────────────────
# GET /progreso/tiempo_por_nivel
# ─────────────────────────────────────────────────────────────────────────────

class TestTiempoPorNivel:

    def test_sin_id_retorna_400(self, client):
        r = client.get('/progreso/tiempo_por_nivel')
        assert r.status_code == 400

    def test_retorna_bandas_1_a_4(self, client, mock_cursor):
        """Los niveles de dificultad se agrupan en 4 bandas (1=Fácil … 4=Avanzado)."""
        mock_cursor.fetchall.return_value = [
            {'nivel_ejercicio': 1, 'nombre_nivel': 'Fácil',
             'promedio_seg': 90, 'promedio_formato': '1m 30s',
             'total_respuestas': 10, 'tasa_acierto': 0.7},
            {'nivel_ejercicio': 2, 'nombre_nivel': 'Básico',
             'promedio_seg': 200, 'promedio_formato': '3m 20s',
             'total_respuestas': 8,  'tasa_acierto': 0.5},
            {'nivel_ejercicio': 3, 'nombre_nivel': 'Intermedio',
             'promedio_seg': 350, 'promedio_formato': '5m 50s',
             'total_respuestas': 6,  'tasa_acierto': 0.4},
            {'nivel_ejercicio': 4, 'nombre_nivel': 'Avanzado',
             'promedio_seg': 600, 'promedio_formato': '10m 0s',
             'total_respuestas': 3,  'tasa_acierto': 0.3},
        ]
        r = client.get(f'/progreso/tiempo_por_nivel?idEstudiante={ID_EST}')
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] is True
        niveles = data.get('niveles') or []
        assert len(niveles) == 4

    def test_sin_datos_retorna_lista_vacia(self, client, mock_cursor):
        """Sin respuestas → lista vacía, no error."""
        mock_cursor.fetchall.return_value = []
        r = client.get(f'/progreso/tiempo_por_nivel?idEstudiante={ID_EST}')
        assert r.status_code == 200
        data = r.get_json()
        assert data.get('niveles') == []

    def test_tasa_acierto_entre_0_y_1(self, client, mock_cursor):
        """tasa_acierto en el rango [0.0, 1.0]."""
        mock_cursor.fetchall.return_value = [
            {'nivel_ejercicio': 1, 'nombre_nivel': 'Fácil',
             'promedio_seg': 60, 'promedio_formato': '1m',
             'total_respuestas': 5, 'tasa_acierto': 0.8},
        ]
        r = client.get(f'/progreso/tiempo_por_nivel?idEstudiante={ID_EST}')
        data = r.get_json()
        for n in (data.get('niveles') or []):
            assert 0.0 <= n['tasaAcierto'] <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# GET /progreso/chart
# ─────────────────────────────────────────────────────────────────────────────

class TestProgresoChart:

    def test_sin_id_retorna_400(self, client):
        r = client.get('/progreso/chart')
        assert r.status_code == 400

    def test_retorna_series_temporales(self, client, mock_cursor):
        mock_cursor.fetchall.return_value = [
            {'fecha': '10/06 10h', 'puntaje': 70},
            {'fecha': '11/06 11h', 'puntaje': 80},
            {'fecha': '12/06 12h', 'puntaje': 85},
        ]
        r = client.get(f'/progreso/chart?idEstudiante={ID_EST}')
        assert r.status_code == 200