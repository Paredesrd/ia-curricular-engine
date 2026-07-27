"""
core/llm/client.py
Puerto de acceso al LLM + implementación OpenAI + fábrica con fallback.

Función única: hablar con un modelo de chat y devolver texto. NO sabe nada de
pedagogía ni del elicitor; eso vive en agents/elicitor.py.

Diseño:
  - LLMClient es la INTERFAZ (puerto). Cambiar de proveedor = nueva subclase en
    su propio archivo; el elicitor no se entera.
  - OpenAIClient es la implementación real (import lazy de la librería `openai`).
  - get_llm_client() devuelve un cliente o None. Devuelve None si: no hay clave,
    el proveedor no está implementado, o la librería no está instalada. En ese
    caso el elicitor cae a su modo de reglas SIN explotar.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from config.llm_settings import get_llm_settings

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Interfaz mínima de chat. messages = lista de {role, content}."""

    @abstractmethod
    def chat(self, messages: list[dict], response_format_json: bool = True) -> str:
        """Envía mensajes y retorna el texto de respuesta del modelo."""


class OpenAIClient(LLMClient):
    """Cliente OpenAI (o compatible vía LLM_BASE_URL). Import lazy."""

    def __init__(self) -> None:
        try:
            from openai import OpenAI  # import lazy: solo si se usa de verdad
        except ImportError as exc:
            raise RuntimeError(
                "La librería 'openai' no está instalada. "
                "Ejecuta: pip install openai"
            ) from exc

        s = get_llm_settings()
        kwargs = {"api_key": s.LLM_API_KEY}
        if s.LLM_BASE_URL.strip():
            kwargs["base_url"] = s.LLM_BASE_URL.strip()
        self._client = OpenAI(**kwargs)
        self._model = s.LLM_MODEL
        self._temperature = s.LLM_TEMPERATURE
        self._max_tokens = s.LLM_MAX_TOKENS

    def chat(self, messages: list[dict], response_format_json: bool = True) -> str:
        kwargs: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        if response_format_json:
            kwargs["response_format"] = {"type": "json_object"}
        resp = self._client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""


def get_llm_client() -> LLMClient | None:
    """
    Fábrica. Retorna un cliente real o None (→ el llamador usa fallback de reglas).
    Nunca lanza: cualquier problema de config/instalación se traduce en None.
    """
    s = get_llm_settings()
    if not s.is_configured:
        logger.info("LLM no configurado (sin clave o proveedor no implementado).")
        return None
    try:
        if s.LLM_PROVIDER == "openai":
            return OpenAIClient()
        # Aquí se añadirán otros proveedores (anthropic, gemini) en sus archivos.
        logger.warning("Proveedor LLM no implementado: %s", s.LLM_PROVIDER)
        return None
    except Exception as exc:  # noqa: BLE001  (no explotar el arranque)
        logger.warning("No se pudo crear el cliente LLM (%s). Usando reglas.", exc)
        return None