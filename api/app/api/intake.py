"""
api/app/api/intake.py
Endpoint del intake conversacional (agente Elicitor).

Función única: exponer el loop humano-máquina que aclara la intención del
instructor ANTES de generar el curso. No toca la BD ni la cadena de 4 agentes.
Stateless: el historial de la charla viaja en el request.
"""
from fastapi import APIRouter, Depends

from api.app.core.deps import get_current_active_user
from api.app.core.path_setup import ensure_core_on_path
from api.app.models.user import User

ensure_core_on_path()

from agents.elicitor import ElicitorAgent  # noqa: E402
from domain.elicitor_models import (  # noqa: E402
    ElicitorRequest,
    ElicitorResponse,
)

router = APIRouter()


@router.post(
    "",
    response_model=ElicitorResponse,
    summary="Turno de aclaración del curso (elicitor conversacional)",
)
def intake_turn(
    payload: ElicitorRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Procesa un turno del intake y devuelve la siguiente pregunta (o 'ready').
    Requiere autenticación (el curso se generará para el colegio del usuario).
    """
    agent = ElicitorAgent()
    return agent.clarify(payload)