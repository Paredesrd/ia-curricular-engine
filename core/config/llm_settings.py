"""
core/config/llm_settings.py
Configuración del proveedor de LLM, AISLADA de la config del motor.

Función única: leer las credenciales/parámetros del modelo desde variables de
entorno (o .env en la raíz del proyecto). El motor (config/settings.py) no sabe
nada del LLM; así cambiar de proveedor o de modelo nunca toca al motor.

Variables (ponlas en el .env de la raíz):
    LLM_PROVIDER   = openai            (hoy solo "openai"; el puerto permite más)
    LLM_MODEL      = gpt-4o-mini
    LLM_API_KEY    = sk-...            (si está vacía, el elicitor usa reglas)
    LLM_BASE_URL   =                  (opcional: para compatibles / modelos locales)
    LLM_TEMPERATURE= 0.3
    LLM_MAX_TOKENS = 1600
"""
from pydantic import Field
from pydantic_settings import BaseSettings


class LLMSettings(BaseSettings):
    """Parámetros del LLM. Inmutables en runtime."""

    LLM_PROVIDER: str = Field(default="openai")
    LLM_MODEL: str = Field(default="gpt-4o-mini")
    LLM_API_KEY: str = Field(default="")
    LLM_BASE_URL: str = Field(default="")
    LLM_TEMPERATURE: float = Field(default=0.3, ge=0.0, le=2.0)
    LLM_MAX_TOKENS: int = Field(default=1600, ge=64, le=8000)

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}

    @property
    def is_configured(self) -> bool:
        """Hay clave y proveedor conocido → se puede usar el LLM real."""
        return bool(self.LLM_API_KEY.strip()) and self.LLM_PROVIDER == "openai"


_llm_settings: LLMSettings | None = None


def get_llm_settings() -> LLMSettings:
    """Singleton de la config del LLM."""
    global _llm_settings
    if _llm_settings is None:
        _llm_settings = LLMSettings()
    return _llm_settings