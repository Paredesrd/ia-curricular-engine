"""
api/app/api/tenants.py
Router del tenant: consultar el colegio del usuario y editar sus reglas
de acreditación (solo administradores).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.app.core.db import get_db
from api.app.core.deps import get_current_active_user
from api.app.crud.tenant import update_tenant_rules
from api.app.models.user import ROLE_ADMIN, User
from api.app.schemas.tenant import (
    AccreditationRulesPayload,
    TenantDetailResponse,
)


router = APIRouter()


def _require_admin(current_user: User) -> None:
    """Solo los administradores del colegio pueden ejecutar la acción."""
    if current_user.role != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador del colegio puede realizar esta acción.",
        )


@router.get(
    "/me",
    response_model=TenantDetailResponse,
    summary="Consultar el colegio del usuario autenticado (con sus reglas)",
)
def get_my_tenant(current_user: User = Depends(get_current_active_user)):
    """Retorna el tenant del usuario con sus reglas de acreditación."""
    return current_user.tenant


@router.put(
    "/me/rules",
    response_model=TenantDetailResponse,
    summary="Actualizar las reglas de acreditación del colegio (solo admin)",
)
def update_my_tenant_rules(
    payload: AccreditationRulesPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Reemplaza las reglas de acreditación del colegio.
    - Solo administradores (403 si es instructor).
    - Las reglas validadas se usan tal cual por la cadena de agentes al generar cursos.
    """
    _require_admin(current_user)
    update_tenant_rules(db, current_user.tenant, payload.model_dump())
    db.commit()
    db.refresh(current_user.tenant)
    return current_user.tenant