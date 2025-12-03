import os
import psycopg2
import psycopg2.extras


class Config:
    # Para Render: usa DATABASE_URL
    DATABASE_URL = os.environ.get("DATABASE_URL")

    # Para tu PC local: usa estos valores
    DB_HOST = "127.0.0.1"
    DB_PORT = 5432
    DB_USER = "postgres"
    DB_PASSWORD = "hola1"
    DB_NAME = "bd_ejemplo"


class SecretKey:
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "claveSuperSecreta2025")


class Host:
    # URL base donde corre tu API Flask
    URL_APP = os.environ.get("URL_APP", "http://127.0.0.1:3008")


def _build_local_conn():
    """
    Conexión para tu máquina local, usando host/puerto/usuario/etc.
    """
    return psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        dbname=Config.DB_NAME,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def _build_render_conn():
    """
    Conexión para Render, usando DATABASE_URL con SSL.
    """
    if not Config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL no está configurada")

    # En Render se requiere sslmode='require'
    return psycopg2.connect(
        Config.DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor,
        sslmode="require",
    )


def get_db():
    """
    Conexión para scripts externos (entrenamiento, etc.)
    """
    # Si hay DATABASE_URL → Render
    if Config.DATABASE_URL:
        return _build_render_conn()
    # Si no → conexión local
    return _build_local_conn()


class Conexion:
    """
    Conexión usada internamente en todos tus blueprints.
    """

    def __init__(self):
        if Config.DATABASE_URL:
            self.dblink = _build_render_conn()
        else:
            self.dblink = _build_local_conn()

    def cursor(self):
        return self.dblink.cursor()

    def commit(self):
        self.dblink.commit()

    def rollback(self):
        self.dblink.rollback()

    def close(self):
        self.dblink.close()
