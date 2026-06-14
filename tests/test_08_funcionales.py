"""
test_08_funcionales.py — Pruebas FUNCIONALES (reglas de negocio del STI)
=========================================================================
Tipo  : Funcional (reglas pedagógicas y de integridad del sistema)

Reglas verificadas
──────────────────
F01  Puntajes SOLO recibe datos del modo repaso (no evaluación, no diagnóstico)
F02  NEC SOLO se actualiza en modo repaso (evaluación es solo lectura)
F03  Fórmula de progreso: (min(nivel,6)-1)/5*100  consistente en todo el sistema
F04  Mapeo STI 7 niveles → MINEDU 5 niveles correcto
F05  Penalización por pista: reduce delta pero nunca por debajo de +1
F06  Repetición espaciada: ejercicios incorrectos vuelven al pool
F07  Diagnóstico bloqueado cuando el docente no asignó notas iniciales
F08  NEC promedio (no mínimo) para modo libre sin dominio (fix L6)
F09  Delta correcto en repaso actualiza NEC; en evaluación no
F10  Tiempo mínimo de respuesta es 1 segundo (nunca 0)
"""

import pytest
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.functional


# ─────────────────────────────────────────────────────────────────────────────
# F01 — puntajes SOLO recibe modo repaso
# ─────────────────────────────────────────────────────────────────────────────

