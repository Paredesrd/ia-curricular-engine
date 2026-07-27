"""
main.py
Punto de entrada CLI del motor de IA curricular.

Ejecuta la cadena completa vía el orquestador puro (orchestrator.Orchestrator)
con datos de ejemplo y guarda el resultado en core/output/.

La lógica de orquestación vive en orchestrator.py (pura y reutilizable por la
API). Este archivo solo contiene el IO del CLI: datos de ejemplo, guardado a
archivo y banner por consola. Cada archivo cumple así una función única.

Ejecutar (desde core/):
    python main.py
"""
import json
import logging
import sys
from pathlib import Path

from domain.models import (
    TenantRules,
    InstructorInput,
    BloomLevel,
)
from orchestrator import Orchestrator
from config.settings import get_settings, setup_logging, OUTPUT_DIR

# Re-export para compatibilidad con imports existentes (tests, etc.).
__all__ = ["Orchestrator", "main"]


# ============================================================
# PERSISTENCIA (IO exclusivo del CLI)
# ============================================================
def _save_output(course_content: dict) -> Path:
    """
    Guarda el course_content (dict ya serializable a JSON) en core/output/.
    Es IO exclusivo del CLI; el orquestador (Orchestrator.run) es puro y no
    toca el disco, de modo que la API puede reutilizarlo sin efectos secundarios.
    """
    settings = get_settings()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = OUTPUT_DIR / f"{course_content['course_id']}.json"
    with open(filepath, "w", encoding=settings.output_encoding) as f:
        json.dump(course_content, f, ensure_ascii=False, indent=2)
    return filepath


# ============================================================
# EJECUCIÓN DIRECTA
# ============================================================
def main() -> None:
    """Punto de entrada del sistema (CLI)."""
    logger = setup_logging()

    # --- Datos de ejemplo (en Fase 2 vendrán de la API) ---
    tenant_rules = TenantRules(
        tenant_id="COL-ING",
        tenant_name="Colegio de Ingenieros del Perú",
        min_total_hours=20,
        max_total_hours=40,
        min_module_hours=4,
        max_module_hours=10,
        required_bloom_levels=[
            BloomLevel.REMEMBER,
            BloomLevel.UNDERSTAND,
            BloomLevel.APPLY,
            BloomLevel.ANALYZE,
        ],
        min_lessons_per_module=2,
        max_lessons_per_module=5,
        custom_restrictions=(
            "Cada módulo debe incluir al menos un estudio de caso "
            "basado en la normativa peruana vigente (E.090)."
        ),
    )
    instructor_input = InstructorInput(
        topic="Diseño de Estructuras de Acero",
        target_audience="Ingenieros civiles colegiados con 2+ años de experiencia",
        additional_context=(
            "El curso debe alinearse con la norma E.090 del Reglamento "
            "Nacional de Edificaciones del Perú."
        ),
    )

    # --- Ejecutar orquestador (lógica pura) ---
    orchestrator = Orchestrator()
    result = orchestrator.run(tenant_rules, instructor_input)

    if result is None:
        logger.error("El sistema no pudo generar el curso.")
        sys.exit(1)

    # --- IO exclusivo del CLI: guardar y mostrar ---
    content = result["course_content"]
    output_path = _save_output(content)
    logger.info("Output guardado: %s", output_path.resolve())

    print()
    print("=" * 60)
    print("  MOTOR DE IA CURRICULAR - RESULTADO FINAL")
    print("=" * 60)
    print(f"  Curso:      {content['course_id']}")
    print(f"  Título:     {content['course_title']}")
    print(f"  Lecciones:  {len(content['lessons_content'])}")
    print(f"  Generado:   {content['generated_at']}")
    print(f"  Output:     {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()