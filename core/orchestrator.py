"""
orchestrator.py
Orquestador del motor de IA curricular (lógica pura de coordinación).
Ejecuta la cadena completa de agentes:
    Director → Arquitecto → Auditor → Redactor
con manejo de errores y loop de revisión funcional.

Este módulo es PURO: no escribe a disco, no imprime por consola, no hace
sys.exit y no contiene datos de ejemplo. El IO (guardado a archivo, banner)
vive en el punto de entrada del CLI (main.py) y la persistencia en BD vive
en la capa API (api/app/services/course_generator.py + router).

Es el ÚNICO lugar con la lógica de orquestación; tanto el CLI como la API
lo reutilizan, de modo que no exista cadena duplicada ni divergente.
"""
import logging

from domain.models import (
    TenantRules,
    InstructorInput,
    DirectorBrief,
    CourseMatrix,
    CourseContent,
    QualityReport,
    RevisionFeedback,
    ValidationStatus,
)
from agents.director import DirectorAgent
from agents.architect import ArchitectAgent
from agents.auditor import AuditorAgent
from agents.writer import WriterAgent
from config.settings import get_settings


class Orchestrator:
    """
    Orquestador principal.
    Coordina la ejecución secuencial de los 4 agentes con un loop de
    revisión funcional: si el Auditor no aprueba, el Arquitecto re-diseña
    aplicando el feedback estructurado del Auditor (no regenera a ciegas).

    `run` es puro: retorna el resultado como dicts y NO toca el disco.
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
    ) -> dict | None:
        """
        Ejecuta la cadena completa de agentes.

        Args:
            tenant_rules: Reglas de acreditación del Tenant.
            instructor_input: Input del instructor.
        Returns:
            dict con claves "course_matrix", "quality_report", "course_content"
            (los tres como dicts listos para persistir en JSON), o None si la
            cadena falla tras todos los intentos.
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

        # --- Paso 2 + 3: Arquitecto + Auditor (loop de revisión funcional) ---
        matrix: CourseMatrix | None = None
        report: QualityReport | None = None
        feedback: RevisionFeedback | None = None
        max_retries = self._settings.max_retries_per_agent

        for attempt in range(1, max_retries + 1):
            self._logger.info(
                "[FASE 2] Ejecutando ArchitectAgent (intento %d/%d)...",
                attempt,
                max_retries,
            )

            # Arquitecto: diseño inicial o revisión con feedback
            try:
                if feedback is None:
                    msg_architect = self._architect.process(brief)
                else:
                    msg_architect = self._architect.revise(brief, feedback)
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
                report = QualityReport(**msg_auditor.payload)
                self._logger.info(
                    "[FASE 3] OK | Estado: %s | Issues: %d (críticos: %d)",
                    report.status.value.upper(),
                    report.total_issues,
                    report.critical_issues,
                )
                if report.status == ValidationStatus.APPROVED:
                    self._logger.info("[FASE 3] Curso APROBADO. Continuando.")
                    break
                else:
                    self._logger.warning(
                        "[FASE 3] Curso %s. Resumen: %s",
                        report.status.value.upper(),
                        report.summary,
                    )
                    if attempt == max_retries:
                        self._logger.error(
                            "[FASE 3] Agotados los reintentos. "
                            "El curso no fue aprobado."
                        )
                        return None
                    # Loop funcional: el feedback del Auditor guía la revisión.
                    feedback = report.feedback
                    self._logger.info(
                        "[FASE 3] Reintentando con el Arquitecto "
                        "(feedback: cap=%s, bloom_faltantes=%d, add_lessons=%s)...",
                        feedback.module_hours_cap if feedback else None,
                        len(feedback.missing_bloom_levels) if feedback else 0,
                        feedback.add_lessons if feedback else False,
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

        if matrix is None or report is None:
            self._logger.error("No se generó una CourseMatrix aprobada.")
            return None

        # --- Paso 4: Redactor ---
        self._logger.info("[FASE 4] Ejecutando WriterAgent...")
        try:
            # Se propaga el brief para que el Redactor aplique la intención del
            # instructor (voz, tono, objetivo, entregable, escenario y fuera de
            # alcance). `brief` nunca es None aquí: la FASE 1 lo garantiza
            # (si fallara, ya habríamos retornado None arriba).
            msg_writer = self._writer.process(matrix, brief)
            content = CourseContent(**msg_writer.payload)
            self._logger.info(
                "[FASE 4] OK | Lecciones redactadas: %d",
                len(content.lessons_content),
            )
        except Exception as e:
            self._logger.error("[FASE 4] FALLO en WriterAgent: %s", str(e))
            return None

        # --- Resultado (dicts listos para persistir) ---
        result = {
            "course_matrix": matrix.model_dump(mode="json"),
            "quality_report": report.model_dump(mode="json"),
            "course_content": content.model_dump(mode="json"),
        }

        self._logger.info("=" * 60)
        self._logger.info("CADENA COMPLETA EXITOSA")
        self._logger.info("Curso: %s", content.course_id)
        self._logger.info("Título: %s", content.course_title)
        self._logger.info("Lecciones: %d", len(content.lessons_content))
        self._logger.info("=" * 60)

        return result