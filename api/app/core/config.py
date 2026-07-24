"""
api/app/core/config.py
Configuración de la API SaaS.
Lee desde variables de entorno o archivo .env.

NOTA DE ARQUITECTURA:
  DATABASE_URL por defecto apunta a SQLite (archivo local) para desarrollo,
  de modo que el sistema arranca sin instalar PostgreSQL ni Docker.
  En producción se sobrescribe con una URL de PostgreSQL vía variable de entorno:
    DATABASE_URL=postgresql://user:pass@host:5432/dbname
"""

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración de la API."""

    # --- Identidad ---
    PROJECT_NAME: str = "IA Curricular Engine API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"

    # --- Rutas ---
    # api/app/core/config.py -> parents[3] = raíz del proyecto
    PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]

    # --- CORS ---
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # --- Base de datos ---
    # Default: SQLite en la raíz del proyecto (desarrollo, cero instalación).
    DATABASE_URL: str = "sqlite:///./ia_curricular_dev.db"

    # --- Seguridad (auth se implementa en el siguiente bloque) ---
    SECRET_KEY: str = "change-me-in-production-please-32+chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
    }


settings = Settings()