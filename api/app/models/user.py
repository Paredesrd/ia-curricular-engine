"""
api/app/models/user.py
Modelo ORM del Usuario.
Pertenece a un único tenant. Rol: admin | instructor.

Regla de identidad: el email es ÚNICO A NIVEL GLOBAL.
Esto permite que el login se haga solo con email + password y que el
backend deduzca el tenant (colegio) del propio usuario, sin pedir slug.
En este MVP no existe el caso de uso "misma persona, mismo correo, en dos
colegios": cada /register funda un colegio con un admin de correo propio,
por lo que la unicidad global refuerza la integridad sin perder funcionalidad.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.core.db import Base

# Roles como String (no ENUM de DB) por portabilidad SQLite/Postgres.
# La validación estricta la hace Pydantic en los schemas.
ROLE_ADMIN = "admin"
ROLE_INSTRUCTOR = "instructor"
VALID_ROLES = {ROLE_ADMIN, ROLE_INSTRUCTOR}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        # Unicidad GLOBAL del email: un correo identifica a un único usuario
        # (y, por su relación, a un único tenant). Reemplaza a la antigua
        # restricción (tenant_id, email) que obligaba a pedir el slug en login.
        UniqueConstraint("email", name="uq_user_email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=_new_uuid
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ROLE_INSTRUCTOR
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relaciones
    tenant: Mapped["Tenant"] = relationship(back_populates="users")  # noqa: F821
    courses: Mapped[list["Course"]] = relationship(  # noqa: F821
        back_populates="creator", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role!r}>"