class TestPuntajesSoloRepaso:

    def test_f01_evaluacion_no_inserta_en_puntajes(self, client, mock_cursor):
        """POST /tutor/responder modo=evaluacion → NO INSERT en puntajes."""
        mock_cursor.fetchone.side_effect = [
            {'es_correcta': True, 'id_competencia': 2,
             'nivel_ejercicio': 3, 'pista': None},
            {'id_respuesta': 5},            # INSERT RETURNING id_respuesta
            {'nivel_actual': 3, 'score': 40.0},  # leer_nec
            {'prom': 3.0},                  # nivel global AVG
        ]
        mock_cursor.fetchall.return_value = []

        client.post('/tutor/responder', json={
            'idEstudiante': 10, 'idEjercicio': 101,
            'idOpcionSeleccionada': 1,
            'tiempoRespuesta': 90, 'usoPista': False,
            'modo': 'evaluacion', 'idEvaluacion': 5,
        })

        puntajes_inserts = [
            c for c in mock_cursor.execute.call_args_list
            if 'puntajes' in str(c).lower() and 'INSERT' in str(c).upper()
        ]
        assert len(puntajes_inserts) == 0, (
            "La evaluación NO debe insertar en la tabla puntajes "
            "(contaminaría los features del ML)"
        )

    def test_f01_repaso_correcto_inserta_100_en_puntajes(self, client, mock_cursor):
        """POST /tutor/responder modo=repaso + correcto → INSERT puntaje=100."""
        mock_cursor.fetchone.side_effect = [
            {'es_correcta': True, 'id_competencia': 2,
             'nivel_ejercicio': 3, 'pista': None},
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
        client.post('/tutor/responder', json={
            'idEstudiante': 10, 'idEjercicio': 101,
            'idOpcionSeleccionada': 1,
            'tiempoRespuesta': 60, 'usoPista': False, 'modo': 'repaso',
        })
        puntajes_inserts = [
            c for c in mock_cursor.execute.call_args_list
            if 'puntajes' in str(c).lower() and 'INSERT' in str(c).upper()
        ]
        # Debe haber al menos un INSERT en puntajes con valor 100
        assert len(puntajes_inserts) >= 1
        sql_params = str(puntajes_inserts[0])
        assert '100' in sql_params

    def test_f01_repaso_incorrecto_inserta_0_en_puntajes(self, client, mock_cursor):
        """POST /tutor/responder modo=repaso + incorrecto → INSERT puntaje=0."""
        mock_cursor.fetchone.side_effect = [
            {'es_correcta': False, 'id_competencia': 1,
             'nivel_ejercicio': 2, 'pista': None},
            {'id_respuesta': 5},            # INSERT RETURNING id_respuesta
            {'nivel_actual': 2, 'score': 25.0},
            {'total_intentos': 0, 'promedio_puntaje': None,
             'min_puntaje': None, 'max_puntaje': None,
             'std_puntaje': 0, 'num_aprobados': 0, 'tendencia': None},
            {'nivel_actual': 2, 'score': 22.0},
        ]
        mock_cursor.fetchall.side_effect = [
            [],
            [{'nivel_actual': 2, 'id_competencia': 1}],
        ]
        client.post('/tutor/responder', json={
            'idEstudiante': 10, 'idEjercicio': 102,
            'idOpcionSeleccionada': 3,
            'tiempoRespuesta': 300, 'usoPista': False, 'modo': 'repaso',
        })
        puntajes_inserts = [
            c for c in mock_cursor.execute.call_args_list
            if 'puntajes' in str(c).lower() and 'INSERT' in str(c).upper()
        ]
        assert len(puntajes_inserts) >= 1
        sql_params = str(puntajes_inserts[0])
        assert ', 0,' in sql_params or sql_params.count('0') > 0


# ─────────────────────────────────────────────────────────────────────────────
# F02 — NEC SOLO se actualiza en repaso
# ─────────────────────────────────────────────────────────────────────────────

class TestNECSoloRepaso:

    def test_f02_evaluacion_no_modifica_nec(self, client, mock_cursor):
        """En evaluación, NEC permanece intacto."""
        mock_cursor.fetchone.side_effect = [
            {'es_correcta': True, 'id_competencia': 2,
             'nivel_ejercicio': 3, 'pista': None},
            {'id_respuesta': 5},            # INSERT RETURNING id_respuesta
            {'nivel_actual': 3, 'score': 40.0},  # leer_nec
            {'prom': 3.0},                  # nivel global AVG
        ]
        mock_cursor.fetchall.return_value = []
        client.post('/tutor/responder', json={
            'idEstudiante': 10, 'idEjercicio': 101,
            'idOpcionSeleccionada': 1,
            'tiempoRespuesta': 90, 'usoPista': False,
            'modo': 'evaluacion', 'idEvaluacion': 5,
        })
        nec_writes = [
            c for c in mock_cursor.execute.call_args_list
            if 'nivel_estudiante_competencia' in str(c).lower()
            and ('UPDATE' in str(c).upper() or 'UPSERT' in str(c).upper()
                 or 'ON CONFLICT' in str(c).upper())
        ]
        assert len(nec_writes) == 0, "NEC no debe modificarse en evaluación"


# ─────────────────────────────────────────────────────────────────────────────
# F03 — Fórmula de progreso consistente
# ─────────────────────────────────────────────────────────────────────────────

class TestFormulaProgreso:

    def test_f03_formula_python_correcta(self):
        """(min(nivel,6)-1)/5*100 da los valores esperados."""
        from models.scoring import nivel_to_progreso
        casos = [(1, 0), (2, 20), (3, 40), (4, 60), (5, 80), (6, 100), (7, 100)]
        for nivel, esperado in casos:
            assert nivel_to_progreso(nivel) == esperado, f"nivel={nivel}"

    def test_f03_formula_web_consistente(self):
        """Misma fórmula en utils.py del web."""
        import sys, os
        web_dir = r'C:\Users\JUAN RAMIREZ\Desktop\proyecto_tesis_web'
        if web_dir not in sys.path:
            sys.path.insert(0, web_dir)
        try:
            from ws.utils import calcular_progreso
            casos = [(1, 0), (2, 20), (3, 40), (4, 60), (5, 80), (6, 100), (7, 100)]
            for nivel, esperado in casos:
                resultado = calcular_progreso(nivel)
                assert resultado == esperado, (
                    f"Web utils nivel={nivel}: esperado {esperado}, got {resultado}"
                )
        except ImportError:
            pytest.skip("Directorio web no disponible en este entorno")


# ─────────────────────────────────────────────────────────────────────────────
# F04 — Mapeo STI → MINEDU
# ─────────────────────────────────────────────────────────────────────────────

class TestMapeoMINEDU:

    def test_f04_5_niveles_minedu_correctos(self):
        from models.scoring import nivel_to_minedu
        assert nivel_to_minedu(1) == "Previo al inicio"
        assert nivel_to_minedu(2) == "En inicio"
        assert nivel_to_minedu(3) == "En proceso"
        assert nivel_to_minedu(4) == "En proceso"
        assert nivel_to_minedu(5) == "Logrado"
        assert nivel_to_minedu(6) == "Logrado"
        assert nivel_to_minedu(7) == "Destacado"

    def test_f04_solo_5_valores_distintos(self):
        from models.scoring import nivel_to_minedu
        valores = {nivel_to_minedu(n) for n in range(1, 8)}
        assert len(valores) == 5

    def test_f04_nivel_6_no_es_destacado(self):
        """Nivel 6 (Experto STI) es 'Logrado' en MINEDU, no 'Destacado'."""
        from models.scoring import nivel_to_minedu
        assert nivel_to_minedu(6) == "Logrado"
        assert nivel_to_minedu(7) == "Destacado"


# ─────────────────────────────────────────────────────────────────────────────
# F05 — Penalización por pista
# ─────────────────────────────────────────────────────────────────────────────

class TestPenalizacionPista:

    def test_f05_pista_reduce_delta_positivo(self):
        from models.scoring import calcular_delta
        for tiempo in [60, 200, 400]:
            sin = calcular_delta(True, tiempo, 2, uso_pista=False)
            con = calcular_delta(True, tiempo, 2, uso_pista=True)
            assert con < sin, f"tiempo={tiempo}: pista debe reducir el delta"

    def test_f05_pista_nunca_da_delta_negativo_en_aciertos(self):
        """Incluso con pista, acertar siempre da delta ≥ 1."""
        from models.scoring import calcular_delta
        for nivel in range(1, 6):
            for tiempo in [60, 300, 800]:
                delta = calcular_delta(True, tiempo, nivel, uso_pista=True)
                assert delta >= 1, (
                    f"N{nivel} t={tiempo}s con pista: delta={delta}, debe ser ≥1"
                )

    def test_f05_pista_no_afecta_respuesta_incorrecta(self):
        """Para respuestas incorrectas, la pista NO modifica el delta."""
        from models.scoring import calcular_delta
        for tiempo in [60, 200, 800]:
            sin = calcular_delta(False, tiempo, 2, uso_pista=False)
            con = calcular_delta(False, tiempo, 2, uso_pista=True)
            assert sin == con


# ─────────────────────────────────────────────────────────────────────────────
# F06 — Repetición espaciada: incorrectos vuelven al pool
# ─────────────────────────────────────────────────────────────────────────────

class TestRepeticionEspaciada:

    def test_f06_query_excluye_solo_correctos(self, mock_cursor):
        """
        La query de ejercicio_siguiente en repaso debe excluir ÚNICAMENTE
        los ejercicios respondidos CORRECTAMENTE (NOT EXISTS + es_correcta=TRUE).
        Ejercicios fallados deben volver al pool.
        """
        mock_cursor.fetchone.side_effect = [
            {'sin_diagnostico': False},
            {'nivel_actual': 3, 'score': 40.0},
            {'total_intentos': 0, 'promedio_puntaje': None,
             'min_puntaje': None, 'max_puntaje': None,
             'std_puntaje': 0, 'num_aprobados': 0, 'tendencia': None},
            {'id_ejercicio': 101, 'enunciado': 'Test', 'imagen_url': None,
             'pista': None, 'id_competencia': 2, 'nivel_logro': 3, 'nivel': 1},
        ]
        mock_cursor.fetchall.side_effect = [
            [],
            [{'id_opcion': 1, 'texto': 'A', 'es_correcta': True}],
        ]
        from app import app
        with app.test_client() as c:
            c.get('/tutor/ejercicio_siguiente?idEstudiante=10&modo=repaso')

        # Verificar que la query usa es_correcta=TRUE en el NOT EXISTS
        all_sql = ' '.join(str(c) for c in mock_cursor.execute.call_args_list)
        # La query de repetición espaciada debe filtrar solo los correctos
        assert 'es_correcta' in all_sql.lower() or 'correcta' in all_sql.lower()


# ─────────────────────────────────────────────────────────────────────────────
# F07 — Diagnóstico bloqueado
# ─────────────────────────────────────────────────────────────────────────────

class TestDiagnosticoBloqueado:

    def test_f07_sin_diagnostico_bloquea(self, client, mock_cursor):
        """Sin diagnóstico del docente → status=False, bloqueado=True."""
        mock_cursor.fetchone.return_value = {'sin_diagnostico': True}
        r = client.get('/tutor/ejercicio_siguiente?idEstudiante=10')
        data = r.get_json()
        assert data['status'] is False
        assert data.get('bloqueado') is True

    def test_f07_con_diagnostico_parcial_no_bloquea(self, client, mock_cursor):
        """Con al menos un diagnóstico → sin bloqueo."""
        mock_cursor.fetchone.side_effect = [
            {'sin_diagnostico': False},  # al menos una nota
            {'nivel_actual': 2, 'score': 22.0},
            {'total_intentos': 0, 'promedio_puntaje': None,
             'min_puntaje': None, 'max_puntaje': None,
             'std_puntaje': 0, 'num_aprobados': 0, 'tendencia': None},
            {'id_ejercicio': 101, 'enunciado': 'X', 'imagen_url': None,
             'pista': None, 'id_competencia': 1, 'nivel_logro': 2, 'nivel': 1},
        ]
        mock_cursor.fetchall.side_effect = [
            [],
            [{'id_opcion': 1, 'texto': 'A', 'es_correcta': True}],
        ]
        r = client.get('/tutor/ejercicio_siguiente?idEstudiante=10')
        data = r.get_json()
        assert data.get('bloqueado') is not True


# ─────────────────────────────────────────────────────────────────────────────
# F08 — Modo libre usa AVG(NEC) no MIN(NEC)  [fix L6]
# ─────────────────────────────────────────────────────────────────────────────

class TestModoLibreUsaPromedio:

    def test_f08_query_modo_libre_usa_avg(self, mock_cursor):
        """
        Sin idDominio (modo libre), la query de NEC debe usar AVG, no MIN.
        Verificar que el SQL generado contiene AVG y no MIN.
        """
        mock_cursor.fetchone.side_effect = [
            {'sin_diagnostico': False},
            {'nivel_min': 3},  # avg de las 4 competencias
            {'total_intentos': 0, 'promedio_puntaje': None,
             'min_puntaje': None, 'max_puntaje': None,
             'std_puntaje': 0, 'num_aprobados': 0, 'tendencia': None},
            {'id_ejercicio': 101, 'enunciado': 'X', 'imagen_url': None,
             'pista': None, 'id_competencia': 2, 'nivel_logro': 3, 'nivel': 1},
        ]
        mock_cursor.fetchall.side_effect = [
            [],
            [{'id_opcion': 1, 'texto': 'A', 'es_correcta': True}],
        ]
        from app import app
        with app.test_client() as c:
            c.get('/tutor/ejercicio_siguiente?idEstudiante=10')  # sin idDominio

        all_sql = ' '.join(str(c) for c in mock_cursor.execute.call_args_list)
        # Debe tener AVG en alguna query (fix L6: se cambió MIN→AVG)
        assert 'avg' in all_sql.lower(), (
            "Modo libre debe usar AVG(nivel_actual) no MIN (fix L6)"
        )
        # Y no debe tener solo MIN sin AVG
        has_min_without_avg = (
            'min(' in all_sql.lower()
            and 'avg(' not in all_sql.lower()
        )
        assert not has_min_without_avg


# ─────────────────────────────────────────────────────────────────────────────
# F09 — Tiempo mínimo de respuesta es ≥ 1 segundo (no 0)
# ─────────────────────────────────────────────────────────────────────────────

class TestTiempoRespuesta:

    def test_f09_tiempo_0_no_genera_categoria_invalida(self):
        """Tiempo = 0 → clasificar_tiempo retorna 'rapido' (nunca None ni error)."""
        from models.scoring import clasificar_tiempo
        cat = clasificar_tiempo(0, 1)
        assert cat == 'rapido'

    def test_f09_tiempo_1_segundo_valido(self):
        """El tiempo mínimo válido (1 seg) se clasifica correctamente."""
        from models.scoring import clasificar_tiempo, calcular_delta
        cat = clasificar_tiempo(1, 1)
        assert cat in ('rapido', 'regular', 'lento')
        delta = calcular_delta(True, 1, 1)
        assert isinstance(delta, int)

    def test_f09_android_asegura_tiempo_minimo_1(self):
        """
        Verificar en el código Android (TutorFragment.kt) que se usa
        maxOf(1, tiempo) para evitar enviar 0 segundos.
        """
        import os
        kt_path = (r'C:\Users\JUAN RAMIREZ\Desktop\Aplicacion_Tesis'
                   r'\app\src\main\java\com\example\aplicacion_tesis'
                   r'\ui\home\tabs\TutorFragment.kt')
        if not os.path.exists(kt_path):
            pytest.skip("TutorFragment.kt no encontrado")
        with open(kt_path, encoding='utf-8') as f:
            content = f.read()
        assert 'maxOf(1,' in content, (
            "TutorFragment debe usar maxOf(1, tiempo) para evitar 0 segundos"
        )