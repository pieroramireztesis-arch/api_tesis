# API_COMERCIAL/config.py
import os

class Config:
    """
    Configuración para la BD.
    En Render, tomamos los datos desde variables de entorno.
    En local, puedes poner valores por defecto.
    """

    # En Render: se leen de las env vars PGHOST, PGUSER, etc.
    # En local: usa los valores por defecto (para tus pruebas en tu PC).
    DB_HOST = os.getenv("PGHOST", "127.0.0.1")
    DB_PORT = os.getenv("PGPORT", "5432")
    DB_USER = os.getenv("PGUSER", "postgres")
    DB_PASSWORD = os.getenv("PGPASSWORD", "hola1")
    DB_NAME = os.getenv("PGDATABASE", "bd_ejemplo")


class SecretKey:
    JWT_SECRET_KEY = "claveSuperSecreta2025"


class Host:
    # Para que otras partes sepan dónde corre la API
    URL_APP = os.getenv("URL_APP", "http://127.0.0.1:3008/")
