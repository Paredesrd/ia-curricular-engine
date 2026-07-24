"""
api/app/models/tenant.py
Modelo ORM del Tenant (Colegio de Profesionales).
Un tenant agrupa usuarios, reglas de acreditación y cursos.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=_new_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(120), unique=True, index=True, nullable=False
    )
    # Reglas de acreditación serializadas (equivale a TenantRules del núcleo).
    accreditation_rules: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relaciones
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        back_populates="tenant", cascade="all, delete-orphan"
    )
    courses: Mapped[list["Course"]] = relationship(  # noqa: F821
        back_populates="tenant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} slug={self.slug!r}>"