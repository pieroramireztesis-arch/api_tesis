-- ============================================================
-- FICHAS MATEMÁTICA 3 — Limpieza + palabras_clave + materiales
-- STI de Álgebra — Tesis universitaria
-- Fecha: 2026-05-28
-- Ejecutar en: bd_ejemplo (PostgreSQL, puerto 5432)
-- ============================================================

BEGIN;

-- ────────────────────────────────────────────────────────────
-- FASE 1: ELIMINAR materiales de prueba (todos genéricos)
-- ────────────────────────────────────────────────────────────
DELETE FROM material_estudio WHERE id_ejercicio IS NULL;

-- ────────────────────────────────────────────────────────────
-- FASE 2: PALABRAS CLAVE para búsquedas de recursos
-- ────────────────────────────────────────────────────────────

-- Competencia 1 — Interés Simple (ejr 106–110)
UPDATE ejercicios SET palabras_clave = 'interés simple bono porcentaje capital'                   WHERE id_ejercicio = 106;
UPDATE ejercicios SET palabras_clave = 'interés simple préstamo ganancia capital tasa'            WHERE id_ejercicio = 107;
UPDATE ejercicios SET palabras_clave = 'interés simple límites tolerancia porcentaje'             WHERE id_ejercicio = 108;
UPDATE ejercicios SET palabras_clave = 'interés simple fórmula despejar tiempo tasa anual'       WHERE id_ejercicio = 109;
UPDATE ejercicios SET palabras_clave = 'interés simple cuotas precio crédito mensual'            WHERE id_ejercicio = 110;

-- Competencia 2 — Progresión Geométrica (ejr 111–113) e Inecuaciones (ejr 114–115)
UPDATE ejercicios SET palabras_clave = 'progresión geométrica razón sucesión término ajedrez'    WHERE id_ejercicio = 111;
UPDATE ejercicios SET palabras_clave = 'progresión geométrica bacterias crecimiento exponencial' WHERE id_ejercicio = 112;
UPDATE ejercicios SET palabras_clave = 'progresión geométrica fórmula término enésimo razón'     WHERE id_ejercicio = 113;
UPDATE ejercicios SET palabras_clave = 'inecuaciones lineal desigualdad solución conjunto'       WHERE id_ejercicio = 114;
UPDATE ejercicios SET palabras_clave = 'inecuaciones problema aplicación obreros restricciones'  WHERE id_ejercicio = 115;

-- Competencia 3 — Transformaciones Geométricas (ejr 116–117), Homotecia (118), Semejanza (119–120)
UPDATE ejercicios SET palabras_clave = 'reflexión simetría espejo transformación geométrica'                WHERE id_ejercicio = 116;
UPDATE ejercicios SET palabras_clave = 'transformaciones geométricas traslación rotación reflexión'         WHERE id_ejercicio = 117;
UPDATE ejercicios SET palabras_clave = 'homotecia ampliación reducción escala fotocopiadora'               WHERE id_ejercicio = 118;
UPDATE ejercicios SET palabras_clave = 'semejanza triángulos escala proporción construcción'               WHERE id_ejercicio = 119;
UPDATE ejercicios SET palabras_clave = 'semejanza congruencia triángulos criterios proporcionalidad'       WHERE id_ejercicio = 120;

-- Competencia 4 — Estadística (ejr 121–122) y Probabilidad (ejr 123–125)
UPDATE ejercicios SET palabras_clave = 'gráfico circular porcentaje interpretar estadística datos'          WHERE id_ejercicio = 121;
UPDATE ejercicios SET palabras_clave = 'medidas dispersión rango varianza desviación estándar'              WHERE id_ejercicio = 122;
UPDATE ejercicios SET palabras_clave = 'probabilidad espacio muestral eventos frecuencia relativa'          WHERE id_ejercicio = 123;
UPDATE ejercicios SET palabras_clave = 'probabilidad condicional evento independiente deporte'              WHERE id_ejercicio = 124;
UPDATE ejercicios SET palabras_clave = 'probabilidad monedas espacio muestral combinaciones'                WHERE id_ejercicio = 125;

