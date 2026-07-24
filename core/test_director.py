"""
test_director.py
Test manual del Agente Director.
Ejecutar: python test_director.py
"""

from domain.models import TenantRules, InstructorInput, BloomLevel
from agents.director import DirectorAgent


def main() -> None:
    # --- Input del Tenant (reglas de acreditación) ---
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

    # --- Input del Instructor (solo el tema) ---
    instructor = InstructorInput(
        topic="Diseño de Estructuras de Acero",
        target_audience="Ingenieros civiles con 2+ años de experiencia",
    )

    # --- Ejecutar el Director ---
    director = DirectorAgent()
    msg = director.process(rules, instructor)

    # --- Imprimir resultados ---
    print("=" * 60)
    print("RESULTADO DEL AGENTE DIRECTOR")
    print("=" * 60)
    print(f"Sender:      {msg.sender.value}")
    print(f"Receiver:    {msg.receiver.value}")
    print(f"Type:        {msg.message_type}")
    print(f"Course ID:   {msg.payload['course_id']}")
    print(f"Topic:       {msg.payload['topic']}")
    print(f"Audience:    {msg.payload['target_audience']}")
    print(f"Tenant:      {msg.payload['tenant_name']}")
    print(f"Hours:       {msg.payload['min_total_hours']}-{msg.payload['max_total_hours']}")
    print(f"Bloom:       {[b for b in msg.payload['required_bloom_levels']]}")
    print(f"Timestamp:   {msg.timestamp}")
    print("-" * 60)
    print(f"RESTRICCIONES ({len(msg.payload['constraints_summary'])} reglas):")
    for i, c in enumerate(msg.payload["constraints_summary"], 1):
        print(f"  {i}. {c}")
    print("=" * 60)
    print("DirectorAgent OK")


if __name__ == "__main__":
    main()