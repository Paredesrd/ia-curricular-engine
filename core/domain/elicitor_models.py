"""
core/domain/elicitor_models.py
Contrato del agente Elicitor (loop humano-máquina previo a la generación).

Función única: definir request/response del intake. Vive separado de models.py
para no acoplar el elicitor con la cadena de 4 agentes y para poder afinarlo sin
tocar el núcleo de generación.
"""
from typing import Any, Literal

from pydantic import BaseModel, Field


class Turn(BaseModel):
    """Un turno de la conversación (lo guarda el frontend y lo reenvía)."""

    role: Literal["user", "assistant"] = Field(..., description="Quién habló")
    content: str = Field(..., min_length=1, description="Texto del turno")


class Clarification(BaseModel):
    """Una aclaración que el elicitor pide al instructor."""

    field: str = Field(..., description="Clave del campo (ver pedagogical_policy)")
    question: str = Field(..., min_length=5)
    example: str = Field(default="", description="Ejemplo para desbloquear al usuario")
    severity: Literal["blocking", "advisory"] = Field(
        default="blocking",
        description="blocking frena la generación; advisory es opcional",
    )


class EnrichedInstructorInput(BaseModel):
    """
    Intención del instructor ya aclarada y normalizada (output cuando ready).
    Es lo que luego alimentará al Director/Arquitecto (en un turno posterior se
    conectará con la cadena de generación).
    """

    course_name: str
    creator_authority: str
    operational_goal: str
    final_deliverable: str
    audience_profile: str
    content_pillars: str  # texto con los 3-5 pilares numerados
    application_context: str
    out_of_scope: str
    tone: str = "cercano"
    additional_context: str = ""


class ElicitorRequest(BaseModel):
    """
    Lo que el frontend envía cada turno.
    - draft: campos ya llenados hasta ahora (puede estar parcial o vacío).
    - free_text: si el usuario escribió en lenguaje natural este turno.
    - history: la conversación previa (stateless: la guarda el frontend).
    """

    draft: dict[str, Any] = Field(default_factory=dict)
    free_text: str = Field(default="", description="Mensaje libre del instructor")
    history: list[Turn] = Field(default_factory=list)


class ElicitorResponse(BaseModel):
    """Lo que el elicitor devuelve cada turno."""

    status: Literal["ready", "needs_clarification"]
    score: int = Field(..., ge=0, le=100)
    assistant_message: str = Field(..., min_length=1)
    clarifications: list[Clarification] = Field(default_factory=list)
    suggested_draft: dict[str, Any] = Field(default_factory=dict)
    enriched_input: EnrichedInstructorInput | None = None
    mode: Literal["llm", "rules"] = Field(
        ..., description="Si este turno usó la IA real o el fallback de reglas"
    )