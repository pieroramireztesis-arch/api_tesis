from conexionBD import Conexion
import json

class Docente:
    def __init__(self, id_docente=None, especialidad=None, id_usuario=None):
        self.id_docente = id_docente
        self.especialidad = especialidad
        self.id_usuario = id_usuario

    # Crear docente
    def crear(self):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                INSERT INTO docente (especialidad, id_usuario)
                VALUES (%s, %s) RETURNING id_docente;
            """
            cursor.execute(sql, (self.especialidad, self.id_usuario))
            nuevo_id = cursor.fetchone()['id_docente']
            con.commit()
            return json.dumps({'status': True, 'id_docente': nuevo_id, 'message': 'Docente creado'})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

    # Listar docentes
    @staticmethod
    def listar():
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                SELECT d.id_docente, u.nombre, u.apellidos, u.correo, d.especialidad, u.estado_usuario
                FROM docente d
                JOIN usuarios u ON d.id_usuario = u.id_usuario
                WHERE u.rol = 'docente';
            """
            cursor.execute(sql)
            datos = cursor.fetchall()
            return json.dumps({'status': True, 'data': datos})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

    # Obtener docente por id
    @staticmethod
    def obtener(id_docente):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                SELECT d.id_docente, u.nombre, u.apellidos, u.correo, d.especialidad, u.estado_usuario
                FROM docente d
                JOIN usuarios u ON d.id_usuario = u.id_usuario
                WHERE d.id_docente = %s;
            """
            cursor.execute(sql, (id_docente,))
            datos = cursor.fetchone()
            if datos:
                return json.dumps({'status': True, 'data': datos})
            else:
                return json.dumps({'status': False, 'message': 'Docente no encontrado'})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

    # Actualizar docente
    def actualizar(self):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = """
                UPDATE docente
                SET especialidad = %s
                WHERE id_docente = %s;
            """
            cursor.execute(sql, (self.especialidad, self.id_docente))
            con.commit()
            return json.dumps({'status': True, 'message': 'Docente actualizado'})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

    # Eliminar docente
    @staticmethod
    def eliminar(id_docente):
        con = Conexion()
        cursor = con.cursor()
        try:
            sql = "DELETE FROM docente WHERE id_docente = %s;"
            cursor.execute(sql, (id_docente,))
            con.commit()
            return json.dumps({'status': True, 'message': 'Docente eliminado'})
        except Exception as e:
            return json.dumps({'status': False, 'message': str(e)})
        finally:
            cursor.close()
            con.close()

  

    # ===============================
    # Dashboard del docente
    # ===============================
    @staticmethod
    def dashboard(id_docente):
        con = Conexion()
        cursor = con.cursor()
        try:
            # 1. Salones asignados
            cursor.execute("""
                SELECT id_salon
                FROM docente_salones
                WHERE id_docente = %s
            """, (id_docente,))
            salones = cursor.fetchall()

            if not salones:
                return json.dumps({
                    "status": True,
                    "data": {
                        "estudiantesActivos": 0,
                        "progresoPromedio": 0,
                        "temaMasDificultad": None,
                        "actividadReciente": []
                    }
                })

            ids_salones = [s["id_salon"] for s in salones]

            # 2. Estudiantes del salón
            cursor.execute("""
                SELECT e.id_estudiante, e.progreso_general, e.estado_estudiante
                FROM estudiante e
                JOIN estudiante_salones es ON e.id_estudiante = es.id_estudiante
                WHERE es.id_salon = ANY(%s)
            """, (ids_salones,))
            estudiantes = cursor.fetchall()

            if not estudiantes:
                return json.dumps({
                    "status": True,
                    "data": {
                        "estudiantesActivos": 0,
                        "progresoPromedio": 0,
                        "temaMasDificultad": None,
                        "actividadReciente": []
                    }
                })

            ids_estudiantes = [e["id_estudiante"] for e in estudiantes]

            # 3. Estudiantes activos
            estudiantes_activos = sum(1 for e in estudiantes if e["estado_estudiante"] == "activo")

            # 4. Progreso promedio
            progresos = [e["progreso_general"] for e in estudiantes if e["progreso_general"] is not None]
            progreso_promedio = round(sum(progresos) / len(progresos), 1) if progresos else 0

            # 5. Tema con más dificultad
            cursor.execute("""
                SELECT c.descripcion, AVG(p.puntaje) AS promedio
                FROM puntajes p
                JOIN competencias c ON p.id_competencia = c.id_competencia
                WHERE p.id_estudiante = ANY(%s)
                GROUP BY c.descripcion
                ORDER BY promedio ASC
                LIMIT 1
            """, (ids_estudiantes,))
            dificultad = cursor.fetchone()
            tema_mas_dificultad = dificultad["descripcion"] if dificultad else None

            # 6. Actividad reciente
            cursor.execute("""
                SELECT pr.fecha, pr.estado, u.nombre, u.apellidos, c.descripcion AS tema
                FROM progreso pr
                JOIN estudiante e ON e.id_estudiante = pr.id_estudiante
                JOIN usuarios u ON u.id_usuario = e.id_usuario
                JOIN ejercicios ej ON ej.id_ejercicio = pr.id_ejercicio
                JOIN competencias c ON c.id_competencia = ej.id_competencia
                WHERE pr.id_estudiante = ANY(%s)
                ORDER BY pr.fecha DESC
                LIMIT 10
            """, (ids_estudiantes,))
            filas = cursor.fetchall()

            actividad = []
            for f in filas:
                actividad.append({
                    "tipo": "completado" if f["estado"] == "completado" else "progreso",
                    "nombreEstudiante": f"{f['nombre']} {f['apellidos']}",
                    "tema": f["tema"],
                    "fecha": f["fecha"].isoformat() if f["fecha"] else None
                })

            # JSON FINAL COMPATIBLE
            return json.dumps({
                "status": True,
                "data": {
                    "estudiantesActivos": estudiantes_activos,
                    "progresoPromedio": progreso_promedio,
                    "temaMasDificultad": tema_mas_dificultad,
                    "actividadReciente": actividad
                }
            })

        except Exception as e:
            return json.dumps({"status": False, "message": str(e)})
        finally:
            cursor.close()
            con.close()
