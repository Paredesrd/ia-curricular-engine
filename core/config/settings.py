"""
config/settings.py
Configuración centralizada del sistema.
Todos los parámetros globales, rutas, logging y constantes del motor.
"""
import logging
import sys
from pathlib import Path

from pydantic import BaseModel, Field

# ============================================================
# RUTAS DEL PROYECTO
# ============================================================
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DOMAIN_DIR: Path = PROJECT_ROOT / "domain"
AGENTS_DIR: Path = PROJECT_ROOT / "agents"
CONFIG_DIR: Path = PROJECT_ROOT / "config"
TESTS_DIR: Path = PROJECT_ROOT / "tests"
OUTPUT_DIR: Path = PROJECT_ROOT / "output"


# ============================================================
# CONFIGURACIÓN DEL SISTEMA
# ============================================================
class Settings(BaseModel):
    """
    Configuración global del motor de IA curricular.
    Inmutable en tiempo de ejecución.
    """

    # --- Identidad del sistema ---
    system_name: str = Field(
        default="IA Curricular Engine",
        description="Nombre del sistema",
    )
    version: str = Field(
        default="0.1.0",
        description="Versión del sistema",
    )
    environment: str = Field(
        default="development",
        pattern="^(development|staging|production)$",
        description="Entorno de ejecución",
    )

    # --- Logging ---
    log_level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Nivel de logging",
    )
    log_format: str = Field(
        default="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        description="Formato de los mensajes de log",
    )
    log_date_format: str = Field(
        default="%Y-%m-%d %H:%M:%S",
        description="Formato de fecha en logs",
    )

    # --- Parámetros de los agentes ---
    max_retries_per_agent: int = Field(
        default=3,
        ge=1,
        le=10,
        description=(
            "Máximo de intentos del par Arquitecto+Auditor antes de dar "
            "el curso por no aprobable."
        ),
    )
    agent_timeout_seconds: int = Field(
        default=300,
        ge=30,
        description=(
            "Reserva de timeout por agente. Hoy los agentes son deterministas "
            "y rápidos, por lo que no se aplica un watchdog; se usará al "
            "integrar un LLM (Fase 2)."
        ),
    )

    # --- Parámetros curriculares por defecto ---
    default_min_hours_per_lesson: float = Field(
        default=0.5,
        gt=0,
        description="Horas mínimas por lección si el Tenant no especifica",
    )
    default_max_hours_per_lesson: float = Field(
        default=4.0,
        gt=0,
        description="Horas máximas por lección si el Tenant no especifica",
    )
    max_modules: int = Field(
        default=12,
        ge=1,
        le=30,
        description="Límite superior de módulos por curso (tope de seguridad).",
    )

    # --- Output ---
    output_encoding: str = Field(
        default="utf-8",
        description="Codificación de archivos de salida",
    )


# ============================================================
# SINGLETON DE CONFIGURACIÓN
# ============================================================
_settings_instance: Settings | None = None


def get_settings() -> Settings:
    """
    Retorna la instancia única de configuración (patrón Singleton).
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


# ============================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================
def setup_logging() -> logging.Logger:
    """
    Configura y retorna el logger raíz del sistema.
    Se llama UNA sola vez al arrancar el motor.
    """
    settings = get_settings()
    logger = logging.getLogger(settings.system_name)
    logger.setLevel(getattr(logging, settings.log_level))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, settings.log_level))
        formatter = logging.Formatter(
            fmt=settings.log_format,
            datefmt=settings.log_date_format,
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger