"""
api/app/schemas/user.py
Schemas de usuario y autenticación.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from api.app.schemas.tenant import SLUG_PATTERN, TenantResponse


class UserRegisterRequest(BaseModel):
    """
    Payload de registro.
    Crea un nuevo tenant (colegio) y a su admin fundador en una sola operación.
    """

    tenant_name: str = Field(..., min_length=3, max_length=255)
    tenant_slug: str = Field(
        ...,
        min_length=3,
        max_length=60,
        pattern=SLUG_PATTERN,
        description="Identificador único del colegio (lowercase, guiones).",
    )
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)


class UserResponse(BaseModel):
    """Representación pública de un usuario."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    tenant_id: uuid.UUID
    is_active: bool
    created_at: datetime


class UserWithTenantResponse(BaseModel):
    """Usuario con su tenant anidado (usado en /me y /register)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    tenant: TenantResponse


class TokenResponse(BaseModel):
    """Respuesta del login: JWT + tipo."""

    access_token: str
    token_type: str = "bearer"