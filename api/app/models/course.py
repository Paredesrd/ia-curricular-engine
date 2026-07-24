"""
api/app/models/course.py
Modelo ORM del Curso.
Almacena el resultado de la cadena de agentes (matriz, reporte, contenido)
como JSON, junto con su estado de procesamiento.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.core.db import Base


# Estados del curso (String, no ENUM de DB).
STATUS_DRAFT = "draft"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
VALID_STATUSES = {STATUS_DRAFT, STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_FAILED}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=_new_uuid
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Input del instructor
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    target_audience: Mapped[str | None] = mapped_column(String(500), nullable=True)
    additional_context: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Estado y resultados de la cadena de agentes
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=STATUS_DRAFT, index=True
    )
    course_matrix: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    quality_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    course_content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relaciones
    tenant: Mapped["Tenant"] = relationship(back_populates="courses")  # noqa: F821
    creator: Mapped["User"] = relationship(back_populates="courses")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Course id={self.id} status={self.status!r} topic={self.topic!r}>"