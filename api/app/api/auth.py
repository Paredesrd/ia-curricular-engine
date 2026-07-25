"""
api/app/api/auth.py
Router de autenticación: registro (fundación de tenant), login (JWT) y /me.
"""

from fastapi import APIRouter, Depends, Form, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.app.core.db import get_db
from api.app.core.deps import get_current_active_user
from api.app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from api.app.crud.tenant import create_tenant, get_tenant_by_slug
from api.app.crud.user import (
    create_user,
    get_user_by_email,
)
from api.app.models.user import ROLE_ADMIN, User
from api.app.schemas.user import (
    TokenResponse,
    UserRegisterRequest,
    UserWithTenantResponse,
)


router = APIRouter()


@router.post(
    "/register",
    response_model=UserWithTenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo colegio y su admin fundador",
)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Crea un tenant nuevo (colegio) y a su primer usuario con rol admin.
    - Si el slug ya existe → 409.
    - Operación atómica: si algo falla, no queda tenant huérfano.
    """
    # 1. El slug debe estar libre (regla de seguridad: no colarse en tenant ajeno).
    if get_tenant_by_slug(db, payload.tenant_slug) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El identificador del colegio (slug) ya está registrado.",
        )

    try:
        # 2. Crear tenant + admin en la misma transacción.
        tenant = create_tenant(
            db,
            name=payload.tenant_name,
            slug=payload.tenant_slug,
        )
        user = create_user(
            db,
            tenant_id=tenant.id,
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            role=ROLE_ADMIN,
        )
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflicto de unicidad al registrar (slug o email).",
        )

    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Autenticar y obtener un JWT",
)
def login(
    username: str = Form(..., description="Email del usuario."),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Autenticación por email + password.
    Retorna un JWT. Usa Form para compatibilidad con el botón Authorize de /docs.
    Cualquier fallo devuelve 401 genérico (no enumera tenants ni usuarios).
    """
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = get_user_by_email(db, email=username)
    if user is None or not verify_password(password, user.hashed_password):
        raise invalid

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta inactiva.",
        )

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "role": user.role,
        }
    )
    return TokenResponse(access_token=access_token)


@router.get(
    "/me",
    response_model=UserWithTenantResponse,
    summary="Obtener el usuario autenticado y su tenant",
)
def me(current_user: User = Depends(get_current_active_user)):
    """Retorna el usuario del JWT con su tenant anidado."""
    return current_user