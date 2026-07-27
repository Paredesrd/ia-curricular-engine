"""
agents/auditor.py
Agente Auditor de Calidad: tercer agente de la cadena.
Responsabilidad única:
  - Recibir la CourseMatrix (del Arquitecto) y el DirectorBrief (del Director).
  - Validar la matriz contra TODAS las restricciones del Tenant.
  - Evaluar carga cognitiva, progresión de Bloom, consistencia estructural.
  - Tener en cuenta la INTENCIÓN del instructor (fuera de alcance y entregable
    final): lo propaga como regla al Redactor y lo deja visible como observación,
    sin bloquear (ver nota de diseño abajo).
  - Emitir un QualityReport con estado APPROVED / NEEDS_REVISION / REJECTED.
  - Si NO aprueba, adjuntar RevisionFeedback estructurado para que el
    Arquitecto pueda corregir de forma dirigida (loop funcional).
  - Envolver el reporte en un AgentMessage dirigido al Redactor (si aprobado)
    o de vuelta al Arquitecto (si necesita revisión).
El Auditor NO modifica la matriz. Solo juzga y retroalimenta.

NOTA DE DISEÑO (fuera de alcance / entregable):
Con el Arquitecto determinista actual, una violación de "fuera de alcance" o la
ausencia del entregable NO son auto-corregibles dentro del loop de revisión (el
Arquitecto regeneraría lo mismo). Por eso aquí se tratan como OBSERVACIONES
(severidad minor) + RECOMENDACIONES, nunca como fallo que bloquee: así no se
reintroduce el bug del loop ciego (reintentos idénticos -> 500), quedan visibles
en la auditoría de la UI y se propagan al Redactor, que es donde realmente se
cumplen (en el contenido). Cuando Arquitecto/Redactor sean LLM, estos chequeos
pasarán a ser bloqueantes con auto-corrección.
"""
import logging
import re
import uuid
from datetime import datetime, timezone

from domain.models import (
    DirectorBrief,
    CourseMatrix,
    QualityIssue,
    QualityReport,
    RevisionFeedback,
    AgentMessage,
    AgentRole,
    BloomLevel,
    ValidationStatus,
)
from config.settings import get_settings


# Orden natural de Bloom para validar progresión
BLOOM_ORDER: dict[BloomLevel, int] = {
    BloomLevel.REMEMBER: 0,
    BloomLevel.UNDERSTAND: 1,
    BloomLevel.APPLY: 2,
    BloomLevel.ANALYZE: 3,
    BloomLevel.EVALUATE: 4,
    BloomLevel.CREATE: 5,
}

# Prefijos que el instructor usa para declarar el fuera de alcance en lenguaje
# natural ("no hablar de X", "excluir Y"...). Se limpian antes de comparar.
_SCOPE_PREFIXES: tuple[str, ...] = (
    "no hablar de",
    "no hables de",
    "no mencionar",
    "no menciones",
    "no incluir",
    "no incluyas",
    "no tratar",
    "no trates",
    "excluir",
    "evitar",
    "sin",
)


