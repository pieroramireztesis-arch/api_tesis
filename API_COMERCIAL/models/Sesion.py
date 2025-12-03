from conexionBD import Conexion
import json

class Sesion():
    def __init__(self, correo=None, contrasena=None):
        self.correo = correo
        self.contrasena = contrasena

    def iniciarSesion(self):
        con = Conexion()
        cursor = con.cursor()
        try:
            # AHORA: unimos usuarios con docente (puede ser NULL si no es docente)
            sql = """
                SELECT 
                    u.id_usuario,
                    u.nombre,
                    u.apellidos,
                    u.correo,
                    u.rol,
                    u.estado_usuario,
                    d.id_docente
                FROM usuarios u
                LEFT JOIN docente d ON d.id_usuario = u.id_usuario
                WHERE u.correo = %s AND u.contrasena = %s
            """
            cursor.execute(sql, (self.correo, self.contrasena))
            datos = cursor.fetchone()

            if datos:
                if datos['estado_usuario'] == 'activo':
                    # datos ahora incluye: id_docente (puede ser None)
                    return json.dumps({
                        'status': True,
                        'data': datos,
                        'message': 'Inicio de sesión satisfactorio. Bienvenido al sistema'
                    })
                else:
                    return json.dumps({
                        'status': False,
                        'data': None,
                        'message': 'Cuenta inactiva. Consulte al administrador'
                    })
            else:
                return json.dumps({
                    'status': False,
                    'data': None,
                    'message': 'Credenciales incorrectas'
                })
        except Exception as e:
            return json.dumps({
                'status': False,
                'data': None,
                'message': str(e)
            })
        finally:
            cursor.close()
            con.close()
