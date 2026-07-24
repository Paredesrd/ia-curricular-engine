"""
agents/architect.py
Agente Arquitecto Curricular: segundo agente de la cadena.

Responsabilidad única:
  - Recibir el DirectorBrief (emitido por el Director).
  - Diseñar la matriz curricular completa: módulos, lecciones,
    distribución de Bloom, horas estimadas.
  - Respetar TODAS las restricciones del Tenant contenidas en el brief.
  - Emitir un AgentMessage con la CourseMatrix como payload,
    dirigido al Auditor de Calidad.

El Arquitecto NO redacta contenido. Solo diseña la estructura.
"""

import logging
import math
from datetime import datetime, timezone

from domain.models import (
    DirectorBrief,
    CourseMatrix,
    Module,
    Lesson,
    AgentMessage,
    AgentRole,
    BloomLevel,
)
from config.settings import get_settings


# ============================================================
# CONSTANTES PEDAGÓGICAS
# ============================================================

# Orden natural de progresión cognitiva (Bloom)
BLOOM_PROGRESSION: list[BloomLevel] = [
    BloomLevel.REMEMBER,
    BloomLevel.UNDERSTAND,
    BloomLevel.APPLY,
    BloomLevel.ANALYZE,
    BloomLevel.EVALUATE,
    BloomLevel.CREATE,
]

# Plantillas de títulos de módulo según posición en el curso
MODULE_TITLE_TEMPLATES: list[str] = [
    "Fundamentos de {topic}",
    "Principios y Marco Teórico de {topic}",
    "Métodos y Procedimientos en {topic}",
    "Análisis y Diagnóstico en {topic}",
    "Aplicación Práctica de {topic}",
    "Evaluación y Optimización en {topic}",
    "Diseño y Creación en {topic}",
    "Integración y Casos Avanzados de {topic}",
]

# Plantillas de títulos de lección según nivel de Bloom
LESSON_TITLE_BY_BLOOM: dict[BloomLevel, list[str]] = {
    BloomLevel.REMEMBER: [
        "Definiciones y terminología esencial",
        "Conceptos fundamentales y vocabulario técnico",
        "Hechos, datos y referentes clave",
        "Taxonomía y clasificaciones básicas",
        "Marcos normativos y regulatorios",
    ],
    BloomLevel.UNDERSTAND: [
        "Principios y fundamentos teóricos",
        "Interpretación de conceptos centrales",
        "Relaciones causales y mecanismos subyacentes",
        "Comparación de enfoques y corrientes",
        "Explicación de fenómenos y procesos",
    ],
    BloomLevel.APPLY: [
        "Métodos y procedimientos operativos",
        "Resolución de problemas estándar",
        "Implementación de técnicas y herramientas",
        "Ejecución de protocolos y normativas",
        "Aplicación en contextos controlados",
    ],
    BloomLevel.ANALYZE: [
        "Análisis de componentes y estructuras",
        "Diagnóstico de situaciones complejas",
        "Descomposición de problemas en elementos",
        "Identificación de patrones y correlaciones",
        "Análisis crítico de casos reales",
    ],
    BloomLevel.EVALUATE: [
        "Evaluación de alternativas y soluciones",
        "Juicio crítico sobre metodologías",
        "Valoración de riesgos y beneficios",
        "Auditoría y control de calidad",
        "Toma de decisiones fundamentada",
    ],
    BloomLevel.CREATE: [
        "Diseño de soluciones innovadoras",
        "Formulación de propuestas originales",
        "Desarrollo de proyectos integradores",
        "Creación de modelos y prototipos",
        "Planificación estratégica y prospectiva",
    ],
}

