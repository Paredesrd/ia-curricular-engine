"""
agents/architect.py
Agente Arquitecto Curricular: segundo agente de la cadena.
Responsabilidad única:
  - Recibir el DirectorBrief (emitido por el Director).
  - Diseñar la matriz curricular completa: módulos, lecciones,
    distribución de Bloom, horas estimadas.
  - Respetar TODAS las restricciones del Tenant contenidas en el brief.
  - Si el instructor aportó INTENCIÓN enriquecida (pilares, objetivo,
    entregable, nombre), usarla como los "huesos" del curso:
      * content_pillars  -> títulos de módulos (1 pilar = 1 módulo),
        agrupados o completados con un cierre si las horas del colegio
        no permiten un módulo por pilar.
      * course_name      -> título del curso.
      * operational_goal -> ancla de los objetivos de lección.
      * final_deliverable-> título del módulo de cierre (si se añade).
    Si NO hay intención (CLI / llamada vieja), cae al diseño por plantillas.
  - Emitir un AgentMessage con la CourseMatrix como payload, al Auditor.
  - Si recibe feedback del Auditor (revise), ajustar la matriz en vez de
    regenerar a ciegas.
El Arquitecto NO redacta contenido. Solo diseña la estructura.
"""
import logging
import math
import re
from datetime import datetime, timezone

from domain.models import (
    DirectorBrief,
    CourseMatrix,
    Module,
    Lesson,
    AgentMessage,
    AgentRole,
    BloomLevel,
    RevisionFeedback,
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

# Plantillas de títulos de módulo según posición (SOLO cuando no hay pilares)
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
    BloomLevel.REMEMBER: ["Identificar", "Definir", "Listar", "Reconocer", "Describir"],
    BloomLevel.UNDERSTAND: ["Explicar", "Interpretar", "Comparar", "Clasificar", "Resumir"],
    BloomLevel.APPLY: ["Aplicar", "Implementar", "Ejecutar", "Resolver", "Utilizar"],
    BloomLevel.ANALYZE: ["Analizar", "Diferenciar", "Examinar", "Descomponer", "Diagnosticar"],
    BloomLevel.EVALUATE: ["Evaluar", "Juzgar", "Valorar", "Justificar", "Priorizar"],
    BloomLevel.CREATE: ["Diseñar", "Crear", "Formular", "Desarrollar", "Proponer"],
}

