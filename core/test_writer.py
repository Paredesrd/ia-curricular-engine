"""
test_writer.py
Test manual del Agente Redactor.
Ejecuta la cadena completa: Director → Arquitecto → Auditor → Redactor.
Ejecutar: python test_writer.py
"""

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


def main() -> None:
    # --- Input del Tenant ---
    rules = TenantRules(
        tenant_id="COL-ING",
        tenant_name="Colegio de Ingenieros",
        min_total_hours=20,
        max_total_hours=40,
        min_module_hours=4,
        max_module_hours=10,
        required_bloom_levels=[
            BloomLevel.REMEMBER,
            BloomLevel.APPLY,
            BloomLevel.ANALYZE,
        ],
        min_lessons_per_module=2,
        max_lessons_per_module=5,
        custom_restrictions="Incluir estudio de caso obligatorio por módulo",
    )

    # --- Input del Instructor ---
    instructor = InstructorInput(
        topic="Diseño de Estructuras de Acero",
        target_audience="Ingenieros civiles con 2+ años de experiencia",
    )

    # --- Paso 1: Director ---
    print("[1/4] Ejecutando DirectorAgent...")
    director = DirectorAgent()
    msg_director = director.process(rules, instructor)
    brief = DirectorBrief(**msg_director.payload)
    print(f"      Brief generado: {brief.course_id}")

    # --- Paso 2: Arquitecto ---
    print("[2/4] Ejecutando ArchitectAgent...")
    architect = ArchitectAgent()
    msg_architect = architect.process(brief)
    matrix = CourseMatrix(**msg_architect.payload)
    print(f"      Matriz generada: {len(matrix.modules)} módulos, {matrix.total_estimated_hours}h")

    # --- Paso 3: Auditor ---
    print("[3/4] Ejecutando AuditorAgent...")
    auditor = AuditorAgent()
    msg_auditor = auditor.process(brief, matrix)
    report = msg_auditor.payload
    print(f"      Auditoría: {report['status'].upper()} | Issues: {report['total_issues']}")

    if report["status"] != ValidationStatus.APPROVED.value:
        print("      ⛔ El curso NO fue aprobado. No se puede continuar con el Redactor.")
        print(f"      Resumen: {report['summary']}")
        return

    # --- Paso 4: Redactor ---
    print("[4/4] Ejecutando WriterAgent...")
    writer = WriterAgent()
    msg_writer = writer.process(matrix)
    content = CourseContent(**msg_writer.payload)
    print(f"      Contenido generado: {len(content.lessons_content)} lecciones")

    # --- Imprimir resultados ---
    print()
    print("=" * 60)
    print("RESULTADO DEL REDACTOR (CADENA COMPLETA)")
    print("=" * 60)
    print(f"Course ID:    {content.course_id}")
    print(f"Título:       {content.course_title}")
    print(f"Lecciones:    {len(content.lessons_content)}")
    print(f"Generado:     {content.generated_at}")
    print("=" * 60)

    for lc in content.lessons_content:
        print(f"\n{'─' * 60}")
        print(f"📄 {lc.lesson_id}: {lc.title} ({lc.estimated_hours}h)")
        print(f"{'─' * 60}")
        print(f"Contenido: {len(lc.full_content)} caracteres")
        print(f"\n  ACTIVIDADES ({len(lc.activities)}):")
        for act in lc.activities:
            print(f"    • {act}")
        print(f"\n  CRITERIOS DE EVALUACIÓN ({len(lc.assessment_criteria)}):")
        for crit in lc.assessment_criteria:
            print(f"    ✓ {crit}")
        print(f"\n  VISTA PREVIA DEL CONTENIDO (primeros 300 chars):")
        preview = lc.full_content[:300].replace("\n", " ")
        print(f"    {preview}...")

    print(f"\n{'=' * 60}")
    print("WriterAgent OK — CADENA COMPLETA FUNCIONAL")
    print("=" * 60)


if __name__ == "__main__":
    main()