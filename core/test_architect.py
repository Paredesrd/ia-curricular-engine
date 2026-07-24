"""
test_architect.py
Test manual del Agente Arquitecto Curricular.
Ejecutar: python test_architect.py
"""

from domain.models import TenantRules, InstructorInput, BloomLevel, DirectorBrief
from agents.director import DirectorAgent
from agents.architect import ArchitectAgent


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

    # --- Paso 1: Director genera el brief ---
    director = DirectorAgent()
    msg_director = director.process(rules, instructor)
    brief = DirectorBrief(**msg_director.payload)

    # --- Paso 2: Arquitecto procesa el brief ---
    architect = ArchitectAgent()
    msg_architect = architect.process(brief)
    matrix = msg_architect.payload

    # --- Imprimir resultados ---
    print("=" * 60)
    print("RESULTADO DEL ARQUITECTO CURRICULAR")
    print("=" * 60)
    print(f"Sender:       {msg_architect.sender.value}")
    print(f"Receiver:     {msg_architect.receiver.value}")
    print(f"Type:         {msg_architect.message_type}")
    print(f"Course ID:    {matrix['course_id']}")
    print(f"Título:       {matrix['course_title']}")
    print(f"Tema:         {matrix['topic']}")
    print(f"Horas total:  {matrix['total_estimated_hours']}")
    print(f"Módulos:      {len(matrix['modules'])}")
    print("-" * 60)

    for mod in matrix["modules"]:
        print(f"  {mod['module_id']}: {mod['title']} ({mod['estimated_hours']}h)")
        for les in mod["lessons"]:
            print(
                f"    {les['lesson_id']}: {les['title']} "
                f"[{les['bloom_level']}] ({les['estimated_hours']}h)"
            )
            print(f"      Objetivo: {les['learning_objective']}")
        print()

    print("-" * 60)
    print("Distribución Bloom:")
    for level, count in matrix["bloom_distribution"].items():
        if count > 0:
            print(f"  {level}: {count} lecciones")

    print("-" * 60)
    print("Validación de restricciones:")
    total_hours = matrix["total_estimated_hours"]
    print(f"  Horas totales: {total_hours} (rango: {rules.min_total_hours}-{rules.max_total_hours}) → {'OK' if rules.min_total_hours <= total_hours <= rules.max_total_hours else 'FALLO'}")

    for mod in matrix["modules"]:
        h = mod["estimated_hours"]
        n = len(mod["lessons"])
        h_ok = rules.min_module_hours <= h <= rules.max_module_hours
        n_ok = rules.min_lessons_per_module <= n <= rules.max_lessons_per_module
        print(f"  {mod['module_id']}: {h}h {'OK' if h_ok else 'FALLO'} | {n} lecciones {'OK' if n_ok else 'FALLO'}")

    bloom_present = [k for k, v in matrix["bloom_distribution"].items() if v > 0]
    required = [b.value for b in rules.required_bloom_levels]
    bloom_ok = all(b in bloom_present for b in required)
    print(f"  Bloom requeridos {required} presentes: {'OK' if bloom_ok else 'FALLO'}")

    print("=" * 60)
    print("ArchitectAgent OK")


if __name__ == "__main__":
    main()