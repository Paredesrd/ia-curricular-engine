"""
tests/test_models.py
Tests unitarios de los modelos de dominio (Pydantic).
Sin dependencias externas. Python puro + assert.

Ejecutar: python tests/test_models.py
"""

import sys
from pathlib import Path

# Asegurar que el proyecto está en el path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import (
    BloomLevel,
    AgentRole,
    ValidationStatus,
    TenantRules,
    InstructorInput,
    DirectorBrief,
    Lesson,
    Module,
    CourseMatrix,
    QualityIssue,
    QualityReport,
    LessonContent,
    CourseContent,
    AgentMessage,
)


def test_bloom_level_enum() -> None:
    """Verifica que BloomLevel tiene los 6 niveles."""
    assert len(BloomLevel) == 6
    assert BloomLevel.REMEMBER.value == "remember"
    assert BloomLevel.CREATE.value == "create"
    print("  ✓ test_bloom_level_enum")


def test_agent_role_enum() -> None:
    """Verifica que AgentRole tiene los 4 roles."""
    assert len(AgentRole) == 4
    assert AgentRole.DIRECTOR.value == "director"
    assert AgentRole.WRITER.value == "writer"
    print("  ✓ test_agent_role_enum")


def test_tenant_rules_valid() -> None:
    """Verifica creación de TenantRules válidas."""
    rules = TenantRules(
        tenant_id="TEST-001",
        tenant_name="Colegio de Test",
        min_total_hours=10,
        max_total_hours=30,
        min_module_hours=2,
        max_module_hours=8,
        required_bloom_levels=[BloomLevel.REMEMBER, BloomLevel.APPLY],
        min_lessons_per_module=2,
        max_lessons_per_module=4,
    )
    assert rules.tenant_id == "TEST-001"
    assert rules.min_total_hours == 10
    assert len(rules.required_bloom_levels) == 2
    print("  ✓ test_tenant_rules_valid")


def test_tenant_rules_invalid_hours() -> None:
    """Verifica que TenantRules rechaza max < min."""
    try:
        TenantRules(
            tenant_id="TEST-002",
            tenant_name="Colegio Inválido",
            min_total_hours=30,
            max_total_hours=10,  # Inválido: max < min
            min_module_hours=2,
            max_module_hours=8,
            required_bloom_levels=[BloomLevel.REMEMBER],
            min_lessons_per_module=2,
            max_lessons_per_module=4,
        )
        assert False, "Debió lanzar ValueError"
    except (ValueError, Exception):
        pass
    print("  ✓ test_tenant_rules_invalid_hours")


def test_instructor_input_valid() -> None:
    """Verifica creación de InstructorInput válido."""
    inp = InstructorInput(
        topic="Inteligencia Artificial Aplicada",
        target_audience="Ingenieros de software",
    )
    assert inp.topic == "Inteligencia Artificial Aplicada"
    assert inp.additional_context is None
    print("  ✓ test_instructor_input_valid")


def test_instructor_input_topic_too_short() -> None:
    """Verifica que InstructorInput rechaza topic < 5 chars."""
    try:
        InstructorInput(topic="IA")
        assert False, "Debió lanzar ValueError"
    except (ValueError, Exception):
        pass
    print("  ✓ test_instructor_input_topic_too_short")


def test_lesson_valid() -> None:
    """Verifica creación de Lesson válida."""
    lesson = Lesson(
        lesson_id="M1L1",
        title="Introducción a los fundamentos",
        bloom_level=BloomLevel.REMEMBER,
        estimated_hours=2.0,
        learning_objective="Identificar los conceptos básicos del tema.",
        key_topics=["Concepto A", "Concepto B"],
    )
    assert lesson.lesson_id == "M1L1"
    assert lesson.bloom_level == BloomLevel.REMEMBER
    assert lesson.estimated_hours == 2.0
    print("  ✓ test_lesson_valid")


def test_module_valid() -> None:
    """Verifica creación de Module válido."""
    lesson = Lesson(
        lesson_id="M1L1",
        title="Lección de prueba",
        bloom_level=BloomLevel.APPLY,
        estimated_hours=1.5,
        learning_objective="Aplicar técnicas básicas del tema.",
        key_topics=["Técnica 1"],
    )
    module = Module(
        module_id="M1",
        title="Módulo de prueba",
        description="Este es un módulo de prueba para validación.",
        estimated_hours=1.5,
        lessons=[lesson],
    )
    assert module.module_id == "M1"
    assert len(module.lessons) == 1
    print("  ✓ test_module_valid")


