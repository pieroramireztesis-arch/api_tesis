from flask import Flask
from flask_jwt_extended import JWTManager
from config import SecretKey



from ws.estudiante import ws_estudiante
from ws.usuario import ws_usuario
from ws.docente import ws_docente
from ws.ejercicio import ws_ejercicio
from ws.competencia import ws_competencia
from ws.respuesta import ws_respuesta
from ws.puntaje import ws_puntaje
from ws.historial_material import ws_historial_material
from ws.nivel import ws_nivel
from ws.material_estudio import ws_material
from ws.salon import ws_salon
from ws.docente_salon import ws_docente_salon
from ws.estudiante_salon import ws_estudiante_salon
from ws.progreso import ws_progreso
from ws.recomendacion import ws_recomendacion
from ws.tutor import ws_tutor
from ws.dashboard import ws_dashboard
from ws.auth import ws_auth
from ws.dominio import ws_dominio

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = SecretKey.JWT_SECRET_KEY
jwt = JWTManager(app)


app.register_blueprint(ws_estudiante)
app.register_blueprint(ws_usuario)
app.register_blueprint(ws_docente)
app.register_blueprint(ws_ejercicio)
app.register_blueprint(ws_competencia)
app.register_blueprint(ws_respuesta)
app.register_blueprint(ws_puntaje)
app.register_blueprint(ws_historial_material)
app.register_blueprint(ws_nivel)
app.register_blueprint(ws_material)
app.register_blueprint(ws_salon)
app.register_blueprint(ws_docente_salon)
app.register_blueprint(ws_estudiante_salon)
app.register_blueprint(ws_progreso)
app.register_blueprint(ws_recomendacion)
app.register_blueprint(ws_tutor)
app.register_blueprint(ws_dashboard)
app.register_blueprint(ws_auth)
app.register_blueprint(ws_dominio)


@app.route('/')
def home():
    return 'API del Sistema de Aprendizaje en Ejecución'

if __name__ == '__main__':
    # Solo para tu PC
    app.run(port=3008, debug=True, host='0.0.0.0')

