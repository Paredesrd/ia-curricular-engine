"""
agents/auditor.py
Agente Auditor de Calidad: tercer agente de la cadena.

Responsabilidad única:
  - Recibir la CourseMatrix (del Arquitecto) y el DirectorBrief (del Director).
  - Validar la matriz contra TODAS las restricciones del Tenant.
  - Evaluar carga cognitiva, progresión de Bloom, consistencia estructural.
  - Emitir un QualityReport con estado APPROVED / NEEDS_REVISION / REJECTED.
  - Envolver el reporte en un AgentMessage dirigido al Redactor (si aprobado)
    o de vuelta al Arquitecto (si necesita revisión).

El Auditor NO modifica la matriz. Solo juzga.
"""

import logging
import uuid
from datetime import datetime, timezone

from domain.models import (
    DirectorBrief,
    CourseMatrix,
    Module,
    Lesson,
    QualityIssue,
    QualityReport,
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
        Si es NEEDS_REVISION o REJECTED → mensaje dirigido al Arquitecto.

        Args:
            brief: DirectorBrief con las restricciones del Tenant.
            matrix: CourseMatrix a auditar.

        Returns:
            AgentMessage con message_type='quality_report'.
        """
        self._logger.info(
            "AuditorAgent iniciado | Curso: %s | Módulos: %d",
            matrix.course_id,
            len(matrix.modules),
        )

        issues: list[QualityIssue] = []

        # --- Bloque 1: Validación de horas ---
        issues.extend(self._check_total_hours(matrix, brief))
        issues.extend(self._check_module_hours(matrix, brief))

        # --- Bloque 2: Validación de lecciones ---
        issues.extend(self._check_lessons_per_module(matrix, brief))

        # --- Bloque 3: Validación de Bloom ---
        issues.extend(self._check_bloom_coverage(matrix, brief))
        issues.extend(self._check_bloom_progression(matrix))

        # --- Bloque 4: Validación de carga cognitiva ---
        issues.extend(self._check_cognitive_load(matrix))

        # --- Bloque 5: Validación estructural ---
        issues.extend(self._check_structural_integrity(matrix))

        # --- Bloque 6: Validación de contenido mínimo ---
        issues.extend(self._check_content_minimums(matrix))

        # --- Determinar estado ---
        status = self._determine_status(issues)
        critical_count = sum(1 for i in issues if i.severity == "critical")

        # --- Construir reporte ---
        report = QualityReport(
            course_id=matrix.course_id,
            status=status,
            total_issues=len(issues),
            critical_issues=critical_count,
            issues=issues,
            summary=self._build_summary(matrix, issues, status),
            recommendations=self._build_recommendations(issues),
        )

        self._logger.info(
            "QualityReport emitido | Curso: %s | Estado: %s | "
            "Issues: %d (críticos: %d)",
            report.course_id,
            report.status.value,
            report.total_issues,
            report.critical_issues,
        )

        # --- Determinar destinatario ---
        if status == ValidationStatus.APPROVED:
            receiver = AgentRole.WRITER
        else:
            receiver = AgentRole.ARCHITECT

        # --- Envolver en AgentMessage ---
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
        """Valida que las horas totales estén dentro del rango."""
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
        """Valida horas por módulo."""
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
        """Valida cantidad de lecciones por módulo."""
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
        """Valida que todos los niveles de Bloom requeridos estén presentes."""
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
        """
        Valida que la progresión de Bloom sea pedagógicamente lógica.
        Detecta saltos abruptos (ej: de REMEMBER a CREATE sin niveles intermedios).
        """
        issues: list[QualityIssue] = []

        for module in matrix.modules:
            if len(module.lessons) < 2:
                continue

            for i in range(1, len(module.lessons)):
                prev_level = module.lessons[i - 1].bloom_level
                curr_level = module.lessons[i].bloom_level
                prev_order = BLOOM_ORDER[prev_level]
                curr_order = BLOOM_ORDER[curr_level]

                # Salto de más de 2 niveles hacia arriba
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
        self, matrix: CourseMatrix
    ) -> list[QualityIssue]:
        """
        Valida que la carga cognitiva por módulo no exceda el máximo.
        Carga cognitiva = horas estimadas del módulo.
        """
        issues: list[QualityIssue] = []
        max_load = self._settings.max_cognitive_load_per_module

        for module in matrix.modules:
            if module.estimated_hours > max_load:
                issues.append(self._make_issue(
                    severity="major",
                    component=module.module_id,
                    description=(
                        f"Módulo '{module.title}' tiene carga cognitiva de "
                        f"{module.estimated_hours:.1f}h, excede el máximo "
                        f"recomendado ({max_load:.1f}h)."
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
        """Valida integridad estructural: IDs únicos, datos completos."""
        issues: list[QualityIssue] = []

        # IDs de módulo únicos
        module_ids = [m.module_id for m in matrix.modules]
        if len(module_ids) != len(set(module_ids)):
            issues.append(self._make_issue(
                severity="critical",
                component=matrix.course_id,
                description="Se detectaron IDs de módulo duplicados.",
                suggestion="Asignar IDs únicos a cada módulo (ej: M1, M2, M3).",
            ))

        # IDs de lección únicos
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

        # Verificar que las horas del módulo coinciden con la suma de lecciones
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
        """Valida que cada lección tenga contenido estructural mínimo."""
        issues: list[QualityIssue] = []

        for module in matrix.modules:
            for lesson in module.lessons:
                # Objetivo de aprendizaje
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

                # Temas clave
                if len(lesson.key_topics) == 0:
                    issues.append(self._make_issue(
                        severity="major",
                        component=lesson.lesson_id,
                        description=(
                            f"Lección '{lesson.title}' no tiene temas clave definidos."
                        ),
                        suggestion="Definir al menos 2-3 temas clave por lección.",
                    ))

                # Título
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
    # MÉTODOS PRIVADOS - UTILIDADES
    # ----------------------------------------------------------------

    def _make_issue(
        self,
        severity: str,
        component: str,
        description: str,
        suggestion: str,
    ) -> QualityIssue:
        """Crea un QualityIssue con ID único."""
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
        """
        Determina el estado de la auditoría según los issues.

        Reglas:
          - Si hay algún issue 'critical' → REJECTED
          - Si hay algún issue 'major' → NEEDS_REVISION
          - Si solo hay 'minor' o ninguno → APPROVED
        """
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
        """Construye el resumen ejecutivo del reporte."""
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
        self, issues: list[QualityIssue]
    ) -> list[str]:
        """Construye lista de recomendaciones generales."""
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

        # Recomendación general de progresión
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

        return recommendations

    @staticmethod
    def _now_iso() -> str:
        """Retorna el timestamp actual en formato ISO 8601 (UTC)."""
        return datetime.now(timezone.utc).isoformat()