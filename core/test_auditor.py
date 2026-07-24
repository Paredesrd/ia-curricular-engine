"""
test_auditor.py
Test manual del Agente Auditor de Calidad.
Ejecuta la cadena completa: Director → Arquitecto → Auditor.
Ejecutar: python test_auditor.py
"""

from domain.models import (
    TenantRules,
    InstructorInput,
    BloomLevel,
    DirectorBrief,
    CourseMatrix,
)
from agents.director import DirectorAgent
from agents.architect import ArchitectAgent
from agents.auditor import AuditorAgent


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
    print("[1/3] Ejecutando DirectorAgent...")
    director = DirectorAgent()
    msg_director = director.process(rules, instructor)
    brief = DirectorBrief(**msg_director.payload)
    print(f"      Brief generado: {brief.course_id}")

    # --- Paso 2: Arquitecto ---
    print("[2/3] Ejecutando ArchitectAgent...")
    architect = ArchitectAgent()
    msg_architect = architect.process(brief)
    matrix = CourseMatrix(**msg_architect.payload)
    print(f"      Matriz generada: {len(matrix.modules)} módulos, {matrix.total_estimated_hours}h")

    # --- Paso 3: Auditor ---
    print("[3/3] Ejecutando AuditorAgent...")
    auditor = AuditorAgent()
    msg_auditor = auditor.process(brief, matrix)
    report = msg_auditor.payload

    # --- Imprimir resultados ---
    print()
    print("=" * 60)
    print("RESULTADO DEL AUDITOR DE CALIDAD")
    print("=" * 60)
    print(f"Sender:       {msg_auditor.sender.value}")
    print(f"Receiver:     {msg_auditor.receiver.value}")
    print(f"Type:         {msg_auditor.message_type}")
    print(f"Course ID:    {report['course_id']}")
    print(f"Estado:       {report['status'].upper()}")
    print(f"Total issues: {report['total_issues']}")
    print(f"Críticos:     {report['critical_issues']}")
    print("-" * 60)
    print(f"Resumen: {report['summary']}")
    print("-" * 60)

    if report["issues"]:
        print("ISSUES DETECTADOS:")
        for issue in report["issues"]:
            severity_icon = {"critical": "🔴", "major": "🟡", "minor": "🔵"}
            icon = severity_icon.get(issue["severity"], "⚪")
            print(f"  {icon} [{issue['severity'].upper()}] {issue['component']}")
            print(f"     Problema: {issue['description']}")
            print(f"     Sugerencia: {issue['suggestion']}")
            print()
    else:
        print("✅ Sin issues detectados.")

    print("-" * 60)
    print("RECOMENDACIONES:")
    for rec in report["recommendations"]:
        print(f"  • {rec}")

    print("=" * 60)
    print(f"Destino del reporte: {msg_auditor.receiver.value}")
    print("AuditorAgent OK")


if __name__ == "__main__":
    main()