# Plantillas de objetivos de aprendizaje según nivel de Bloom
OBJECTIVE_VERBS: dict[BloomLevel, list[str]] = {
    BloomLevel.REMEMBER: [
        "Identificar", "Definir", "Listar", "Reconocer", "Describir"
    ],
    BloomLevel.UNDERSTAND: [
        "Explicar", "Interpretar", "Comparar", "Clasificar", "Resumir"
    ],
    BloomLevel.APPLY: [
        "Aplicar", "Implementar", "Ejecutar", "Resolver", "Utilizar"
    ],
    BloomLevel.ANALYZE: [
        "Analizar", "Diferenciar", "Examinar", "Descomponer", "Diagnosticar"
    ],
    BloomLevel.EVALUATE: [
        "Evaluar", "Juzgar", "Valorar", "Justificar", "Priorizar"
    ],
    BloomLevel.CREATE: [
        "Diseñar", "Crear", "Formular", "Desarrollar", "Proponer"
    ],
}


class ArchitectAgent:
    """
    Agente Arquitecto Curricular.
    Diseña la matriz curricular completa a partir del DirectorBrief.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._logger = logging.getLogger(
            f"{self._settings.system_name}.ArchitectAgent"
        )

    # ----------------------------------------------------------------
    # MÉTODO PÚBLICO PRINCIPAL
    # ----------------------------------------------------------------

    def process(self, brief: DirectorBrief) -> AgentMessage:
        """
        Diseña la CourseMatrix a partir del DirectorBrief.
        Retorna un AgentMessage dirigido al Auditor.

        Args:
            brief: DirectorBrief emitido por el Director.

        Returns:
            AgentMessage con message_type='course_matrix'.

        Raises:
            ValueError: Si el brief es inválido o no se puede construir
                        una matriz que cumpla las restricciones.
        """
        self._logger.info(
            "ArchitectAgent iniciado | Curso: %s | Tema: '%s'",
            brief.course_id,
            brief.topic,
        )

        # Paso 1: Calcular número de módulos
        num_modules = self._calculate_num_modules(brief)
        self._logger.info("Módulos calculados: %d", num_modules)

        # Paso 2: Planificar distribución de Bloom
        bloom_plan = self._plan_bloom_distribution(brief, num_modules)
        self._logger.info(
            "Plan Bloom: %s",
            {k.value: v for k, v in bloom_plan.items()},
        )

        # Paso 3: Construir módulos y lecciones
        modules = self._build_modules(brief, num_modules, bloom_plan)
        self._logger.info("Módulos construidos: %d", len(modules))

        # Paso 4: Calcular horas totales y distribución Bloom real
        total_hours = sum(m.estimated_hours for m in modules)
        bloom_distribution = self._compute_bloom_distribution(modules)

        self._logger.info(
            "Horas totales: %.1f | Distribución Bloom: %s",
            total_hours,
            {k.value: v for k, v in bloom_distribution.items()},
        )

        # Paso 5: Validar que la matriz cumple las restricciones
        self._validate_matrix_against_brief(
            modules, total_hours, bloom_distribution, brief
        )

        # Paso 6: Construir CourseMatrix
        matrix = CourseMatrix(
            course_id=brief.course_id,
            course_title=self._generate_course_title(brief.topic),
            topic=brief.topic,
            total_estimated_hours=round(total_hours, 1),
            modules=modules,
            bloom_distribution=bloom_distribution,
        )

        self._logger.info(
            "CourseMatrix construida | Curso: %s | Título: '%s' | "
            "Módulos: %d | Horas: %.1f",
            matrix.course_id,
            matrix.course_title,
            len(matrix.modules),
            matrix.total_estimated_hours,
        )

        # Paso 7: Envolver en AgentMessage
        message = AgentMessage(
            sender=AgentRole.ARCHITECT,
            receiver=AgentRole.AUDITOR,
            message_type="course_matrix",
            payload=matrix.model_dump(mode="json"),
            timestamp=self._now_iso(),
        )

        self._logger.info(
            "AgentMessage emitido: Arquitecto → Auditor | Tipo: %s",
            message.message_type,
        )

        return message

    # ----------------------------------------------------------------
    # MÉTODOS PRIVADOS - PLANIFICACIÓN
    # ----------------------------------------------------------------

    def _calculate_num_modules(self, brief: DirectorBrief) -> int:
        """
        Calcula el número óptimo de módulos respetando restricciones.

        Estrategia:
          - Apuntar al punto medio de horas totales.
          - Dividir por el punto medio de horas por módulo.
          - Ajustar para cumplir todas las restricciones.
        """
        target_total = (brief.min_total_hours + brief.max_total_hours) / 2.0
        target_module = (brief.min_module_hours + brief.max_module_hours) / 2.0

        # Cálculo inicial
        num_modules = max(1, round(target_total / target_module))

        # Restricción: num_modules * min_module_hours <= max_total_hours
        while num_modules > 1 and (num_modules * brief.min_module_hours) > brief.max_total_hours:
            num_modules -= 1

        # Restricción: num_modules * max_module_hours >= min_total_hours
        while (num_modules * brief.max_module_hours) < brief.min_total_hours:
            num_modules += 1

        # Restricción: al menos 1 módulo
        num_modules = max(1, num_modules)

        # Restricción: no exceder un límite razonable (12 módulos máximo)
        num_modules = min(num_modules, 12)

        return num_modules

    def _plan_bloom_distribution(
        self, brief: DirectorBrief, num_modules: int
    ) -> dict[BloomLevel, int]:
        """
        Planifica cuántas lecciones de cada nivel de Bloom se necesitan.

        Garantiza que TODOS los required_bloom_levels estén presentes.
        Distribuye el resto siguiendo la progresión cognitiva natural.
        """
        required = brief.required_bloom_levels
        plan: dict[BloomLevel, int] = {level: 0 for level in BLOOM_PROGRESSION}

        # Calcular total de lecciones estimado
        total_lessons = self._estimate_total_lessons(brief, num_modules)

        # Garantizar al menos 1 lección por cada Bloom requerido
        for level in required:
            plan[level] = 1

        # Distribuir lecciones restantes
        remaining = total_lessons - len(required)
        if remaining > 0:
            # Filtrar solo los niveles requeridos para la distribución
            required_ordered = [
                level for level in BLOOM_PROGRESSION if level in required
            ]
            # Distribuir proporcionalmente con peso progresivo
            weights = list(range(1, len(required_ordered) + 1))
            total_weight = sum(weights)

            for i, level in enumerate(required_ordered):
                extra = round(remaining * weights[i] / total_weight)
                plan[level] += extra

            # Ajustar sobrantes/faltantes al nivel intermedio
            current_total = sum(plan.values())
            diff = total_lessons - current_total
            if diff != 0 and required_ordered:
                mid_index = len(required_ordered) // 2
                plan[required_ordered[mid_index]] += diff

        return plan

    def _estimate_total_lessons(
        self, brief: DirectorBrief, num_modules: int
    ) -> int:
        """
        Estima el número total de lecciones del curso.
        """
        target_total = (brief.min_total_hours + brief.max_total_hours) / 2.0
        target_lesson_hours = (
            self._settings.default_min_hours_per_lesson
            + self._settings.default_max_hours_per_lesson
        ) / 2.0

        total_lessons = max(num_modules, round(target_total / target_lesson_hours))

        # Respetar mínimo por módulo
        min_total = num_modules * brief.min_lessons_per_module
        total_lessons = max(total_lessons, min_total)

        # Respetar máximo por módulo
        max_total = num_modules * brief.max_lessons_per_module
        total_lessons = min(total_lessons, max_total)

        return total_lessons

    # ----------------------------------------------------------------
    # MÉTODOS PRIVADOS - CONSTRUCCIÓN
    # ----------------------------------------------------------------

    def _build_modules(
        self,
        brief: DirectorBrief,
        num_modules: int,
        bloom_plan: dict[BloomLevel, int],
    ) -> list[Module]:
        """
        Construye todos los módulos con sus lecciones.
        """
        modules: list[Module] = []
        target_total = (brief.min_total_hours + brief.max_total_hours) / 2.0
        hours_per_module = target_total / num_modules

        # Ajustar horas por módulo a los límites
        hours_per_module = max(
            float(brief.min_module_hours),
            min(float(brief.max_module_hours), hours_per_module),
        )

        # Contador global de lecciones por Bloom
        bloom_counters: dict[BloomLevel, int] = {
            level: 0 for level in BLOOM_PROGRESSION
        }

        # Índice de título de lección por Bloom (para no repetir)
        bloom_title_index: dict[BloomLevel, int] = {
            level: 0 for level in BLOOM_PROGRESSION
        }

        for m_idx in range(num_modules):
            module_id = f"M{m_idx + 1}"
            module_title = self._get_module_title(m_idx, brief.topic)

            # Determinar cuántas lecciones en este módulo
            lessons_in_module = self._lessons_for_module(
                m_idx, num_modules, brief, bloom_plan, bloom_counters
            )

            # Construir lecciones del módulo
            lessons: list[Lesson] = []
            module_hours = 0.0

            for l_idx in range(lessons_in_module):
                # Seleccionar nivel de Bloom para esta lección
                bloom_level = self._select_bloom_for_lesson(
                    m_idx, l_idx, num_modules, lessons_in_module,
                    brief, bloom_plan, bloom_counters
                )
                bloom_counters[bloom_level] += 1

                # Calcular horas de la lección
                lesson_hours = round(
                    hours_per_module / lessons_in_module, 1
                )
                lesson_hours = max(
                    self._settings.default_min_hours_per_lesson,
                    min(self._settings.default_max_hours_per_lesson, lesson_hours),
                )
                module_hours += lesson_hours

                # Generar título de lección
                lesson_title = self._get_lesson_title(
                    bloom_level, bloom_title_index[bloom_level]
                )
                bloom_title_index[bloom_level] += 1

                # Generar objetivo de aprendizaje
                objective = self._generate_objective(bloom_level, brief.topic)

                # Generar temas clave
                key_topics = self._generate_key_topics(
                    bloom_level, brief.topic, l_idx
                )

                lesson = Lesson(
                    lesson_id=f"{module_id}L{l_idx + 1}",
                    title=lesson_title,
                    bloom_level=bloom_level,
                    estimated_hours=lesson_hours,
                    learning_objective=objective,
                    key_topics=key_topics,
                )
                lessons.append(lesson)

            # Ajustar horas del módulo
            module_hours = round(sum(l.estimated_hours for l in lessons), 1)
            module_hours = max(
                float(brief.min_module_hours),
                min(float(brief.max_module_hours), module_hours),
            )

            module = Module(
                module_id=module_id,
                title=module_title,
                description=self._generate_module_description(
                    m_idx, brief.topic, lessons
                ),
                estimated_hours=module_hours,
                lessons=lessons,
            )
            modules.append(module)

        return modules

    def _lessons_for_module(
        self,
        module_index: int,
        num_modules: int,
        brief: DirectorBrief,
        bloom_plan: dict[BloomLevel, int],
        bloom_counters: dict[BloomLevel, int],
    ) -> int:
        """
        Determina cuántas lecciones debe tener un módulo específico.
        """
        total_lessons = self._estimate_total_lessons(brief, num_modules)
        base = total_lessons // num_modules
        remainder = total_lessons % num_modules

        # Distribuir el residuo entre los primeros módulos
        count = base + (1 if module_index < remainder else 0)

        # Respetar límites del Tenant
        count = max(brief.min_lessons_per_module, count)
        count = min(brief.max_lessons_per_module, count)

        return count

    def _select_bloom_for_lesson(
        self,
        module_index: int,
        lesson_index: int,
        num_modules: int,
        lessons_in_module: int,
        brief: DirectorBrief,
        bloom_plan: dict[BloomLevel, int],
        bloom_counters: dict[BloomLevel, int],
    ) -> BloomLevel:
        """
        Selecciona el nivel de Bloom para una lección específica.

        Estrategia:
          - Progresión cognitiva a lo largo del curso.
          - Garantizar que todos los Bloom requeridos se cumplan.
          - Priorizar niveles con déficit en el plan.
        """
        required = brief.required_bloom_levels
        required_ordered = [
            level for level in BLOOM_PROGRESSION if level in required
        ]

        # Posición relativa en el curso (0.0 a 1.0)
        global_lesson_pos = (
            (module_index * lessons_in_module + lesson_index)
            / max(1, num_modules * lessons_in_module - 1)
        )

        # Primero: verificar si hay algún Bloom requerido con déficit
        for level in required_ordered:
            if bloom_counters[level] < bloom_plan[level]:
                # ¿Es el momento adecuado para este nivel?
                level_pos = BLOOM_PROGRESSION.index(level) / max(
                    1, len(BLOOM_PROGRESSION) - 1
                )
                # Si la posición global está cerca de la posición del nivel
                if abs(global_lesson_pos - level_pos) < 0.4:
                    return level

        # Segundo: seleccionar por progresión natural
        target_index = int(global_lesson_pos * (len(required_ordered) - 1))
        target_index = max(0, min(len(required_ordered) - 1, target_index))
        return required_ordered[target_index]

    # ----------------------------------------------------------------
    # MÉTODOS PRIVADOS - GENERACIÓN DE TEXTO ESTRUCTURAL
    # ----------------------------------------------------------------

    def _generate_course_title(self, topic: str) -> str:
        """Genera el título del curso."""
        return f"Curso de {topic}"

    def _get_module_title(self, index: int, topic: str) -> str:
        """Genera el título de un módulo según su posición."""
        if index < len(MODULE_TITLE_TEMPLATES):
            return MODULE_TITLE_TEMPLATES[index].format(topic=topic)
        return f"Módulo {index + 1}: {topic} - Sección {index + 1}"

    def _get_lesson_title(
        self, bloom_level: BloomLevel, variant_index: int
    ) -> str:
        """Genera el título de una lección según su nivel de Bloom."""
        titles = LESSON_TITLE_BY_BLOOM.get(bloom_level, ["Contenido de la lección"])
        idx = variant_index % len(titles)
        return titles[idx]

    def _generate_objective(
        self, bloom_level: BloomLevel, topic: str
    ) -> str:
        """Genera un objetivo de aprendizaje según el nivel de Bloom."""
        verbs = OBJECTIVE_VERBS.get(bloom_level, ["Comprender"])
        verb = verbs[0]
        templates = {
            BloomLevel.REMEMBER: f"{verb} los conceptos fundamentales y la terminología esencial de {topic}.",
            BloomLevel.UNDERSTAND: f"{verb} los principios teóricos y las relaciones causales en {topic}.",
            BloomLevel.APPLY: f"{verb} métodos y procedimientos operativos en situaciones prácticas de {topic}.",
            BloomLevel.ANALYZE: f"{verb} componentes, estructuras y patrones en problemas complejos de {topic}.",
            BloomLevel.EVALUATE: f"{verb} alternativas de solución y emitir juicios fundamentados en {topic}.",
            BloomLevel.CREATE: f"{verb} soluciones innovadoras y propuestas originales en {topic}.",
        }
        return templates.get(bloom_level, f"{verb} aspectos relevantes de {topic}.")

    def _generate_key_topics(
        self, bloom_level: BloomLevel, topic: str, lesson_index: int
    ) -> list[str]:
        """Genera temas clave para una lección."""
        base_topics = {
            BloomLevel.REMEMBER: [
                f"Terminología de {topic}",
                f"Definiciones clave",
                f"Marco normativo aplicable",
            ],
            BloomLevel.UNDERSTAND: [
                f"Principios teóricos de {topic}",
                f"Mecanismos y relaciones causales",
                f"Comparación de enfoques",
            ],
            BloomLevel.APPLY: [
                f"Procedimientos operativos",
                f"Herramientas y técnicas de {topic}",
                f"Resolución de problemas estándar",
            ],
            BloomLevel.ANALYZE: [
                f"Descomposición de problemas",
                f"Análisis de casos en {topic}",
                f"Identificación de patrones",
            ],
            BloomLevel.EVALUATE: [
                f"Criterios de evaluación",
                f"Análisis de riesgos en {topic}",
                f"Toma de decisiones",
            ],
            BloomLevel.CREATE: [
                f"Diseño de soluciones",
                f"Formulación de proyectos en {topic}",
                f"Innovación y mejora continua",
            ],
        }
        return base_topics.get(bloom_level, [f"Contenido de {topic}"])

    def _generate_module_description(
        self, module_index: int, topic: str, lessons: list[Lesson]
    ) -> str:
        """Genera la descripción de un módulo."""
        bloom_levels_in_module = set(l.bloom_level.value for l in lessons)
        num_lessons = len(lessons)
        return (
            f"Módulo {module_index + 1} del curso de {topic}. "
            f"Contiene {num_lessons} lecciones que cubren los niveles "
            f"cognitivos: {', '.join(sorted(bloom_levels_in_module))}. "
            f"Enfocado en el desarrollo progresivo de competencias "
            f"en {topic}."
        )

    # ----------------------------------------------------------------
    # MÉTODOS PRIVADOS - VALIDACIÓN
    # ----------------------------------------------------------------

    def _validate_matrix_against_brief(
        self,
        modules: list[Module],
        total_hours: float,
        bloom_distribution: dict[BloomLevel, int],
        brief: DirectorBrief,
    ) -> None:
        """
        Valida que la matriz construida cumple TODAS las restricciones
        del DirectorBrief. Lanza ValueError si hay incumplimientos.
        """
        errors: list[str] = []

        # Horas totales
        if total_hours < brief.min_total_hours:
            errors.append(
                f"Horas totales ({total_hours:.1f}) < "
                f"mínimo requerido ({brief.min_total_hours})"
            )
        if total_hours > brief.max_total_hours:
            errors.append(
                f"Horas totales ({total_hours:.1f}) > "
                f"máximo permitido ({brief.max_total_hours})"
            )

        # Horas por módulo
        for module in modules:
            if module.estimated_hours < brief.min_module_hours:
                errors.append(
                    f"Módulo {module.module_id}: horas ({module.estimated_hours:.1f}) < "
                    f"mínimo ({brief.min_module_hours})"
                )
            if module.estimated_hours > brief.max_module_hours:
                errors.append(
                    f"Módulo {module.module_id}: horas ({module.estimated_hours:.1f}) > "
                    f"máximo ({brief.max_module_hours})"
                )

        # Lecciones por módulo
        for module in modules:
            num_lessons = len(module.lessons)
            if num_lessons < brief.min_lessons_per_module:
                errors.append(
                    f"Módulo {module.module_id}: lecciones ({num_lessons}) < "
                    f"mínimo ({brief.min_lessons_per_module})"
                )
            if num_lessons > brief.max_lessons_per_module:
                errors.append(
                    f"Módulo {module.module_id}: lecciones ({num_lessons}) > "
                    f"máximo ({brief.max_lessons_per_module})"
                )

        # Bloom requeridos presentes
        for level in brief.required_bloom_levels:
            if bloom_distribution.get(level, 0) == 0:
                errors.append(
                    f"Nivel de Bloom requerido '{level.value}' "
                    f"no está presente en ninguna lección"
                )

        if errors:
            error_msg = (
                f"CourseMatrix del curso '{brief.course_id}' "
                f"incumple restricciones: " + "; ".join(errors)
            )
            self._logger.error(error_msg)
            raise ValueError(error_msg)

        self._logger.info(
            "CourseMatrix validada contra el brief: TODAS las restricciones cumplidas"
        )

    # ----------------------------------------------------------------
    # MÉTODOS PRIVADOS - UTILIDADES
    # ----------------------------------------------------------------

    def _compute_bloom_distribution(
        self, modules: list[Module]
    ) -> dict[BloomLevel, int]:
        """Calcula la distribución real de Bloom en la matriz."""
        distribution: dict[BloomLevel, int] = {
            level: 0 for level in BloomLevel
        }
        for module in modules:
            for lesson in module.lessons:
                distribution[lesson.bloom_level] += 1
        return distribution

    @staticmethod
    def _now_iso() -> str:
        """Retorna el timestamp actual en formato ISO 8601 (UTC)."""
        return datetime.now(timezone.utc).isoformat()