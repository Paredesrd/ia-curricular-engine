"""
api/app/schemas/course.py
Schemas de request/response del módulo de cursos.
"""
import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class CourseCreateRequest(BaseModel):
    """
    Payload para pedir la generación de un curso.
    Campos clásicos (topic/target_audience/additional_context) + los 9 de
    intención del elicitor, todos opcionales. Cuando el frontend envíe la
    intención enriquecida, estos 9 vendrán poblados y el router los pasará al
    InstructorInput del núcleo; si no (llamada vieja/CLI), quedan en None y el
    motor cae al comportamiento por tema.
    """
    # --- Clásicos ---
    topic: str = Field(..., min_length=5, max_length=500)
    target_audience: str | None = Field(None, max_length=500)
    additional_context: str | None = Field(None, max_length=5000)
    # --- Intención enriquecida (elicitor) ---
    course_name: str | None = Field(None, max_length=255)
    creator_authority: str | None = Field(None, max_length=500)
    operational_goal: str | None = Field(None, max_length=2000)
    final_deliverable: str | None = Field(None, max_length=2000)
    audience_profile: str | None = Field(None, max_length=500)
    content_pillars: str | None = Field(None, max_length=4000)
    application_context: str | None = Field(None, max_length=1000)
    out_of_scope: str | None = Field(None, max_length=2000)
    tone: str | None = Field(None, max_length=100)


class CourseSummary(BaseModel):
    """Representación ligera para listados (sin payloads JSON grandes)."""
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    topic: str
    target_audience: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class CourseResponse(BaseModel):
    """Representación completa de un curso (incluye el resultado generado)."""
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_by: uuid.UUID
    topic: str
    target_audience: str | None
    additional_context: str | None
    status: str
    course_matrix: dict[str, Any] | None
    quality_report: dict[str, Any] | None
    course_content: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime