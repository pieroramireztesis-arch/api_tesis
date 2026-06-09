# API_COMERCIAL/config.py
import os
from dotenv import load_dotenv

# Carga el .env si existe (local dev). En Railway, las vars ya están en el entorno.
load_dotenv()

class Config:
    """
    Configuración para la BD.
    Railway inyecta DATABASE_URL automáticamente (ver conexionBD.py).
    En local usa los parámetros separados como fallback.
    """
    DB_HOST     = os.getenv("PGHOST",     "127.0.0.1")
    DB_PORT     = os.getenv("PGPORT",     "5432")
    DB_USER     = os.getenv("PGUSER",     "postgres")
    DB_PASSWORD = os.getenv("PGPASSWORD", "hola1")
    DB_NAME     = os.getenv("PGDATABASE", "bd_ejemplo")


class SecretKey:
    # ⚠️  En producción (Railway) define JWT_SECRET_KEY con un valor largo y aleatorio.
    #     Con el default de desarrollo los tokens pueden ser forjados si alguien lo conoce.
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-jwt-tutormath2026-CHANGE-IN-PROD")


class Host:
    URL_APP = os.getenv("URL_APP", "http://127.0.0.1:3008/")