class AuditorAgent:
    """
    Agente Auditor de Calidad.
    Valida la CourseMatrix contra las restricciones del Tenant
    y criterios pedagógicos.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._logger = logging.getLogger(
            f"{self._settings.system_name}.AuditorAgent"
        )

    # ----------------------------------------------------------------
    # MÉTODO PÚBLICO PRINCIPAL
    # ----------------------------------------------------------------
    def process(
        self, brief: DirectorBrief, matrix: CourseMatrix
    ) -> AgentMessage:
        """
        Audita la CourseMatrix contra el DirectorBrief.
        Retorna un AgentMessage con el QualityReport como payload.
        Si el estado es APPROVED → mensaje dirigido al Redactor.
        Si es NEEDS_REVISION o REJECTED → mensaje dirigido al Arquitecto,
        con RevisionFeedback adjunto.
        """
        self._logger.info(
            "AuditorAgent iniciado | Curso: %s | Módulos: %d",
            matrix.course_id,
            len(matrix.modules),
        )

        issues: list[QualityIssue] = []

        issues.extend(self._check_total_hours(matrix, brief))
        issues.extend(self._check_module_hours(matrix, brief))
        issues.extend(self._check_lessons_per_module(matrix, brief))
        issues.extend(self._check_bloom_coverage(matrix, brief))
        issues.extend(self._check_bloom_progression(matrix))
        issues.extend(self._check_cognitive_load(matrix, brief))
        issues.extend(self._check_structural_integrity(matrix))
        issues.extend(self._check_content_minimums(matrix))
        # Intención del instructor: observaciones no bloqueantes + regla al Redactor.
        issues.extend(self._check_intent_alignment(brief, matrix))

        status = self._determine_status(issues)
        critical_count = sum(1 for i in issues if i.severity == "critical")

        # Feedback estructurado SOLO si no fue aprobado.
        feedback: RevisionFeedback | None = None
        if status != ValidationStatus.APPROVED:
            feedback = self._build_feedback(brief, matrix, issues)

        report = QualityReport(
            course_id=matrix.course_id,
            status=status,
            total_issues=len(issues),
            critical_issues=critical_count,
            issues=issues,
            summary=self._build_summary(matrix, issues, status),
            recommendations=self._build_recommendations(issues, brief),
            feedback=feedback,
        )

        self._logger.info(
            "QualityReport emitido | Curso: %s | Estado: %s | "
            "Issues: %d (críticos: %d)",
            report.course_id,
            report.status.value,
            report.total_issues,
            report.critical_issues,
        )

        if status == ValidationStatus.APPROVED:
            receiver = AgentRole.WRITER
        else:
            receiver = AgentRole.ARCHITECT

        message = AgentMessage(
            sender=AgentRole.AUDITOR,
            receiver=receiver,
            message_type="quality_report",
            payload=report.model_dump(mode="json"),
            timestamp=self._now_iso(),
        )
        self._logger.info(
            "AgentMessage emitido: Auditor → %s | Tipo: %s",
            receiver.value,
            message.message_type,
        )
        return message

    # ----------------------------------------------------------------
    # BLOQUE 1: VALIDACIÓN DE HORAS
    # ----------------------------------------------------------------
    def _check_total_hours(
        self, matrix: CourseMatrix, brief: DirectorBrief
    ) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        if matrix.total_estimated_hours < brief.min_total_hours:
            issues.append(self._make_issue(
                severity="critical",
                component=matrix.course_id,
                description=(
                    f"Horas totales ({matrix.total_estimated_hours:.1f}) "
                    f"por debajo del mínimo requerido ({brief.min_total_hours})."
                ),
                suggestion=(
                    f"Agregar más lecciones o módulos para alcanzar al menos "
                    f"{brief.min_total_hours} horas."
                ),
            ))
        if matrix.total_estimated_hours > brief.max_total_hours:
            issues.append(self._make_issue(
                severity="critical",
                component=matrix.course_id,
                description=(
                    f"Horas totales ({matrix.total_estimated_hours:.1f}) "
                    f"exceden el máximo permitido ({brief.max_total_hours})."
                ),
                suggestion=(
                    f"Reducir lecciones o módulos para no exceder "
                    f"{brief.max_total_hours} horas."
                ),
            ))
        return issues

    def _check_module_hours(
        self, matrix: CourseMatrix, brief: DirectorBrief
    ) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        for module in matrix.modules:
            if module.estimated_hours < brief.min_module_hours:
                issues.append(self._make_issue(
                    severity="major",
                    component=module.module_id,
                    description=(
                        f"Módulo '{module.title}' tiene {module.estimated_hours:.1f}h, "
                        f"por debajo del mínimo ({brief.min_module_hours}h)."
                    ),
                    suggestion=(
                        f"Agregar contenido o lecciones al módulo para alcanzar "
                        f"al menos {brief.min_module_hours}h."
                    ),
                ))
            if module.estimated_hours > brief.max_module_hours:
                issues.append(self._make_issue(
                    severity="major",
                    component=module.module_id,
                    description=(
                        f"Módulo '{module.title}' tiene {module.estimated_hours:.1f}h, "
                        f"excede el máximo ({brief.max_module_hours}h)."
                    ),
                    suggestion=(
                        f"Dividir el módulo o redistribuir lecciones para no "
                        f"exceder {brief.max_module_hours}h."
                    ),
                ))
        return issues

    # ----------------------------------------------------------------
    # BLOQUE 2: VALIDACIÓN DE LECCIONES
    # ----------------------------------------------------------------
    def _check_lessons_per_module(
        self, matrix: CourseMatrix, brief: DirectorBrief
    ) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        for module in matrix.modules:
            num_lessons = len(module.lessons)
            if num_lessons < brief.min_lessons_per_module:
                issues.append(self._make_issue(
                    severity="major",
                    component=module.module_id,
                    description=(
                        f"Módulo '{module.title}' tiene {num_lessons} lecciones, "
                        f"por debajo del mínimo ({brief.min_lessons_per_module})."
                    ),
                    suggestion=(
                        f"Agregar al menos {brief.min_lessons_per_module - num_lessons} "
                        f"lección(es) adicional(es)."
                    ),
                ))
            if num_lessons > brief.max_lessons_per_module:
                issues.append(self._make_issue(
                    severity="major",
                    component=module.module_id,
                    description=(
                        f"Módulo '{module.title}' tiene {num_lessons} lecciones, "
                        f"excede el máximo ({brief.max_lessons_per_module})."
                    ),
                    suggestion=(
                        f"Reducir a máximo {brief.max_lessons_per_module} lecciones "
                        f"o redistribuir en otro módulo."
                    ),
                ))
        return issues

    # ----------------------------------------------------------------
    # BLOQUE 3: VALIDACIÓN DE BLOOM
    # ----------------------------------------------------------------
    def _check_bloom_coverage(
        self, matrix: CourseMatrix, brief: DirectorBrief
    ) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        for level in brief.required_bloom_levels:
            count = matrix.bloom_distribution.get(level, 0)
            if count == 0:
                issues.append(self._make_issue(
                    severity="critical",
                    component=matrix.course_id,
                    description=(
                        f"Nivel de Bloom requerido '{level.value}' no está "
                        f"presente en ninguna lección del curso."
                    ),
                    suggestion=(
                        f"Agregar al menos una lección con nivel de Bloom "
                        f"'{level.value}'."
                    ),
                ))
        return issues

    def _check_bloom_progression(
        self, matrix: CourseMatrix
    ) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        for module in matrix.modules:
            if len(module.lessons) < 2:
                continue
            for i in range(1, len(module.lessons)):
                prev_level = module.lessons[i - 1].bloom_level
                curr_level = module.lessons[i].bloom_level
                prev_order = BLOOM_ORDER[prev_level]
                curr_order = BLOOM_ORDER[curr_level]

                if curr_order - prev_order > 2:
                    issues.append(self._make_issue(
                        severity="minor",
                        component=module.lessons[i].lesson_id,
                        description=(
                            f"Salto cognitivo abrupto en módulo '{module.title}': "
                            f"de '{prev_level.value}' a '{curr_level.value}' "
                            f"(lección {module.lessons[i].lesson_id})."
                        ),
                        suggestion=(
                            f"Considerar insertar una lección con nivel intermedio "
                            f"entre '{prev_level.value}' y '{curr_level.value}'."
                        ),
                    ))
        return issues

    # ----------------------------------------------------------------
    # BLOQUE 4: VALIDACIÓN DE CARGA COGNITIVA
    # ----------------------------------------------------------------
    def _check_cognitive_load(
        self, matrix: CourseMatrix, brief: DirectorBrief
    ) -> list[QualityIssue]:
        """
        Valida que la carga cognitiva por módulo no exceda el máximo.
        Fuente de verdad: el máximo de horas por módulo del Tenant.
        """
        issues: list[QualityIssue] = []
        max_load = float(brief.max_module_hours)
        for module in matrix.modules:
            if module.estimated_hours > max_load:
                issues.append(self._make_issue(
                    severity="major",
                    component=module.module_id,
                    description=(
                        f"Módulo '{module.title}' tiene carga cognitiva de "
                        f"{module.estimated_hours:.1f}h, excede el máximo "
                        f"permitido por el Tenant ({max_load:.1f}h)."
                    ),
                    suggestion=(
                        f"Dividir el módulo en dos o reducir lecciones para "
                        f"mantener la carga bajo {max_load:.1f}h."
                    ),
                ))
        return issues

    # ----------------------------------------------------------------
    # BLOQUE 5: VALIDACIÓN ESTRUCTURAL
    # ----------------------------------------------------------------
    def _check_structural_integrity(
        self, matrix: CourseMatrix
    ) -> list[QualityIssue]:
        issues: list[QualityIssue] = []

        module_ids = [m.module_id for m in matrix.modules]
        if len(module_ids) != len(set(module_ids)):
            issues.append(self._make_issue(
                severity="critical",
                component=matrix.course_id,
                description="Se detectaron IDs de módulo duplicados.",
                suggestion="Asignar IDs únicos a cada módulo (ej: M1, M2, M3).",
            ))

        lesson_ids: list[str] = []
        for module in matrix.modules:
            for lesson in module.lessons:
                lesson_ids.append(lesson.lesson_id)
        if len(lesson_ids) != len(set(lesson_ids)):
            issues.append(self._make_issue(
                severity="critical",
                component=matrix.course_id,
                description="Se detectaron IDs de lección duplicados.",
                suggestion="Asignar IDs únicos a cada lección (ej: M1L1, M1L2).",
            ))

        for module in matrix.modules:
            lessons_sum = round(sum(l.estimated_hours for l in module.lessons), 1)
            if abs(module.estimated_hours - lessons_sum) > 0.2:
                issues.append(self._make_issue(
                    severity="minor",
                    component=module.module_id,
                    description=(
                        f"Horas del módulo ({module.estimated_hours:.1f}h) no "
                        f"coinciden con la suma de lecciones ({lessons_sum:.1f}h)."
                    ),
                    suggestion="Recalcular las horas del módulo como suma de sus lecciones.",
                ))
        return issues

    # ----------------------------------------------------------------
    # BLOQUE 6: VALIDACIÓN DE CONTENIDO MÍNIMO
    # ----------------------------------------------------------------
    def _check_content_minimums(
        self, matrix: CourseMatrix
    ) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        for module in matrix.modules:
            for lesson in module.lessons:
                if len(lesson.learning_objective.strip()) < 10:
                    issues.append(self._make_issue(
                        severity="major",
                        component=lesson.lesson_id,
                        description=(
                            f"Lección '{lesson.title}' tiene un objetivo de "
                            f"aprendizaje demasiado corto o vacío."
                        ),
                        suggestion=(
                            "Redactar un objetivo de aprendizaje específico, "
                            "medible y con verbo de acción según Bloom."
                        ),
                    ))
                if len(lesson.key_topics) == 0:
                    issues.append(self._make_issue(
                        severity="major",
                        component=lesson.lesson_id,
                        description=(
                            f"Lección '{lesson.title}' no tiene temas clave definidos."
                        ),
                        suggestion="Definir al menos 2-3 temas clave por lección.",
                    ))
                if len(lesson.title.strip()) < 3:
                    issues.append(self._make_issue(
                        severity="minor",
                        component=lesson.lesson_id,
                        description=(
                            f"Lección '{lesson.lesson_id}' tiene un título "
                            f"demasiado corto."
                        ),
                        suggestion="Asignar un título descriptivo de al menos 3 caracteres.",
                    ))
        return issues

    # ----------------------------------------------------------------
    # BLOQUE 7: ALINEACIÓN CON LA INTENCIÓN (no bloqueante)
    # ----------------------------------------------------------------
    def _check_intent_alignment(
        self, brief: DirectorBrief, matrix: CourseMatrix
    ) -> list[QualityIssue]:
        """
        Observaciones sobre fuera de alcance y entregable final.
        Siempre severidad 'minor': no cambian el estado ni disparan el loop
        (no son auto-corregibles por el Arquitecto determinista). Quedan
        visibles en la auditoría y se propagan al Redactor vía recomendaciones.
        """
        issues: list[QualityIssue] = []
        if not brief.out_of_scope and not brief.final_deliverable:
            return issues

        matrix_text = self._matrix_searchable_text(matrix)

        # Fuera de alcance: si alguna frase declarada aparece en la estructura,
        # avisar (minor) para que el Redactor no la cuele en el contenido.
        if brief.out_of_scope:
            for phrase in self._scope_phrases(brief.out_of_scope):
                if phrase and phrase in matrix_text:
                    issues.append(self._make_issue(
                        severity="minor",
                        component=matrix.course_id,
                        description=(
                            f"El instructor marcó como fuera de alcance "
                            f"«{phrase}», pero aparece en la estructura del curso."
                        ),
                        suggestion=(
                            "El Redactor debe omitir este tema al generar el "
                            "contenido de las lecciones."
                        ),
                    ))

        # Entregable: si ninguna palabra significativa aparece en la estructura,
        # sugerir anclarlo en el cierre (minor, no bloquea).
        if brief.final_deliverable:
            words = [
                w for w in brief.final_deliverable.lower().split() if len(w) > 5
            ]
            anchored = any(w and w in matrix_text for w in words[:6])
            if not anchored:
                issues.append(self._make_issue(
                    severity="minor",
                    component=matrix.course_id,
                    description=(
                        f"El entregable final («{brief.final_deliverable}») no se "
                        f"refleja explícitamente en la estructura del curso."
                    ),
                    suggestion=(
                        "Asegura que el módulo de cierre consolide y entregue "
                        "este artefacto al alumno."
                    ),
                ))
        return issues

    def _matrix_searchable_text(self, matrix: CourseMatrix) -> str:
        """Texto concatenado de la matriz (en minúsculas) para búsquedas."""
        parts: list[str] = [matrix.course_title, matrix.topic]
        for module in matrix.modules:
            parts.append(module.title)
            parts.append(module.description)
            for lesson in module.lessons:
                parts.append(lesson.title)
                parts.append(lesson.learning_objective)
                parts.extend(lesson.key_topics)
        return " ".join(parts).lower()

    def _scope_phrases(self, raw: str) -> list[str]:
        """
        Parte el fuera de alcance en frases significativas (>= 3 palabras),
        limpiando prefijos del tipo 'no hablar de'. En minúsculas.
        """
        chunks = re.split(r"[,;\n.]+", raw)
        phrases: list[str] = []
        for chunk in chunks:
            item = chunk.strip().lower()
            if not item:
                continue
            for prefix in _SCOPE_PREFIXES:
                if item.startswith(prefix):
                    item = item[len(prefix):].strip()
                    break
            item = item.strip(" -:–—")
            if len(item.split()) >= 3:
                phrases.append(item)
        return phrases

    # ----------------------------------------------------------------
    # MÉTODOS PRIVADOS - FEEDBACK / UTILIDADES
    # ----------------------------------------------------------------
    def _build_feedback(
        self,
        brief: DirectorBrief,
        matrix: CourseMatrix,
        issues: list[QualityIssue],
    ) -> RevisionFeedback:
        """
        Construye el feedback estructurado para el Arquitecto a partir de los
        issues detectados. Es lo que hace que el loop de revisión corrija de
        verdad en vez de regenerar a ciegas.
        """
        # Bloom faltantes (críticos de cobertura)
        missing: list[BloomLevel] = []
        for level in brief.required_bloom_levels:
            if matrix.bloom_distribution.get(level, 0) == 0:
                missing.append(level)

        # ¿Hay déficit de lecciones/horas en algún módulo?
        add_lessons = any(
            len(m.lessons) < brief.min_lessons_per_module
            or m.estimated_hours < brief.min_module_hours
            for m in matrix.modules
        )

        notes = [issue.suggestion for issue in issues if issue.severity != "minor"]

        return RevisionFeedback(
            module_hours_cap=float(brief.max_module_hours),
            missing_bloom_levels=missing,
            add_lessons=add_lessons,
            notes=notes,
        )

    def _make_issue(
        self,
        severity: str,
        component: str,
        description: str,
        suggestion: str,
    ) -> QualityIssue:
        return QualityIssue(
            issue_id=f"ISS-{uuid.uuid4().hex[:6].upper()}",
            severity=severity,
            component=component,
            description=description,
            suggestion=suggestion,
        )

    def _determine_status(
        self, issues: list[QualityIssue]
    ) -> ValidationStatus:
        severities = [i.severity for i in issues]
        if "critical" in severities:
            return ValidationStatus.REJECTED
        if "major" in severities:
            return ValidationStatus.NEEDS_REVISION
        return ValidationStatus.APPROVED

    def _build_summary(
        self,
        matrix: CourseMatrix,
        issues: list[QualityIssue],
        status: ValidationStatus,
    ) -> str:
        critical = sum(1 for i in issues if i.severity == "critical")
        major = sum(1 for i in issues if i.severity == "major")
        minor = sum(1 for i in issues if i.severity == "minor")
        if status == ValidationStatus.APPROVED:
            return (
                f"El curso '{matrix.course_title}' ({matrix.course_id}) "
                f"CUMPLE todas las restricciones del Tenant. "
                f"{len(matrix.modules)} módulos, "
                f"{matrix.total_estimated_hours:.1f}h totales. "
                f"Issues menores: {minor}. Aprobado para redacción."
            )
        elif status == ValidationStatus.NEEDS_REVISION:
            return (
                f"El curso '{matrix.course_title}' ({matrix.course_id}) "
                f"requiere REVISIÓN antes de continuar. "
                f"Issues: {critical} críticos, {major} mayores, {minor} menores. "
                f"Se devuelve al Arquitecto para corrección."
            )
        else:
            return (
                f"El curso '{matrix.course_title}' ({matrix.course_id}) "
                f"ha sido RECHAZADO. "
                f"Issues: {critical} críticos, {major} mayores, {minor} menores. "
                f"Requiere rediseño significativo por parte del Arquitecto."
            )

    def _build_recommendations(
        self, issues: list[QualityIssue], brief: DirectorBrief
    ) -> list[str]:
        recommendations: list[str] = []
        critical_issues = [i for i in issues if i.severity == "critical"]
        major_issues = [i for i in issues if i.severity == "major"]
        if critical_issues:
            recommendations.append(
                f"Resolver {len(critical_issues)} issue(s) crítico(s) "
                f"de forma prioritaria antes de cualquier otro ajuste."
            )
        if major_issues:
            recommendations.append(
                f"Corregir {len(major_issues)} issue(s) mayor(es) "
                f"para cumplir con las restricciones del Tenant."
            )
        if not issues:
            recommendations.append(
                "La matriz curricular cumple todos los criterios. "
                "Proceder con la redacción de contenido."
            )

        bloom_issues = [
            i for i in issues
            if "progresión" in i.description.lower()
            or "salto" in i.description.lower()
        ]
        if bloom_issues:
            recommendations.append(
                "Revisar la progresión cognitiva entre lecciones para "
                "garantizar una transición pedagógica suave entre niveles de Bloom."
            )

        # Reglas de intención propagadas al Redactor (visibles en la auditoría).
        if brief.out_of_scope:
            recommendations.append(
                f"FUERA DE ALCANCE (el Redactor debe respetarlo al redactar): "
                f"{brief.out_of_scope}"
            )
        if brief.final_deliverable:
            recommendations.append(
                f"ENTREGABLE FINAL a consolidar en el cierre del curso: "
                f"{brief.final_deliverable}"
            )
        return recommendations

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()