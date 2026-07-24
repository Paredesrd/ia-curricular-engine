"""
api/app/schemas/tenant.py
Schemas del Tenant (Colegio de Profesionales).
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# Slug: lowercase, números y guiones simples. Ej: colegio-ingenieros
SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"

# Niveles de Bloom aceptados (sin acoplar al enum del núcleo).
BloomLiteral = Literal[
    "remember", "understand", "apply", "analyze", "evaluate", "create"
]


class TenantResponse(BaseModel):
    """Representación pública ligera de un tenant."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str = Field(..., pattern=SLUG_PATTERN)
    is_active: bool
    created_at: datetime


class AccreditationRulesPayload(BaseModel):
    """
    Reglas de acreditación que el administrador del colegio puede editar.
    Estructura compatible con TenantRules del núcleo.
    """

    min_total_hours: int = Field(..., ge=1)
    max_total_hours: int = Field(..., ge=1)
    min_module_hours: int = Field(..., ge=1)
    max_module_hours: int = Field(..., ge=1)
    required_bloom_levels: list[BloomLiteral] = Field(..., min_length=1)
    min_lessons_per_module: int = Field(..., ge=1)
    max_lessons_per_module: int = Field(..., ge=1)
    custom_restrictions: str | None = None

    @field_validator("required_bloom_levels")
    @classmethod
    def _no_duplicados(cls, v: list[str]) -> list[str]:
        if len(v) != len(set(v)):
            raise ValueError("required_bloom_levels contiene duplicados")
        return v

    @model_validator(mode="after")
    def _rangos_consistentes(self) -> "AccreditationRulesPayload":
        if self.max_total_hours < self.min_total_hours:
            raise ValueError("max_total_hours debe ser >= min_total_hours")
        if self.max_module_hours < self.min_module_hours:
            raise ValueError("max_module_hours debe ser >= min_module_hours")
        if self.max_lessons_per_module < self.min_lessons_per_module:
            raise ValueError("max_lessons_per_module debe ser >= min_lessons_per_module")
        return self


class TenantDetailResponse(BaseModel):
    """Tenant con sus reglas de acreditación (para /tenants/me)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    accreditation_rules: dict
    created_at: datetime