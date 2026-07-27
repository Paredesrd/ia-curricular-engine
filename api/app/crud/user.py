"""
api/app/crud/user.py
CRUD del modelo User.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.app.models.user import User, ROLE_ADMIN


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    """Obtiene un usuario por ID, cargando su tenant (evita lazy load suelto)."""
    stmt = select(User).options(selectinload(User.tenant)).where(User.id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def get_user_by_email(db: Session, *, email: str) -> User | None:
    """
    Obtiene un usuario por email a nivel GLOBAL (sin tenant).
    Como el email es único globalmente, esto identifica unívocamente al
    usuario y, por su relación, a su tenant. Se usa en el login sin slug.
    Carga el tenant eagerly para poder validar tenant.is_active sin lazy load.
    """
    stmt = (
        select(User)
        .options(selectinload(User.tenant))
        .where(User.email == email)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_user_by_email_and_tenant(
    db: Session, *, email: str, tenant_id: uuid.UUID
) -> User | None:
    """
    Obtiene un usuario por email dentro de un tenant específico.
    Se conserva por compatibilidad con otros módulos; el login ya no la usa.
    """
    stmt = (
        select(User)
        .options(selectinload(User.tenant))
        .where(User.email == email, User.tenant_id == tenant_id)
    )
    return db.execute(stmt).scalar_one_or_none()


def create_user(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    email: str,
    hashed_password: str,
    full_name: str,
    role: str = ROLE_ADMIN,
) -> User:
    """
    Crea un usuario. NO hace commit (lo decide el llamador para atomicidad).
    """
    user = User(
        tenant_id=tenant_id,
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        role=role,
    )
    db.add(user)
    db.flush()
    return user