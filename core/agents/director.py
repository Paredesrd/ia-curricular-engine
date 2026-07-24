"""
agents/director.py
Agente Director: primer agente de la cadena.

Responsabilidad única:
  - Recibir las TenantRules (reglas de acreditación del colegio)
    y el InstructorInput (tema técnico del instructor).
  - Validar la consistencia de las reglas del Tenant.
  - Generar un DirectorBrief estructurado con todas las restricciones
    procesadas y listas para el Arquitecto Curricular.
  - Emitir un AgentMessage dirigido al Arquitecto.

El Director NO diseña el curso. Solo prepara el terreno.
"""

import uuid
import logging
from datetime import datetime, timezone

from domain.models import (
    TenantRules,
    InstructorInput,
    DirectorBrief,
    AgentMessage,
    AgentRole,
    BloomLevel,
)
from config.settings import get_settings


class DirectorAgent:
    """
    Agente Director.
    Gestiona las reglas del Tenant y emite el brief inicial
    hacia el Arquitecto Curricular.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._logger = logging.getLogger(
            f"{self._settings.system_name}.DirectorAgent"
        )

    # ----------------------------------------------------------------
    # MÉTODO PÚBLICO PRINCIPAL
    # ----------------------------------------------------------------

    def process(
        self,
        tenant_rules: TenantRules,
        instructor_input: InstructorInput,
    ) -> AgentMessage:
        """
        Procesa las reglas del Tenant y el input del instructor.
        Retorna un AgentMessage con el DirectorBrief como payload,
        dirigido al Arquitecto Curricular.

        Args:
            tenant_rules: Reglas de acreditación del colegio.
            instructor_input: Tema técnico del instructor.

        Returns:
            AgentMessage con message_type='director_brief'.

        Raises:
            ValueError: Si las reglas del Tenant son inconsistentes.
        """
        self._logger.info(
            "DirectorAgent iniciado | Tenant: %s | Tema: '%s'",
            tenant_rules.tenant_name,
            instructor_input.topic,
        )

        # Paso 1: Validar consistencia de las reglas del Tenant
        self._validate_tenant_rules(tenant_rules)

        # Paso 2: Generar ID único del curso
        course_id = self._generate_course_id(tenant_rules.tenant_id)
        self._logger.info("Course ID generado: %s", course_id)

        # Paso 3: Construir el resumen de restricciones
        constraints_summary = self._build_constraints_summary(tenant_rules)
        self._logger.info(
            "Restricciones procesadas: %d reglas explícitas",
            len(constraints_summary),
        )

        # Paso 4: Construir el DirectorBrief
        brief = DirectorBrief(
            course_id=course_id,
            topic=instructor_input.topic.strip(),
            target_audience=(
                instructor_input.target_audience.strip()
                if instructor_input.target_audience
                else None
            ),
            additional_context=(
                instructor_input.additional_context.strip()
                if instructor_input.additional_context
                else None
            ),
            tenant_id=tenant_rules.tenant_id,
            tenant_name=tenant_rules.tenant_name,
            min_total_hours=tenant_rules.min_total_hours,
            max_total_hours=tenant_rules.max_total_hours,
            min_module_hours=tenant_rules.min_module_hours,
            max_module_hours=tenant_rules.max_module_hours,
            required_bloom_levels=tenant_rules.required_bloom_levels,
            min_lessons_per_module=tenant_rules.min_lessons_per_module,
            max_lessons_per_module=tenant_rules.max_lessons_per_module,
            custom_restrictions=tenant_rules.custom_restrictions,
            constraints_summary=constraints_summary,
            created_at=self._now_iso(),
        )

        self._logger.info(
            "DirectorBrief construido | Curso: %s | Horas: %d-%d | "
            "Bloom requeridos: %s",
            brief.course_id,
            brief.min_total_hours,
            brief.max_total_hours,
            [b.value for b in brief.required_bloom_levels],
        )

        # Paso 5: Envolver en AgentMessage
        message = AgentMessage(
            sender=AgentRole.DIRECTOR,
            receiver=AgentRole.ARCHITECT,
            message_type="director_brief",
            payload=brief.model_dump(mode="json"),
            timestamp=self._now_iso(),
        )

        self._logger.info(
            "AgentMessage emitido: Director → Arquitecto | Tipo: %s",
            message.message_type,
        )

        return message

    # ----------------------------------------------------------------
    # MÉTODOS PRIVADOS
    # ----------------------------------------------------------------

    def _validate_tenant_rules(self, rules: TenantRules) -> None:
        """
        Valida la consistencia interna de las reglas del Tenant.
        Lanza ValueError si detecta inconsistencias.
        """
        errors: list[str] = []

        # Horas totales
        if rules.min_total_hours > rules.max_total_hours:
            errors.append(
                f"min_total_hours ({rules.min_total_hours}) > "
                f"max_total_hours ({rules.max_total_hours})"
            )

        # Horas por módulo
        if rules.min_module_hours > rules.max_module_hours:
            errors.append(
                f"min_module_hours ({rules.min_module_hours}) > "
                f"max_module_hours ({rules.max_module_hours})"
            )

        # Lecciones por módulo
        if rules.min_lessons_per_module > rules.max_lessons_per_module:
            errors.append(
                f"min_lessons_per_module ({rules.min_lessons_per_module}) > "
                f"max_lessons_per_module ({rules.max_lessons_per_module})"
            )

        # Horas de módulo vs horas totales
        if rules.min_module_hours > rules.max_total_hours:
            errors.append(
                f"min_module_hours ({rules.min_module_hours}) > "
                f"max_total_hours ({rules.max_total_hours}): "
                f"imposible cumplir con al menos 1 módulo"
            )

        # Niveles de Bloom requeridos
        if len(rules.required_bloom_levels) == 0:
            errors.append("required_bloom_levels no puede estar vacío")

        # Verificar duplicados en Bloom
        bloom_values = [b.value for b in rules.required_bloom_levels]
        if len(bloom_values) != len(set(bloom_values)):
            errors.append("required_bloom_levels contiene duplicados")

        if errors:
            error_msg = (
                f"Reglas del Tenant '{rules.tenant_name}' inconsistentes: "
                + "; ".join(errors)
            )
            self._logger.error(error_msg)
            raise ValueError(error_msg)

        self._logger.info(
            "Reglas del Tenant '%s' validadas correctamente",
            rules.tenant_name,
        )

    def _build_constraints_summary(self, rules: TenantRules) -> list[str]:
        """
        Construye una lista de restricciones en lenguaje claro
        a partir de las reglas del Tenant.
        """
        constraints: list[str] = []

        constraints.append(
            f"El curso DEBE tener entre {rules.min_total_hours} y "
            f"{rules.max_total_hours} horas totales."
        )

        constraints.append(
            f"Cada módulo DEBE tener entre {rules.min_module_hours} y "
            f"{rules.max_module_hours} horas."
        )

        constraints.append(
            f"Cada módulo DEBE tener entre {rules.min_lessons_per_module} y "
            f"{rules.max_lessons_per_module} lecciones."
        )

        bloom_names = [b.value for b in rules.required_bloom_levels]
        constraints.append(
            f"El curso DEBE incluir los siguientes niveles de Bloom: "
            f"{', '.join(bloom_names)}."
        )

        if rules.custom_restrictions:
            constraints.append(
                f"Restricción adicional del colegio: {rules.custom_restrictions}"
            )

        return constraints

    def _generate_course_id(self, tenant_id: str) -> str:
        """
        Genera un ID único para el curso.
        Formato: {tenant_id}-{uuid_short}
        """
        short_uuid = uuid.uuid4().hex[:8].upper()
        return f"{tenant_id}-{short_uuid}"

    @staticmethod
    def _now_iso() -> str:
        """Retorna el timestamp actual en formato ISO 8601 (UTC)."""
        return datetime.now(timezone.utc).isoformat()