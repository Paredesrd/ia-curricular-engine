"""
test_integration.py
Test de integración automatizado de la cadena completa.
Valida que el sistema produce un CourseContent válido desde cero.

Ejecutar: python test_integration.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from domain.models import (
    TenantRules,
    InstructorInput,
    BloomLevel,
    DirectorBrief,
    CourseMatrix,
    CourseContent,
    ValidationStatus,
)
from agents.director import DirectorAgent
from agents.architect import ArchitectAgent
from agents.auditor import AuditorAgent
from agents.writer import WriterAgent


def test_full_pipeline() -> None:
    """
    Test de integración: cadena completa Director → Arquitecto → Auditor → Redactor.
    Valida que el output cumple TODAS las restricciones del Tenant.
    """
    print("=" * 60)
    print("TEST DE INTEGRACIÓN - CADENA COMPLETA")
    print("=" * 60)

    # --- Setup: Tenant + Instructor ---
    rules = TenantRules(
        tenant_id="TEST-INTEGRATION",
        tenant_name="Colegio de Pruebas",
        min_total_hours=15,
        max_total_hours=35,
        min_module_hours=3,
        max_module_hours=9,
        required_bloom_levels=[
            BloomLevel.REMEMBER,
            BloomLevel.UNDERSTAND,
            BloomLevel.APPLY,
        ],
        min_lessons_per_module=2,
        max_lessons_per_module=4,
        custom_restrictions="Cada módulo debe incluir un caso práctico.",
    )

    instructor = InstructorInput(
        topic="Gestión de Proyectos Ágiles",
        target_audience="Profesionales de TI con experiencia básica",
    )

    # --- Paso 1: Director ---
    print("[1/4] DirectorAgent...")
    director = DirectorAgent()
    msg_director = director.process(rules, instructor)
    brief = DirectorBrief(**msg_director.payload)
    assert brief.course_id is not None
    assert brief.topic == instructor.topic
    assert len(brief.constraints_summary) >= 4
    print(f"      ✓ Brief: {brief.course_id}")

    # --- Paso 2: Arquitecto ---
    print("[2/4] ArchitectAgent...")
    architect = ArchitectAgent()
    msg_architect = architect.process(brief)
    matrix = CourseMatrix(**msg_architect.payload)
    assert len(matrix.modules) >= 1
    assert matrix.total_estimated_hours >= rules.min_total_hours
    assert matrix.total_estimated_hours <= rules.max_total_hours
    print(f"      ✓ Matriz: {len(matrix.modules)} módulos, {matrix.total_estimated_hours}h")

    # --- Paso 3: Auditor ---
    print("[3/4] AuditorAgent...")
    auditor = AuditorAgent()
    msg_auditor = auditor.process(brief, matrix)
    report = msg_auditor.payload
    assert report["status"] == ValidationStatus.APPROVED.value
    assert report["critical_issues"] == 0
    print(f"      ✓ Auditoría: {report['status'].upper()}")

    # --- Paso 4: Redactor ---
    print("[4/4] WriterAgent...")
    writer = WriterAgent()
    msg_writer = writer.process(matrix)
    content = CourseContent(**msg_writer.payload)
    assert len(content.lessons_content) >= 1
    assert content.course_id == brief.course_id
    print(f"      ✓ Contenido: {len(content.lessons_content)} lecciones")

    # --- Validaciones finales ---
    print("-" * 60)
    print("Validaciones de restricciones del Tenant:")

    # Horas totales
    total_hours = sum(lc.estimated_hours for lc in content.lessons_content)
    assert rules.min_total_hours <= total_hours <= rules.max_total_hours
    print(f"  ✓ Horas totales: {total_hours:.1f}h (rango: {rules.min_total_hours}-{rules.max_total_hours})")

    # Bloom coverage
    bloom_levels_in_content = set()
    for module in matrix.modules:
        for lesson in module.lessons:
            bloom_levels_in_content.add(lesson.bloom_level)

    for required_level in rules.required_bloom_levels:
        assert required_level in bloom_levels_in_content
    print(f"  ✓ Bloom requeridos presentes: {[b.value for b in rules.required_bloom_levels]}")

    # Lecciones por módulo
    for module in matrix.modules:
        num_lessons = len(module.lessons)
        assert rules.min_lessons_per_module <= num_lessons <= rules.max_lessons_per_module
    print(f"  ✓ Lecciones por módulo: {rules.min_lessons_per_module}-{rules.max_lessons_per_module}")

    # Contenido no vacío
    for lc in content.lessons_content:
        assert len(lc.full_content) >= 100
        assert len(lc.activities) >= 1
        assert len(lc.assessment_criteria) >= 1
    print(f"  ✓ Contenido de lecciones: no vacío y estructurado")

    print("=" * 60)
    print("TEST DE INTEGRACIÓN: PASÓ")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_full_pipeline()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ TEST DE INTEGRACIÓN FALLÓ: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR INESPERADO: {e}")
        sys.exit(1)