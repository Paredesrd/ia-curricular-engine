"""
main.py
Orquestador del motor de IA curricular.

Ejecuta la cadena completa de agentes:
  Director → Arquitecto → Auditor → Redactor

Con manejo de errores, reintentos y persistencia de resultados.

Ejecutar:
  python main.py
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

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
from config.settings import get_settings, setup_logging, OUTPUT_DIR


class Orchestrator:
    """
    Orquestador principal.
    Coordina la ejecución secuencial de los 4 agentes
    con manejo de errores y reintentos.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._logger = logging.getLogger(
            f"{self._settings.system_name}.Orchestrator"
        )
        self._director = DirectorAgent()
        self._architect = ArchitectAgent()
        self._auditor = AuditorAgent()
        self._writer = WriterAgent()

    # ----------------------------------------------------------------
    # MÉTODO PÚBLICO PRINCIPAL
    # ----------------------------------------------------------------

    def run(
        self,
        tenant_rules: TenantRules,
        instructor_input: InstructorInput,
    ) -> CourseContent | None:
        """
        Ejecuta la cadena completa de agentes.

        Args:
            tenant_rules: Reglas de acreditación del Tenant.
            instructor_input: Input del instructor.

        Returns:
            CourseContent si la cadena completa exitosamente.
            None si falla después de todos los reintentos.
        """
        self._logger.info("=" * 60)
        self._logger.info("ORQUESTADOR INICIADO")
        self._logger.info("Tenant: %s", tenant_rules.tenant_name)
        self._logger.info("Tema: %s", instructor_input.topic)
        self._logger.info("=" * 60)

        # --- Paso 1: Director ---
        self._logger.info("[FASE 1] Ejecutando DirectorAgent...")
        try:
            msg_director = self._director.process(tenant_rules, instructor_input)
            brief = DirectorBrief(**msg_director.payload)
            self._logger.info(
                "[FASE 1] OK | Brief: %s | Restricciones: %d",
                brief.course_id,
                len(brief.constraints_summary),
            )
        except Exception as e:
            self._logger.error("[FASE 1] FALLO en DirectorAgent: %s", str(e))
            return None

        # --- Paso 2 + 3: Arquitecto + Auditor (con reintentos) ---
        matrix: CourseMatrix | None = None
        max_retries = self._settings.max_retries_per_agent

        for attempt in range(1, max_retries + 1):
            self._logger.info(
                "[FASE 2] Ejecutando ArchitectAgent (intento %d/%d)...",
                attempt,
                max_retries,
            )

            # Arquitecto
            try:
                msg_architect = self._architect.process(brief)
                matrix = CourseMatrix(**msg_architect.payload)
                self._logger.info(
                    "[FASE 2] OK | Módulos: %d | Horas: %.1f",
                    len(matrix.modules),
                    matrix.total_estimated_hours,
                )
            except Exception as e:
                self._logger.error(
                    "[FASE 2] FALLO en ArchitectAgent (intento %d): %s",
                    attempt,
                    str(e),
                )
                if attempt == max_retries:
                    self._logger.error(
                        "[FASE 2] Agotados los reintentos. Abortando."
                    )
                    return None
                continue

            # Auditor
            self._logger.info("[FASE 3] Ejecutando AuditorAgent...")
            try:
                msg_auditor = self._auditor.process(brief, matrix)
                report = msg_auditor.payload
                status = report["status"]
                self._logger.info(
                    "[FASE 3] OK | Estado: %s | Issues: %d (críticos: %d)",
                    status.upper(),
                    report["total_issues"],
                    report["critical_issues"],
                )

                if status == ValidationStatus.APPROVED.value:
                    self._logger.info("[FASE 3] Curso APROBADO. Continuando.")
                    break
                else:
                    self._logger.warning(
                        "[FASE 3] Curso %s. Resumen: %s",
                        status.upper(),
                        report["summary"],
                    )
                    if attempt == max_retries:
                        self._logger.error(
                            "[FASE 3] Agotados los reintentos. "
                            "El curso no fue aprobado."
                        )
                        return None
                    self._logger.info(
                        "[FASE 3] Reintentando con el Arquitecto..."
                    )

            except Exception as e:
                self._logger.error(
                    "[FASE 3] FALLO en AuditorAgent (intento %d): %s",
                    attempt,
                    str(e),
                )
                if attempt == max_retries:
                    self._logger.error(
                        "[FASE 3] Agotados los reintentos. Abortando."
                    )
                    return None

        if matrix is None:
            self._logger.error("No se generó una CourseMatrix válida.")
            return None

        # --- Paso 4: Redactor ---
        self._logger.info("[FASE 4] Ejecutando WriterAgent...")
        try:
            msg_writer = self._writer.process(matrix)
            content = CourseContent(**msg_writer.payload)
            self._logger.info(
                "[FASE 4] OK | Lecciones redactadas: %d",
                len(content.lessons_content),
            )
        except Exception as e:
            self._logger.error("[FASE 4] FALLO en WriterAgent: %s", str(e))
            return None

        # --- Persistencia ---
        self._save_output(content)

        self._logger.info("=" * 60)
        self._logger.info("CADENA COMPLETA EXITOSA")
        self._logger.info("Curso: %s", content.course_id)
        self._logger.info("Título: %s", content.course_title)
        self._logger.info("Lecciones: %d", len(content.lessons_content))
        self._logger.info("=" * 60)

        return content

    # ----------------------------------------------------------------
    # MÉTODOS PRIVADOS
    # ----------------------------------------------------------------

    def _save_output(self, content: CourseContent) -> None:
        """Guarda el CourseContent en un archivo JSON."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{content.course_id}.json"
        filepath = OUTPUT_DIR / filename

        data = content.model_dump(mode="json")

        with open(filepath, "w", encoding=self._settings.output_encoding) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self._logger.info("Output guardado: %s", filepath.resolve())


# ============================================================
# EJECUCIÓN DIRECTA
# ============================================================

def main() -> None:
    """Punto de entrada del sistema."""
    # Configurar logging
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

    # --- Ejecutar orquestador ---
    orchestrator = Orchestrator()
    result = orchestrator.run(tenant_rules, instructor_input)

    if result is None:
        logger.error("El sistema no pudo generar el curso.")
        sys.exit(1)

    # --- Resumen final por consola ---
    print()
    print("=" * 60)
    print("  MOTOR DE IA CURRICULAR - RESULTADO FINAL")
    print("=" * 60)
    print(f"  Curso:      {result.course_id}")
    print(f"  Título:     {result.course_title}")
    print(f"  Lecciones:  {len(result.lessons_content)}")
    print(f"  Generado:   {result.generated_at}")
    print(f"  Output:     {OUTPUT_DIR / f'{result.course_id}.json'}")
    print("=" * 60)


if __name__ == "__main__":
    main()