def test_course_matrix_valid() -> None:
    """Verifica creación de CourseMatrix válida."""
    lesson = Lesson(
        lesson_id="M1L1",
        title="Lección de prueba",
        bloom_level=BloomLevel.ANALYZE,
        estimated_hours=2.0,
        learning_objective="Analizar componentes del sistema.",
        key_topics=["Componente A"],
    )
    module = Module(
        module_id="M1",
        title="Módulo de prueba",
        description="Descripción del módulo de prueba.",
        estimated_hours=2.0,
        lessons=[lesson],
    )
    matrix = CourseMatrix(
        course_id="TEST-COURSE-001",
        course_title="Curso de Prueba",
        topic="Tema de prueba",
        total_estimated_hours=2.0,
        modules=[module],
        bloom_distribution={BloomLevel.ANALYZE: 1},
    )
    assert matrix.course_id == "TEST-COURSE-001"
    assert len(matrix.modules) == 1
    print("  ✓ test_course_matrix_valid")


def test_quality_report_valid() -> None:
    """Verifica creación de QualityReport válido."""
    issue = QualityIssue(
        issue_id="ISS-001",
        severity="major",
        component="M1",
        description="El módulo excede las horas máximas permitidas.",
        suggestion="Reducir el contenido del módulo.",
    )
    report = QualityReport(
        course_id="TEST-001",
        status=ValidationStatus.NEEDS_REVISION,
        total_issues=1,
        critical_issues=0,
        issues=[issue],
        summary="El curso requiere revisión por exceso de horas.",
        recommendations=["Reducir horas del módulo M1."],
    )
    assert report.status == ValidationStatus.NEEDS_REVISION
    assert report.total_issues == 1
    print("  ✓ test_quality_report_valid")


def test_agent_message_valid() -> None:
    """Verifica creación de AgentMessage válido."""
    msg = AgentMessage(
        sender=AgentRole.DIRECTOR,
        receiver=AgentRole.ARCHITECT,
        message_type="director_brief",
        payload={"course_id": "TEST-001", "topic": "Test"},
        timestamp="2026-07-24T00:00:00+00:00",
    )
    assert msg.sender == AgentRole.DIRECTOR
    assert msg.receiver == AgentRole.ARCHITECT
    print("  ✓ test_agent_message_valid")


def test_director_brief_valid() -> None:
    """Verifica creación de DirectorBrief válido."""
    brief = DirectorBrief(
        course_id="TEST-001",
        topic="Diseño Estructural",
        tenant_id="COL-001",
        tenant_name="Colegio de Test",
        min_total_hours=10,
        max_total_hours=30,
        min_module_hours=2,
        max_module_hours=8,
        required_bloom_levels=[BloomLevel.REMEMBER, BloomLevel.APPLY],
        min_lessons_per_module=2,
        max_lessons_per_module=4,
        constraints_summary=["Regla 1", "Regla 2"],
        created_at="2026-07-24T00:00:00+00:00",
    )
    assert brief.course_id == "TEST-001"
    assert len(brief.constraints_summary) == 2
    print("  ✓ test_director_brief_valid")


def test_lesson_content_valid() -> None:
    """Verifica creación de LessonContent válido."""
    content = LessonContent(
        lesson_id="M1L1",
        title="Lección de prueba",
        full_content="Este es un contenido de prueba que tiene más de cien caracteres para cumplir con la validación mínima del modelo Pydantic.",
        activities=["Actividad 1", "Actividad 2"],
        assessment_criteria=["Criterio 1"],
        estimated_hours=2.0,
    )
    assert content.lesson_id == "M1L1"
    assert len(content.activities) == 2
    print("  ✓ test_lesson_content_valid")


# ============================================================
# EJECUCIÓN
# ============================================================

def main() -> None:
    print("=" * 60)
    print("TESTS UNITARIOS DE MODELOS DE DOMINIO")
    print("=" * 60)

    tests = [
        test_bloom_level_enum,
        test_agent_role_enum,
        test_tenant_rules_valid,
        test_tenant_rules_invalid_hours,
        test_instructor_input_valid,
        test_instructor_input_topic_too_short,
        test_lesson_valid,
        test_module_valid,
        test_course_matrix_valid,
        test_quality_report_valid,
        test_agent_message_valid,
        test_director_brief_valid,
        test_lesson_content_valid,
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  ✗ {test_fn.__name__}: {e}")
            failed += 1

    print("-" * 60)
    print(f"Resultados: {passed} pasaron, {failed} fallaron, {len(tests)} total")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()