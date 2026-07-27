"""
api/app/services/course_generator.py
Enchufe entre la API y el núcleo de IA.

NO reimplementa la cadena de agentes: delega en el orquestador único del
núcleo (core/orchestrator.py -> Orchestrator.run). Así existe UNA sola lógica
de orquestación (loop de revisión, reintentos, validación) compartida por la
API y el CLI, sin duplicación ni divergencia.

Recibe las reglas del tenant (TenantRules) y el pedido del instructor
(InstructorInput) y devuelve los tres payloads resultantes como dicts listos
para persistir en JSON. NO toca la base de datos, NO imprime, NO hace
sys.exit, NO guarda archivos: la orquestación con IO vive en el router.
"""
import logging

from api.app.core.path_setup import ensure_core_on_path

# Blindaje: si este módulo se importa sin pasar por services/__init__,
# core/ queda registrado igual. Idempotente.
ensure_core_on_path()

# Imports del núcleo (resuelven gracias al puente de path_setup).
from domain.models import (  # noqa: E402
    TenantRules,
    InstructorInput,
)
from orchestrator import Orchestrator  # noqa: E402  (core/orchestrator.py)

logger = logging.getLogger(__name__)


class GenerationError(Exception):
    """Error controlado de la cadena de generación de un curso."""


def generate_course(
    tenant_rules: TenantRules,
    instructor_input: InstructorInput,
) -> dict:
    """
    Ejecuta la cadena completa de agentes delegando en el orquestador único.

    Returns:
        dict con claves:
          - "course_matrix":  dict (CourseMatrix en JSON)
          - "quality_report": dict (QualityReport en JSON)
          - "course_content": dict (CourseContent en JSON)
    Raises:
        GenerationError: si la cadena no logra un curso aprobado o falla.
    """
    logger.info(
        "generate_course | tenant=%s | topic=%s",
        tenant_rules.tenant_name,
        instructor_input.topic,
    )

    orchestrator = Orchestrator()
    try:
        result = orchestrator.run(tenant_rules, instructor_input)
    except Exception as exc:  # cualquier fallo no controlado del núcleo
        logger.exception("Fallo no controlado en la cadena de agentes")
        raise GenerationError(f"Cadena de agentes: {exc}") from exc

    if result is None:
        raise GenerationError(
            "El curso no superó la auditoría tras los reintentos "
            "configurados o un agente falló de forma irrecuperable."
        )

    return result