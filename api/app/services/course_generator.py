"""
api/app/services/course_generator.py
Enchufe entre la API y el núcleo de IA.

Recibe las reglas del tenant (TenantRules) y el pedido del instructor
(InstructorInput), ejecuta la cadena de 4 agentes (Director -> Arquitecto ->
Auditor -> Redactor) con reintentos, y devuelve los tres payloads resultantes
como dicts listos para persistir en JSON.

NO toca la base de datos, NO imprime, NO hace sys.exit, NO guarda archivos:
es puro. La orquestación con IO vive en el router.
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
    DirectorBrief,
    CourseMatrix,
    CourseContent,
    ValidationStatus,
)
from agents.director import DirectorAgent  # noqa: E402
from agents.architect import ArchitectAgent  # noqa: E402
from agents.auditor import AuditorAgent  # noqa: E402
from agents.writer import WriterAgent  # noqa: E402


logger = logging.getLogger(__name__)

# Reintentos del par Arquitecto+Auditor si el curso no es aprobado.
MAX_ATTEMPTS = 3


class GenerationError(Exception):
    """Error controlado de la cadena de generación de un curso."""


def generate_course(
    tenant_rules: TenantRules,
    instructor_input: InstructorInput,
) -> dict:
    """
    Ejecuta la cadena completa de agentes.

    Returns:
        dict con claves:
          - "course_matrix":  dict (CourseMatrix en JSON)
          - "quality_report": dict (QualityReport en JSON)
          - "course_content": dict (CourseContent en JSON)

    Raises:
        GenerationError: si la cadena no logra un curso aprobado tras
                         MAX_ATTEMPTS, o si algún agente falla.
    """
    logger.info(
        "generate_course | tenant=%s | topic=%s",
        tenant_rules.tenant_name,
        instructor_input.topic,
    )

    director = DirectorAgent()
    architect = ArchitectAgent()
    auditor = AuditorAgent()
    writer = WriterAgent()

    # Fase 1: Director
    try:
        msg_director = director.process(tenant_rules, instructor_input)
        brief = DirectorBrief(**msg_director.payload)
    except Exception as exc:
        logger.exception("Fallo en DirectorAgent")
        raise GenerationError(f"DirectorAgent: {exc}") from exc

    # Fase 2+3: Arquitecto + Auditor con reintentos
    matrix: CourseMatrix | None = None
    report_payload: dict | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            msg_architect = architect.process(brief)
            matrix = CourseMatrix(**msg_architect.payload)
        except Exception as exc:
            logger.exception("Fallo en ArchitectAgent (intento %d)", attempt)
            raise GenerationError(f"ArchitectAgent: {exc}") from exc

        try:
            msg_auditor = auditor.process(brief, matrix)
            report_payload = msg_auditor.payload
        except Exception as exc:
            logger.exception("Fallo en AuditorAgent (intento %d)", attempt)
            raise GenerationError(f"AuditorAgent: {exc}") from exc

        if report_payload["status"] == ValidationStatus.APPROVED.value:
            logger.info("Curso aprobado en intento %d", attempt)
            break

        logger.warning(
            "Curso no aprobado (intento %d): %s",
            attempt,
            report_payload.get("summary"),
        )
        if attempt == MAX_ATTEMPTS:
            raise GenerationError(
                "El curso no superó la auditoría tras "
                f"{MAX_ATTEMPTS} intentos: {report_payload.get('summary')}"
            )

    if matrix is None or report_payload is None:
        raise GenerationError("No se produjo una matriz curricular válida.")

    # Fase 4: Redactor
    try:
        msg_writer = writer.process(matrix)
        content_payload = msg_writer.payload
    except Exception as exc:
        logger.exception("Fallo en WriterAgent")
        raise GenerationError(f"WriterAgent: {exc}") from exc

    # Validación mínima de integridad del contenido
    content_obj = CourseContent(**content_payload)
    if len(content_obj.lessons_content) == 0:
        raise GenerationError("El curso generado no contiene lecciones.")

    return {
        "course_matrix": matrix.model_dump(mode="json"),
        "quality_report": report_payload,
        "course_content": content_payload,
    }