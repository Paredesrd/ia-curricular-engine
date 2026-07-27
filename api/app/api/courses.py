"""
api/app/api/courses.py
Router de cursos: pedir generación, listar, consultar y eliminar
(multi-tenant aislado).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# El service registra core/ en sys.path al importarse; va primero por seguridad.
from api.app.services.course_generator import generate_course, GenerationError

# Imports del núcleo (resuelven gracias al puente de path_setup).
from domain.models import TenantRules, InstructorInput

from api.app.core.db import get_db
from api.app.core.deps import get_current_active_user
from api.app.crud.course import (
    create_course,
    get_course_by_id,
    list_courses_by_tenant,
    update_course_generation,
    delete_course,
    STATUS_COMPLETED,
    STATUS_FAILED,
)
from api.app.models.course import Course
from api.app.models.user import User
from api.app.schemas.course import (
    CourseCreateRequest,
    CourseResponse,
    CourseSummary,
)

router = APIRouter()


def _build_tenant_rules(tenant) -> TenantRules:
    """Construye las TenantRules del núcleo a partir del tenant ORM."""
    rules = dict(tenant.accreditation_rules or {})
    return TenantRules(
        tenant_id=str(tenant.id),
        tenant_name=tenant.name,
        **rules,
    )


def _ensure_owned(course: Course, user: User) -> None:
    """
    Garantiza que el curso pertenece al tenant del usuario.
    Si no, 404 (no 403) para no permitir enumeración de IDs ajenos.
    """
    if course is None or course.tenant_id != user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado.",
        )


@router.post(
    "",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Pedir la generación de un curso (dispara la cadena de agentes)",
)
def create_and_generate(
    payload: CourseCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Crea la ficha del curso y ejecuta la cadena de 4 agentes del núcleo.
    Persiste el resultado (matriz, reporte, contenido) y devuelve el curso.
    Si la generación falla, la ficha queda como 'failed' y se retorna 500.

    La intención enriquecida del elicitor (9 campos) se pasa al núcleo vía
    InstructorInput para que los agentes la usen como "huesos" del curso.
    No se persiste como columnas (el resultado generado ya la refleja).
    """
    tenant_rules = _build_tenant_rules(current_user.tenant)

    instructor_input = InstructorInput(
        # --- Clásicos (retrocompatibles) ---
        topic=payload.topic,
        target_audience=payload.target_audience,
        additional_context=payload.additional_context,
        # --- Intención enriquecida del elicitor (paso 2) ---
        course_name=payload.course_name,
        creator_authority=payload.creator_authority,
        operational_goal=payload.operational_goal,
        final_deliverable=payload.final_deliverable,
        audience_profile=payload.audience_profile,
        content_pillars=payload.content_pillars,
        application_context=payload.application_context,
        out_of_scope=payload.out_of_scope,
        tone=payload.tone,
    )

    course = create_course(
        db,
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        topic=payload.topic,
        target_audience=payload.target_audience,
        additional_context=payload.additional_context,
    )
    db.commit()
    db.refresh(course)

    try:
        result = generate_course(tenant_rules, instructor_input)
    except GenerationError as exc:
        update_course_generation(
            db,
            course,
            status=STATUS_FAILED,
            error_message=str(exc),
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"La generación del curso falló: {exc}",
        )

    update_course_generation(
        db,
        course,
        status=STATUS_COMPLETED,
        course_matrix=result["course_matrix"],
        quality_report=result["quality_report"],
        course_content=result["course_content"],
    )
    db.commit()
    db.refresh(course)
    return course


@router.get(
    "",
    response_model=list[CourseSummary],
    summary="Listar los cursos del colegio del usuario autenticado",
)
def list_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retorna solo los cursos del tenant del usuario (aislamiento multi-tenant)."""
    courses = list_courses_by_tenant(db, current_user.tenant_id)
    return courses


@router.get(
    "/{course_id}",
    response_model=CourseResponse,
    summary="Consultar un curso por ID (solo si pertenece al colegio del usuario)",
)
def get_course(
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retorna el curso completo si pertenece al tenant del usuario; si no, 404."""
    course = get_course_by_id(db, course_id)
    _ensure_owned(course, current_user)
    return course


@router.delete(
    "/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un curso (solo si pertenece al colegio del usuario)",
)
def delete_course_endpoint(
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Borra el curso si pertenece al tenant del usuario; si no, 404.
    Cualquier miembro del colegio puede borrar (coherente con crear/listar,
    que tampoco exigen admin). Retorna 204 sin cuerpo.
    IMPORTANTE: tras el commit NO se hace db.refresh(course) porque la fila
    ya no existe.
    """
    course = get_course_by_id(db, course_id)
    _ensure_owned(course, current_user)
    delete_course(db, course)
    db.commit()
    return None