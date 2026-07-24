"""
api/app/crud/course.py
CRUD del modelo Course.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.models.course import (
    Course,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
    STATUS_FAILED,
)


def create_course(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    created_by: uuid.UUID,
    topic: str,
    target_audience: str | None = None,
    additional_context: str | None = None,
) -> Course:
    """Crea la ficha del curso en estado 'in_progress'. NO hace commit."""
    course = Course(
        tenant_id=tenant_id,
        created_by=created_by,
        topic=topic,
        target_audience=target_audience,
        additional_context=additional_context,
        status=STATUS_IN_PROGRESS,
    )
    db.add(course)
    db.flush()
    return course


def get_course_by_id(db: Session, course_id: uuid.UUID) -> Course | None:
    """Obtiene un curso por ID (sin filtrar tenant; el router valida pertenencia)."""
    return db.get(Course, course_id)


def list_courses_by_tenant(db: Session, tenant_id: uuid.UUID) -> list[Course]:
    """Lista los cursos de un tenant, más recientes primero."""
    stmt = (
        select(Course)
        .where(Course.tenant_id == tenant_id)
        .order_by(Course.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def update_course_generation(
    db: Session,
    course: Course,
    *,
    status: str,
    course_matrix: dict | None = None,
    quality_report: dict | None = None,
    course_content: dict | None = None,
    error_message: str | None = None,
) -> Course:
    """Actualiza el resultado de la generación. NO hace commit."""
    course.status = status
    course.course_matrix = course_matrix
    course.quality_report = quality_report
    course.course_content = course_content
    course.error_message = error_message
    db.add(course)
    db.flush()
    return course


# Re-export de estados para comodidad del router.
__all__ = [
    "create_course",
    "get_course_by_id",
    "list_courses_by_tenant",
    "update_course_generation",
    "STATUS_COMPLETED",
    "STATUS_FAILED",
]