-- ────────────────────────────────────────────────────────────
-- FASE 3: MATERIALES REALES vinculados por id_ejercicio
-- 2 materiales por ejercicio: video (YouTube Search) + link (Khan Academy)
-- ────────────────────────────────────────────────────────────

-- ══ COMPETENCIA 1: INTERÉS SIMPLE ════════════════════════════

-- ejr 106 — Patricia, bono laboral
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Interés Simple: fórmula I=C·r·t y ejercicios', 'video',
 'https://www.youtube.com/results?search_query=interes+simple+formula+ejercicios+resueltos+secundaria',
 1, 106, 1),
('Interés simple – Khan Academy', 'link',
 'https://es.khanacademy.org/math/cc-seventh-grade-math/cc-7th-ratio-proportion/cc-7th-interest/v/introduction-to-interest',
 1, 106, 1);

-- ejr 107 — Sebastián, préstamo de capital
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Calcular ganancia con Interés Simple', 'video',
 'https://www.youtube.com/results?search_query=interes+simple+calcular+ganancia+prestamo+capital',
 1, 107, 1),
('Problemas de interés simple – Khan Academy', 'link',
 'https://es.khanacademy.org/math/cc-seventh-grade-math/cc-7th-ratio-proportion/cc-7th-interest',
 1, 107, 1);

-- ejr 108 — Límites de tolerancia y porcentajes
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Interés Simple con porcentajes: aplicaciones', 'video',
 'https://www.youtube.com/results?search_query=interes+simple+porcentaje+aplicaciones+limites',
 1, 108, 1),
('Porcentajes e interés simple – Khan Academy', 'link',
 'https://es.khanacademy.org/math/cc-seventh-grade-math/cc-7th-ratio-proportion/cc-7th-interest',
 1, 108, 1);

-- ejr 109 — Inmobiliaria, despejar el tiempo
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Interés Simple: despejar el tiempo (t)', 'video',
 'https://www.youtube.com/results?search_query=interes+simple+despejar+tiempo+ejercicios+resueltos',
 1, 109, 1),
('Despejar variables en interés simple – Khan Academy', 'link',
 'https://es.khanacademy.org/math/cc-seventh-grade-math/cc-7th-ratio-proportion/cc-7th-interest',
 1, 109, 1);

-- ejr 110 — Cámara digital, cuotas y precio final
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Interés Simple: calcular cuotas mensuales', 'video',
 'https://www.youtube.com/results?search_query=interes+simple+cuotas+mensuales+credito+precio+final',
 1, 110, 1),
('Aplicaciones del interés simple – Khan Academy', 'link',
 'https://es.khanacademy.org/math/cc-seventh-grade-math/cc-7th-ratio-proportion/cc-7th-interest',
 1, 110, 1);

-- ══ COMPETENCIA 2: PROGRESIÓN GEOMÉTRICA E INECUACIONES ══════

-- ejr 111 — Ajedrez, razón de la progresión
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Progresión Geométrica: razón y primeros términos', 'video',
 'https://www.youtube.com/results?search_query=progresion+geometrica+razon+terminos+ejercicios+secundaria',
 2, 111, 1),
('Introducción a sucesiones geométricas – Khan Academy', 'link',
 'https://es.khanacademy.org/math/algebra/x2f8bb11595b61c86:sequences/x2f8bb11595b61c86:introduction-to-geometric-sequences/v/geometric-sequences-introduction',
 2, 111, 1);

-- ejr 112 — Bacterias, crecimiento exponencial
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Progresión Geométrica: crecimiento exponencial', 'video',
 'https://www.youtube.com/results?search_query=progresion+geometrica+crecimiento+exponencial+bacterias+ejercicios',
 2, 112, 1),