# Separadores tolerados para partir pilares escritos en una sola línea.
_PILLAR_SPLIT = re.compile(r"[;|]")
# Numeración inicial a limpiar de cada pilar ("1)", "1.", "1-", "* ", "- ").
_PILLAR_NUM = re.compile(r"^\s*[\d]+[\).\-\:]\s*")
_PILLAR_BULLET = re.compile(r"^\s*[\*\-]\s+")


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
    def process(
        self,
        brief: DirectorBrief,
        feedback: RevisionFeedback | None = None,
    ) -> AgentMessage:
        """
        Diseña la CourseMatrix a partir del DirectorBrief.
        Si se pasa `feedback` (del Auditor), aplica sus ajustes; si no,
        diseña desde cero. Retorna un AgentMessage dirigido al Auditor.
        """
        self._logger.info(
            "ArchitectAgent iniciado | Curso: %s | Tema: '%s' | Revisión: %s",
            brief.course_id,
            brief.topic,
            "SÍ (con feedback)" if feedback else "no (diseño inicial)",
        )

        # Paso 1: Resolver las "specs" de módulo (pilares del instructor o
        # plantillas por posición) y el número de módulos coherente con ellas
        # y con las horas del colegio.
        module_specs = self._resolve_module_specs(brief)
        if module_specs is not None:
            num_modules = len(module_specs)
            self._logger.info(
                "Módulos desde pilares del instructor: %d", num_modules
            )
        else:
            num_modules = self._calculate_num_modules(brief)
            module_specs = self._specs_from_templates(brief, num_modules)
            self._logger.info("Módulos calculados por plantillas: %d", num_modules)

        # Paso 2: Planificar distribución de Bloom (reforzada por feedback)
        bloom_plan = self._plan_bloom_distribution(brief, num_modules, feedback)
        self._logger.info(
            "Plan Bloom: %s",
            {k.value: v for k, v in bloom_plan.items()},
        )

        # Paso 3: Construir módulos y lecciones a partir de las specs
        modules = self._build_modules(brief, num_modules, bloom_plan, module_specs, feedback)
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

        # Paso 6: Construir CourseMatrix (título desde la intención si la hay)
        matrix = CourseMatrix(
            course_id=brief.course_id,
            course_title=self._generate_course_title(brief),
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

    def revise(
        self,
        brief: DirectorBrief,
        feedback: RevisionFeedback,
    ) -> AgentMessage:
        """
        Re-diseña la matriz aplicando el feedback del Auditor.
        Alias semántico de `process(brief, feedback)`.
        """
        return self.process(brief, feedback=feedback)

    # ----------------------------------------------------------------
    # INTENCIÓN DEL INSTRUCTOR -> SPECS DE MÓDULO
    # ----------------------------------------------------------------
    def _parse_pillars(self, raw: str | None) -> list[str]:
        """
        Extrae los pilares/pasos del instructor de forma tolerante.
        Acepta líneas numeradas, viñetas, o una sola línea separada por ; | ,.
        Retorna la lista limpia (sin numeración), en orden, sin vacíos.
        """
        if not raw:
            return []
        text = raw.strip()
        if not text:
            return []

        # Partir por líneas; si no hay saltos, intentar separadores ; |
        if "\n" in text:
            chunks = text.splitlines()
        elif _PILLAR_SPLIT.search(text):
            chunks = _PILLAR_SPLIT.split(text)
        else:
            chunks = [text]

        pillars: list[str] = []
        for chunk in chunks:
            item = chunk.strip()
            if not item:
                continue
            item = _PILLAR_NUM.sub("", item)
            item = _PILLAR_BULLET.sub("", item)
            item = item.strip(" -:–—")
            if item:
                pillars.append(item)
        return pillars

    def _module_hour_bounds(self, brief: DirectorBrief) -> tuple[int, int]:
        """
        Rango de módulos físicamente viable según las horas del colegio.
        min_viable = ceil(min_total / max_module)  (módulos como mínimo)
        max_viable = floor(max_total / min_module)  (módulos como máximo)
        Ambos acotados por settings.max_modules y >= 1.
        """
        min_viable = math.ceil(brief.min_total_hours / brief.max_module_hours)
        max_viable = math.floor(brief.max_total_hours / brief.min_module_hours)
        min_viable = max(1, min_viable)
        max_viable = max(min_viable, min(max_viable, self._settings.max_modules))
        return min_viable, max_viable

    def _resolve_module_specs(
        self, brief: DirectorBrief
    ) -> list[dict] | None:
        """
        Convierte los pilares del instructor en specs de módulo.
        Retorna None si no hay pilares (→ diseño por plantillas).
        Cada spec = {"title": str, "pillar": str | None, "closing": bool}.
        Respeta los huesos del instructor: si caben 1:1, perfecto; si son
        demasiados para las horas del colegio, los AGRUPA (no los trunca);
        si son pocos para el mínimo de horas, AÑADE un cierre anclado al
        entregable final.
        """
        pillars = self._parse_pillars(brief.content_pillars)
        if not pillars:
            return None

        min_viable, max_viable = self._module_hour_bounds(brief)

        if len(pillars) > max_viable:
            # Agrupar pilares en max_viable buckets contiguos (sin perder ninguno).
            self._logger.warning(
                "Pilares (%d) exceden el máximo viable de módulos (%d) para "
                "las horas del colegio; se agrupan en %d módulos.",
                len(pillars),
                max_viable,
                max_viable,
            )
            buckets: list[list[str]] = [[] for _ in range(max_viable)]
            for i, p in enumerate(pillars):
                buckets[i % max_viable].append(p)
            specs: list[dict] = []
            for bucket in buckets:
                title = " / ".join(bucket)
                specs.append({
                    "title": title,
                    "pillar": " / ".join(bucket),
                    "closing": False,
                })
            return specs

        # Caben 1:1.
        specs = [
            {"title": p, "pillar": p, "closing": False} for p in pillars
        ]

        # Si faltan módulos para el mínimo de horas, añadir cierre(s).
        if len(specs) < min_viable:
            extra = min_viable - len(specs)
            self._logger.info(
                "Pilares (%d) por debajo del mínimo viable de módulos (%d); "
                "se añaden %d módulo(s) de cierre/integración.",
                len(pillars),
                min_viable,
                extra,
            )
            for k in range(extra):
                specs.append(self._closing_spec(brief, k))

        return specs

    def _closing_spec(self, brief: DirectorBrief, index: int) -> dict:
        """Spec de módulo de cierre/integración anclado al entregable final."""
        if brief.final_deliverable:
            if index == 0:
                title = f"Integración final: {brief.final_deliverable}"
            else:
                title = f"Cierre y puesta en práctica ({index + 1})"
        else:
            title = "Integración y cierre del curso"
        return {"title": title, "pillar": None, "closing": True}

    def _specs_from_templates(
        self, brief: DirectorBrief, num_modules: int
    ) -> list[dict]:
        """Specs por plantillas de posición (modo sin pilares / retrocompatible)."""
        specs: list[dict] = []
        for i in range(num_modules):
            if i < len(MODULE_TITLE_TEMPLATES):
                title = MODULE_TITLE_TEMPLATES[i].format(topic=brief.topic)
            else:
                title = f"Módulo {i + 1}: {brief.topic} - Sección {i + 1}"
            specs.append({"title": title, "pillar": None, "closing": False})
        return specs

    # ----------------------------------------------------------------
    # MÉTODOS PRIVADOS - PLANIFICACIÓN
    # ----------------------------------------------------------------
    def _effective_max_module_hours(
        self, brief: DirectorBrief, feedback: RevisionFeedback | None
    ) -> float:
        """
        Techo efectivo de horas por módulo (mínimo entre el máximo del Tenant
        y el techo pedido por el Auditor en el feedback).
        """
        cap = float(brief.max_module_hours)
        if feedback is not None and feedback.module_hours_cap is not None:
            cap = min(cap, float(feedback.module_hours_cap))
        return cap

    def _calculate_num_modules(self, brief: DirectorBrief) -> int:
        """Número óptimo de módulos por horas (modo sin pilares)."""
        target_total = (brief.min_total_hours + brief.max_total_hours) / 2.0
        target_module = (brief.min_module_hours + brief.max_module_hours) / 2.0

        num_modules = max(1, round(target_total / target_module))

        while num_modules > 1 and (num_modules * brief.min_module_hours) > brief.max_total_hours:
            num_modules -= 1
        while (num_modules * brief.max_module_hours) < brief.min_total_hours:
            num_modules += 1

        num_modules = max(1, num_modules)
        num_modules = min(num_modules, self._settings.max_modules)
        return num_modules

    def _plan_bloom_distribution(
        self,
        brief: DirectorBrief,
        num_modules: int,
        feedback: RevisionFeedback | None = None,
    ) -> dict[BloomLevel, int]:
        """Planifica lecciones por nivel de Bloom; garantiza los requeridos."""
        required = brief.required_bloom_levels
        plan: dict[BloomLevel, int] = {level: 0 for level in BLOOM_PROGRESSION}

        total_lessons = self._estimate_total_lessons(brief, num_modules)

        for level in required:
            plan[level] = 1

        if feedback is not None:
            for level in feedback.missing_bloom_levels:
                if plan.get(level, 0) < 1:
                    plan[level] = 1

        remaining = total_lessons - sum(plan.values())
        if remaining > 0:
            required_ordered = [
                level for level in BLOOM_PROGRESSION if level in required
            ]
            weights = list(range(1, len(required_ordered) + 1))
            total_weight = sum(weights)
            for i, level in enumerate(required_ordered):
                extra = round(remaining * weights[i] / total_weight)
                plan[level] += extra

            current_total = sum(plan.values())
            diff = total_lessons - current_total
            if diff != 0 and required_ordered:
                mid_index = len(required_ordered) // 2
                plan[required_ordered[mid_index]] += diff

        return plan

    def _estimate_total_lessons(
        self, brief: DirectorBrief, num_modules: int
    ) -> int:
        """Estima el número total de lecciones del curso."""
        target_total = (brief.min_total_hours + brief.max_total_hours) / 2.0
        target_lesson_hours = (
            self._settings.default_min_hours_per_lesson
            + self._settings.default_max_hours_per_lesson
        ) / 2.0
        total_lessons = max(num_modules, round(target_total / target_lesson_hours))

        min_total = num_modules * brief.min_lessons_per_module
        total_lessons = max(total_lessons, min_total)

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
        module_specs: list[dict],
        feedback: RevisionFeedback | None = None,
    ) -> list[Module]:
        """Construye todos los módulos con sus lecciones, desde las specs."""
        modules: list[Module] = []
        target_total = (brief.min_total_hours + brief.max_total_hours) / 2.0
        hours_per_module = target_total / num_modules

        effective_max = self._effective_max_module_hours(brief, feedback)
        hours_per_module = max(
            float(brief.min_module_hours),
            min(effective_max, hours_per_module),
        )

        goal = (brief.operational_goal or "").strip() or None

        bloom_counters: dict[BloomLevel, int] = {
            level: 0 for level in BLOOM_PROGRESSION
        }
        bloom_title_index: dict[BloomLevel, int] = {
            level: 0 for level in BLOOM_PROGRESSION
        }

        for m_idx, spec in enumerate(module_specs):
            module_id = f"M{m_idx + 1}"
            module_title = spec["title"]
            pillar = spec.get("pillar")

            lessons_in_module = self._lessons_for_module(
                m_idx, num_modules, brief, bloom_plan, bloom_counters
            )

            lessons: list[Lesson] = []
            for l_idx in range(lessons_in_module):
                bloom_level = self._select_bloom_for_lesson(
                    m_idx, l_idx, num_modules, lessons_in_module,
                    brief, bloom_plan, bloom_counters,
                )
                bloom_counters[bloom_level] += 1

                lesson_hours = round(hours_per_module / lessons_in_module, 1)
                lesson_hours = max(
                    self._settings.default_min_hours_per_lesson,
                    min(self._settings.default_max_hours_per_lesson, lesson_hours),
                )

                lesson_title = self._get_lesson_title(
                    bloom_level, bloom_title_index[bloom_level]
                )
                bloom_title_index[bloom_level] += 1

                objective = self._generate_objective(bloom_level, brief.topic, goal)
                key_topics = self._generate_key_topics(
                    bloom_level, brief.topic, l_idx, pillar
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

            # Coherencia: las horas del módulo SON la suma de sus lecciones.
            module_hours = round(sum(l.estimated_hours for l in lessons), 1)

            module = Module(
                module_id=module_id,
                title=module_title,
                description=self._generate_module_description(
                    m_idx, brief.topic, lessons, pillar, goal, spec.get("closing", False)
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
        """Cuántas lecciones debe tener un módulo específico."""
        total_lessons = self._estimate_total_lessons(brief, num_modules)
        base = total_lessons // num_modules
        remainder = total_lessons % num_modules

        count = base + (1 if module_index < remainder else 0)
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
        """Selecciona el nivel de Bloom para una lección específica."""
        required = brief.required_bloom_levels
        required_ordered = [
            level for level in BLOOM_PROGRESSION if level in required
        ]

        global_lesson_pos = (
            (module_index * lessons_in_module + lesson_index)
            / max(1, num_modules * lessons_in_module - 1)
        )

        for level in required_ordered:
            if bloom_counters[level] < bloom_plan[level]:
                level_pos = BLOOM_PROGRESSION.index(level) / max(
                    1, len(BLOOM_PROGRESSION) - 1
                )
                if abs(global_lesson_pos - level_pos) < 0.4:
                    return level

        target_index = int(global_lesson_pos * (len(required_ordered) - 1))
        target_index = max(0, min(len(required_ordered) - 1, target_index))
        return required_ordered[target_index]

    # ----------------------------------------------------------------
    # MÉTODOS PRIVADOS - GENERACIÓN DE TEXTO ESTRUCTURAL
    # ----------------------------------------------------------------
    def _generate_course_title(self, brief: DirectorBrief) -> str:
        """Título del curso: el nombre del instructor si lo dio; si no, por tema."""
        name = (brief.course_name or "").strip()
        if name:
            return name
        return f"Curso de {brief.topic}"

    def _get_lesson_title(
        self, bloom_level: BloomLevel, variant_index: int
    ) -> str:
        titles = LESSON_TITLE_BY_BLOOM.get(bloom_level, ["Contenido de la lección"])
        idx = variant_index % len(titles)
        return titles[idx]

    def _generate_objective(
        self,
        bloom_level: BloomLevel,
        topic: str,
        goal: str | None = None,
    ) -> str:
        """Objetivo por Bloom; si hay objetivo operativo, lo ancla al final."""
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
        base = templates.get(bloom_level, f"{verb} aspectos relevantes de {topic}.")
        if goal:
            return f"{base} Todo orientado a que el alumno logre: {goal}."
        return base

    def _generate_key_topics(
        self,
        bloom_level: BloomLevel,
        topic: str,
        lesson_index: int,
        pillar: str | None = None,
    ) -> list[str]:
        """Temas clave; si el módulo viene de un pilar, este encabeza la lista."""
        base_topics = {
            BloomLevel.REMEMBER: [
                f"Terminología de {topic}",
                "Definiciones clave",
                "Marco normativo aplicable",
            ],
            BloomLevel.UNDERSTAND: [
                f"Principios teóricos de {topic}",
                "Mecanismos y relaciones causales",
                "Comparación de enfoques",
            ],
            BloomLevel.APPLY: [
                "Procedimientos operativos",
                f"Herramientas y técnicas de {topic}",
                "Resolución de problemas estándar",
            ],
            BloomLevel.ANALYZE: [
                "Descomposición de problemas",
                f"Análisis de casos en {topic}",
                "Identificación de patrones",
            ],
            BloomLevel.EVALUATE: [
                "Criterios de evaluación",
                f"Análisis de riesgos en {topic}",
                "Toma de decisiones",
            ],
            BloomLevel.CREATE: [
                "Diseño de soluciones",
                f"Formulación de proyectos en {topic}",
                "Innovación y mejora continua",
            ],
        }
        topics = list(base_topics.get(bloom_level, [f"Contenido de {topic}"]))
        if pillar:
            # El pilar como ancla principal para el Redactor.
            topics = [pillar] + [t for t in topics if t != pillar][:2]
        return topics

    def _generate_module_description(
        self,
        module_index: int,
        topic: str,
        lessons: list[Lesson],
        pillar: str | None = None,
        goal: str | None = None,
        closing: bool = False,
    ) -> str:
        """Descripción del módulo: habla del pilar si lo hay; si no, genérica."""
        bloom_levels_in_module = sorted({l.bloom_level.value for l in lessons})
        num_lessons = len(lessons)
        bloom_txt = ", ".join(bloom_levels_in_module)

        if closing and goal:
            return (
                f"Módulo de cierre e integración del curso de {topic}. "
                f"Consolida lo aprendido en {num_lessons} lecciones "
                f"(niveles: {bloom_txt}) para alcanzar el objetivo final: {goal}."
            )
        if pillar:
            lead = (
                f"Paso del proceso: {pillar}. "
                f"Este módulo desarrolla ese pilar en {num_lessons} lecciones "
                f"(niveles cognitivos: {bloom_txt}) dentro del curso de {topic}."
            )
            if goal:
                lead += f" Aporta directamente a: {goal}."
            return lead

        return (
            f"Módulo {module_index + 1} del curso de {topic}. "
            f"Contiene {num_lessons} lecciones que cubren los niveles "
            f"cognitivos: {bloom_txt}. Enfocado en el desarrollo progresivo "
            f"de competencias en {topic}."
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
        """Valida la matriz contra TODAS las restricciones. Lanza ValueError."""
        errors: list[str] = []

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
        distribution: dict[BloomLevel, int] = {
            level: 0 for level in BloomLevel
        }
        for module in modules:
            for lesson in module.lessons:
                distribution[lesson.bloom_level] += 1
        return distribution

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()