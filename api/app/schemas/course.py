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
    El instructor solo aporta el tema (y contexto opcional).
    """

    topic: str = Field(..., min_length=5, max_length=500)
    target_audience: str | None = Field(None, max_length=500)
    additional_context: str | None = Field(None, max_length=5000)


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