('Crecimiento geométrico exponencial – Khan Academy', 'link',
 'https://es.khanacademy.org/math/algebra/x2f8bb11595b61c86:sequences/x2f8bb11595b61c86:introduction-to-geometric-sequences',
 2, 112, 1);

-- ejr 113 — Encontrar el término enésimo
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Fórmula del n-ésimo término en Progresión Geométrica', 'video',
 'https://www.youtube.com/results?search_query=formula+termino+enesimo+progresion+geometrica+ejercicios',
 2, 113, 1),
('Fórmula explícita de sucesiones geométricas – Khan Academy', 'link',
 'https://es.khanacademy.org/math/algebra/x2f8bb11595b61c86:sequences/x2f8bb11595b61c86:constructing-geometric-sequences',
 2, 113, 1);

-- ejr 114 — Diana, inecuaciones lineales
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Inecuaciones lineales: resolver paso a paso', 'video',
 'https://www.youtube.com/results?search_query=inecuaciones+lineales+resolver+paso+a+paso+secundaria',
 2, 114, 1),
('Inecuaciones lineales – Khan Academy', 'link',
 'https://es.khanacademy.org/math/algebra/x2f8bb11595b61c86:solving-equations-inequalities/x2f8bb11595b61c86:linear-inequalities/v/inequalities',
 2, 114, 1);

-- ejr 115 — Obreros, inecuaciones aplicadas
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Inecuaciones: problemas de aplicación con contexto', 'video',
 'https://www.youtube.com/results?search_query=inecuaciones+problemas+aplicacion+contexto+real+secundaria',
 2, 115, 1),
('Modelar situaciones con inecuaciones – Khan Academy', 'link',
 'https://es.khanacademy.org/math/algebra/x2f8bb11595b61c86:solving-equations-inequalities/x2f8bb11595b61c86:linear-inequalities',
 2, 115, 1);

-- ══ COMPETENCIA 3: TRANSFORMACIONES GEOMÉTRICAS Y SEMEJANZA ══

-- ejr 116 — Espejo plano, reflexión
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Reflexión geométrica: simetría y espejo plano', 'video',
 'https://www.youtube.com/results?search_query=reflexion+geometrica+simetria+espejo+plano+ejemplos',
 3, 116, 1),
('Reflexiones en geometría – Khan Academy', 'link',
 'https://es.khanacademy.org/math/geometry/hs-geo-transformations/hs-geo-reflections/v/reflecting-segment-over-line',
 3, 116, 1);

-- ejr 117 — Identificar tipo de transformación
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Transformaciones: traslación, rotación y reflexión', 'video',
 'https://www.youtube.com/results?search_query=tipos+transformaciones+geometricas+traslacion+rotacion+reflexion+secundaria',
 3, 117, 1),
('Intro a las transformaciones rígidas – Khan Academy', 'link',
 'https://es.khanacademy.org/math/geometry/hs-geo-transformations/hs-geo-intro-euclid/v/language-and-notation-of-basic-geometry',
 3, 117, 1);

-- ejr 118 — Fotocopiadora, homotecia
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Homotecia: ampliación y reducción con escala', 'video',
 'https://www.youtube.com/results?search_query=homotecia+ampliacion+reduccion+escala+ejercicios+resueltos',
 3, 118, 1),
('Dilataciones (homotecia) – Khan Academy', 'link',
 'https://es.khanacademy.org/math/geometry/hs-geo-transformations/hs-geo-dilations/v/scaling-down-a-triangle-by-half',
 3, 118, 1);

-- ejr 119 — Puente, semejanza de triángulos
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Semejanza de triángulos: escala y proporciones', 'video',
 'https://www.youtube.com/results?search_query=semejanza+triangulos+escala+proporcion+ejercicios+secundaria',
 3, 119, 1),
('Semejanza de triángulos – Khan Academy', 'link',
 'https://es.khanacademy.org/math/geometry/hs-geo-similarity/hs-geo-triangle-similarity-intro/v/similar-triangles-1',
 3, 119, 1);

-- ejr 120 — Palmeras, semejanza y congruencia
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Semejanza y Congruencia: diferencias y criterios', 'video',
 'https://www.youtube.com/results?search_query=semejanza+congruencia+triangulos+diferencias+criterios+secundaria',
 3, 120, 1),
('Criterios de semejanza de triángulos – Khan Academy', 'link',
 'https://es.khanacademy.org/math/geometry/hs-geo-similarity/hs-geo-triangle-similarity-intro',
 3, 120, 1);

-- ══ COMPETENCIA 4: ESTADÍSTICA Y PROBABILIDAD ════════════════

-- ejr 121 — Gráfico circular, color de ojos
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Cómo interpretar gráficos circulares', 'video',
 'https://www.youtube.com/results?search_query=interpretar+grafico+circular+estadistica+porcentaje+ejercicios',
 4, 121, 1),
('Leer gráficos circulares – Khan Academy', 'link',
 'https://es.khanacademy.org/math/statistics-probability/displaying-describing-data/displays-of-distributions/v/reading-pie-graphs',
 4, 121, 1);

-- ejr 122 — Evaluaciones, medidas de dispersión
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Rango, varianza y desviación estándar: paso a paso', 'video',
 'https://www.youtube.com/results?search_query=medidas+dispersion+rango+varianza+desviacion+estandar+secundaria',
 4, 122, 1),
('Varianza y desviación estándar – Khan Academy', 'link',
 'https://es.khanacademy.org/math/statistics-probability/summarizing-quantitative-data/variance-standard-deviation-population/v/range-variance-and-standard-deviation-as-measures-of-dispersion',
 4, 122, 1);

-- ejr 123 — Debate, probabilidad básica
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Probabilidad: espacio muestral y eventos', 'video',
 'https://www.youtube.com/results?search_query=probabilidad+espacio+muestral+eventos+ejercicios+secundaria',
 4, 123, 1),
('Probabilidad básica – Khan Academy', 'link',
 'https://es.khanacademy.org/math/statistics-probability/probability-library/basic-theoretical-probability/v/basic-probability',
 4, 123, 1);

-- ejr 124 — Deporte, probabilidad condicional
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Probabilidad condicional: eventos dependientes', 'video',
 'https://www.youtube.com/results?search_query=probabilidad+condicional+eventos+dependientes+independientes+ejercicios',
 4, 124, 1),
('Probabilidad condicional – Khan Academy', 'link',
 'https://es.khanacademy.org/math/statistics-probability/probability-library/conditional-probability-independence/v/calculating-conditional-probability',
 4, 124, 1);

-- ejr 125 — Monedas, espacio muestral
INSERT INTO material_estudio (titulo, tipo, url, id_competencia, id_ejercicio, nivel) VALUES
('Probabilidad con monedas: caras y sellos', 'video',
 'https://www.youtube.com/results?search_query=probabilidad+monedas+caras+sello+espacio+muestral+ejercicios',
 4, 125, 1),
('Probabilidad con monedas – Khan Academy', 'link',
 'https://es.khanacademy.org/math/statistics-probability/probability-library/basic-theoretical-probability/v/basic-probability',
 4, 125, 1);

COMMIT;

-- ────────────────────────────────────────────────────────────
-- VERIFICACIÓN FINAL
-- ────────────────────────────────────────────────────────────
SELECT
  e.id_ejercicio,
  e.id_competencia,
  CASE WHEN e.palabras_clave IS NOT NULL THEN 'SI' ELSE 'NO' END AS tiene_kw,
  e.palabras_clave,
  COUNT(m.id_material) AS materiales
FROM ejercicios e
LEFT JOIN material_estudio m ON m.id_ejercicio = e.id_ejercicio
GROUP BY e.id_ejercicio, e.id_competencia, e.palabras_clave
ORDER BY e.id_competencia, e.id_ejercicio;
