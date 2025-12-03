# API_RESTFUL/seed_usuarios_iniciales.py

from werkzeug.security import generate_password_hash
from conexionBD import Conexion


def crear_docentes_y_salones(cur, salones):
    """
    Crea docentes de prueba y los asigna a salones.
    salones: dict { '3ro A': id_salon, ... }
    """
    docentes_data = [
        # nombre, apellidos, correo, especialidad, salones_asignados
        ("María", "Gonzales López", "maria.gonzales@colegio.edu.pe", "Matemática", ["3ro A"]),
        ("Juan", "Pérez Ramos", "juan.perez@colegio.edu.pe", "Matemática", ["3ro B", "3ro C"]),
    ]

    ids_docentes = []

    for nombre, apellidos, correo, especialidad, salones_asignados in docentes_data:
        password_hash = generate_password_hash("docente123")

        # Insertar en usuarios
        cur.execute(
            """
            INSERT INTO usuarios (nombre, apellidos, correo, contrasena, rol)
            VALUES (%s, %s, %s, %s, 'docente')
            RETURNING id_usuario;
            """,
            (nombre, apellidos, correo, password_hash),
        )
        row_usuario = cur.fetchone()
        id_usuario = row_usuario["id_usuario"]

        # Insertar en docente
        cur.execute(
            """
            INSERT INTO docente (especialidad, id_usuario)
            VALUES (%s, %s)
            RETURNING id_docente;
            """,
            (especialidad, id_usuario),
        )
        row_docente = cur.fetchone()
        id_docente = row_docente["id_docente"]
        ids_docentes.append(id_docente)

        # Asignar salones a docente
        for nombre_salon in salones_asignados:
            id_salon = salones.get(nombre_salon)
            if id_salon:
                cur.execute(
                    """
                    INSERT INTO docente_salones (id_docente, id_salon)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    (id_docente, id_salon),
                )

    return ids_docentes


def crear_estudiantes(cur, salones):
    """
    Crea estudiantes de prueba y los asigna a 3ro A, 3ro B y 3ro C.
    """
    estudiantes_data = [
        # nombre, apellidos, correo, salon
        ("Ana", "Rodríguez Silva", "ana.rodriguez@alumno.edu.pe", "3ro A"),
        ("Luis", "Ramírez Torres", "luis.ramirez@alumno.edu.pe", "3ro A"),
        ("Sofía", "Vásquez León", "sofia.vasquez@alumno.edu.pe", "3ro A"),

        ("Carlos", "Chávez Díaz", "carlos.chavez@alumno.edu.pe", "3ro B"),
        ("Valeria", "Mendoza Ruiz", "valeria.mendoza@alumno.edu.pe", "3ro B"),
        ("Diego", "Flores Campos", "diego.flores@alumno.edu.pe", "3ro B"),

        ("Piero", "Ramírez Chávez", "piero.ramirez@alumno.edu.pe", "3ro C"),
        ("Camila", "Sánchez Poma", "camila.sanchez@alumno.edu.pe", "3ro C"),
        ("Mateo", "Huamán Ríos", "mateo.huaman@alumno.edu.pe", "3ro C"),
    ]

    for nombre, apellidos, correo, nombre_salon in estudiantes_data:
        password_hash = generate_password_hash("alumno123")

        # Insertar en usuarios
        cur.execute(
            """
            INSERT INTO usuarios (nombre, apellidos, correo, contrasena, rol)
            VALUES (%s, %s, %s, %s, 'estudiante')
            RETURNING id_usuario;
            """,
            (nombre, apellidos, correo, password_hash),
        )
        row_usuario = cur.fetchone()
        id_usuario = row_usuario["id_usuario"]

        # Insertar en estudiante
        cur.execute(
            """
            INSERT INTO estudiante (grado, id_usuario)
            VALUES (%s, %s)
            RETURNING id_estudiante;
            """,
            ("3ro", id_usuario),
        )
        row_est = cur.fetchone()
        id_estudiante = row_est["id_estudiante"]

        # Asignar a salón
        id_salon = salones.get(nombre_salon)
        if id_salon:
            cur.execute(
                """
                INSERT INTO estudiante_salones (id_estudiante, id_salon)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (id_estudiante, id_salon),
            )


def obtener_salones(cur):
    """
    Retorna un dict con los salones existentes:
    { '3ro A': id_salon, '3ro B': id_salon, '3ro C': id_salon }
    """
    cur.execute("SELECT id_salon, nombre_salon FROM salones;")
    rows = cur.fetchall()

    salones = {}
    for row in rows:
        salones[row["nombre_salon"]] = row["id_salon"]

    return salones


def main():
    conn = Conexion()
    cur = conn.cursor()

    try:
        # 1. Obtener salones (asumimos que ya se ejecutó el reset y están 3ro A, B, C)
        salones = obtener_salones(cur)
        if not salones:
            raise RuntimeError("No hay salones registrados. Asegúrate de haber ejecutado el script de reset.")

        # 2. Crear docentes y asignarlos a salones
        crear_docentes_y_salones(cur, salones)

        # 3. Crear estudiantes y asignarlos a salones
        crear_estudiantes(cur, salones)

        conn.commit()
        print("✅ Seed de docentes y estudiantes completado correctamente.")

    except Exception as e:
        conn.rollback()
        print("❌ Error durante el seed:", str(e))

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
