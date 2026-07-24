"""
api/app/core/db.py
Capa de persistencia: engine, sesión y Base de SQLAlchemy 2.0.

Modo síncrono. Driver configurable por DATABASE_URL:
  - Desarrollo: SQLite (default, sin instalación).
  - Producción: PostgreSQL (cambiar DATABASE_URL).

init_db() crea las tablas al arranque SOLO en desarrollo.
En producción se usará Alembic (se introduce cuando el schema se congele).
"""

import logging
from pathlib import Path
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from api.app.core.config import settings


logger = logging.getLogger(__name__)


# ============================================================
# NORMALIZACIÓN DE LA URL DE SQLITE
# ============================================================

def _normalize_database_url(url: str) -> str:
    """
    Convierte una URL de SQLite relativa en absoluta para evitar
    dependencia del directorio de trabajo (cwd) de uvicorn.
    URLs de otros motores (postgresql, etc.) se dejan intactas.
    """
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        relative_path = url.replace("sqlite:///", "", 1)
        absolute_path = (Path.cwd() / relative_path).resolve()
        normalized = f"sqlite:///{absolute_path.as_posix()}"
        logger.info("SQLite normalizado a ruta absoluta: %s", absolute_path)
        return normalized
    return url


# ============================================================
# ENGINE
# ============================================================

_connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite requiere esto para funcionar con el threadpool de FastAPI.
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    _normalize_database_url(settings.DATABASE_URL),
    connect_args=_connect_args,
    pool_pre_ping=True,
    echo=False,
)


# ============================================================
# SESIÓN Y BASE
# ============================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """Base declarativa para todos los modelos ORM."""
    pass


# ============================================================
# DEPENDENCIA DE FASTAPI
# ============================================================

def get_db() -> Generator[Session, None, None]:
    """
    Dependencia que provee una sesión de DB por request
    y garantiza su cierre.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# INICIALIZACIÓN
# ============================================================

def init_db() -> None:
    """
    Crea todas las tablas definidas en los modelos.
    El import local de api.app.models registra los modelos en Base.metadata
    sin provocar import circular (db no importa models en tiempo de módulo).
    """
    import api.app.models  # noqa: F401  (registra modelos en metadata)

    Base.metadata.create_all(bind=engine)
    logger.info(
        "Tablas creadas/verificadas en: %s",
        _normalize_database_url(settings.DATABASE_URL),
    )


def check_db_connection() -> dict:
    """
    Verifica la conexión real a la DB ejecutando una query mínima.
    Retorna un dict con el estado. Lanza excepción si falla.
    """
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
        # Contar tenants sin importar el modelo aquí (evita acople):
        from api.app.models.tenant import Tenant
        tenant_count = session.query(Tenant).count()
    return {
        "connected": True,
        "engine": engine.url.drivername,
        "tenants": tenant_count,
    }