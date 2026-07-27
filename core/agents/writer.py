"""
agents/writer.py
Agente Redactor: cuarto y último agente de la cadena.
Responsabilidad única:
  - Recibir la CourseMatrix aprobada por el Auditor (y, opcionalmente, el
    DirectorBrief con la intención del instructor).
  - Generar el contenido completo de cada lección: texto estructurado,
    actividades de aprendizaje, criterios de evaluación.
  - Si recibe la intención, aplicarla al contenido:
      * creator_authority -> voz del narrador (meta para TTS/producción).
      * tone              -> registro (meta para TTS/producción).
      * application_context -> sitúa los ejemplos ("aplicado a...").
      * operational_goal  -> ancla de backward design en el cierre.
      * final_deliverable -> recordatorio del artefacto final en el cierre.
      * out_of_scope      -> bloque "fuera de alcance" (no desarrollar).
    Si NO recibe brief (brief=None), redacta como siempre (retrocompatible).
  - Producir el CourseContent final (output del sistema).
  - Emitir un AgentMessage con el CourseContent como payload.
El Redactor NO valida ni rediseña. Solo ejecuta contenido.
"""
import logging
from datetime import datetime, timezone

from domain.models import (
    CourseMatrix,
    Lesson,
    LessonContent,
    CourseContent,
    AgentMessage,
    AgentRole,
    BloomLevel,
    DirectorBrief,
)
from config.settings import get_settings


# ============================================================
# PLANTILLAS DE CONTENIDO POR NIVEL DE BLOOM
# ============================================================
CONTENT_INTRO_TEMPLATES: dict[BloomLevel, str] = {
    BloomLevel.REMEMBER: (
        "En esta lección se establecen las bases conceptuales fundamentales. "
        "El objetivo es que el participante adquiera el vocabulario técnico, "
        "las definiciones esenciales y los referentes normativos que "
        "sustentan {topic}. Se espera que al finalizar, el participante "
        "pueda reconocer y reproducir con precisión los conceptos clave."
    ),
    BloomLevel.UNDERSTAND: (
        "Esta lección profundiza en la comprensión de los principios y "
        "mecanismos subyacentes de {topic}. No basta con memorizar: "
        "el participante debe ser capaz de explicar con sus propias palabras, "
        "interpretar relaciones causales y comparar enfoques teóricos "
        "relevantes."
    ),
    BloomLevel.APPLY: (
        "En esta lección el participante transita del conocimiento teórico "
        "a la ejecución práctica. Se trabajarán métodos, procedimientos y "
        "herramientas operativas de {topic} en contextos controlados, "
        "buscando que el participante resuelva problemas estándar con "
        "autonomía y rigor técnico."
    ),
    BloomLevel.ANALYZE: (
        "Esta lección desarrolla la capacidad de descomponer problemas "
        "complejos en sus elementos constitutivos. El participante aprenderá "
        "a examinar estructuras, identificar patrones, diagnosticar "
        "situaciones y establecer correlaciones en el ámbito de {topic}."
    ),
    BloomLevel.EVALUATE: (
        "En esta lección el participante ejercita el juicio crítico. "
        "Se trabaja la evaluación de alternativas, la valoración de "
        "riesgos y beneficios, y la toma de decisiones fundamentada "
        "en evidencia dentro del campo de {topic}."
    ),
    BloomLevel.CREATE: (
        "Esta lección culmina el proceso cognitivo con la generación de "
        "propuestas originales. El participante integrará todo lo aprendido "
        "para diseñar soluciones innovadoras, formular proyectos y crear "
        "modelos propios en {topic}."
    ),
}

CONTENT_DEVELOPMENT_TEMPLATE: str = (
    "\n\n## Desarrollo del Contenido\n\n"
    "{sections}"
)

CONTENT_SECTION_TEMPLATE: str = (
    "### {index}. {subtopic}\n\n"
    "{body}\n"
)

CONTENT_SECTION_BODIES: dict[BloomLevel, str] = {
    BloomLevel.REMEMBER: (
        "Se presentan las definiciones formales, clasificaciones y "
        "terminología normativa asociada a este tema. El participante "
        "debe registrar los conceptos en un glosario técnico personal "
        "y verificar su comprensión mediante autoevaluación."
    ),
    BloomLevel.UNDERSTAND: (
        "Se explican los principios teóricos, se ilustran con ejemplos "
        "y se establecen las relaciones causales entre los conceptos. "
        "El participante debe ser capaz de parafrasear los principios "
        "y construir un mapa conceptual que integre las ideas centrales."
    ),
    BloomLevel.APPLY: (
        "Se describen los procedimientos paso a paso, se demuestran técnicas "
        "y se proporcionan guías de ejecución. El participante realiza "
        "ejercicios guiados y resuelve problemas estándar aplicando "
        "los métodos presentados."
    ),
    BloomLevel.ANALYZE: (
        "Se presenta un caso o situación compleja que el participante "
        "debe descomponer en sus componentes. Se guía el análisis "
        "mediante preguntas estructuradas, matrices de comparación "
        "y herramientas de diagnóstico."
    ),
    BloomLevel.EVALUATE: (
        "Se plantean escenarios con múltiples alternativas de solución. "
        "El participante debe aplicar criterios de evaluación explícitos, "
        "ponderar ventajas y desventajas, y justificar su decisión "
        "con argumentos técnicos fundamentados."
    ),
    BloomLevel.CREATE: (
        "Se propone un reto de diseño o formulación que requiere "
        "integrar conocimientos de todas las lecciones anteriores. "
        "El participante desarrolla una propuesta original siguiendo "
        "un proceso estructurado de creación."
    ),
}

CONTENT_CLOSING_TEMPLATE: str = (
    "\n\n## Síntesis y Cierre\n\n"
    "En esta lección se abordó: {objective}. "
    "Los puntos clave tratados fueron: {key_points}. "
    "Este contenido se conecta con las lecciones posteriores del módulo, "
    "donde se profundizará en la aplicación y el análisis de estos "
    "conceptos en contextos más complejos de {topic}."
)


# ============================================================
# ACTIVIDADES POR NIVEL DE BLOOM
# ============================================================
ACTIVITIES_BY_BLOOM: dict[BloomLevel, list[str]] = {
    BloomLevel.REMEMBER: [
        "Elaborar un glosario técnico con al menos 15 términos clave de la lección.",
        "Completar un cuestionario de reconocimiento de conceptos (opción múltiple).",
        "Construir un mapa conceptual que relacione las definiciones presentadas.",
        "Realizar una línea de tiempo con los hitos normativos del tema.",
    ],
    BloomLevel.UNDERSTAND: [
        "Redactar un resumen ejecutivo de los principios teóricos en máximo 500 palabras.",
        "Elaborar un cuadro comparativo entre al menos dos enfoques teóricos del tema.",
        "Explicar oralmente (o por escrito) un concepto central como si se dirigiera a un colega no especialista.",
        "Construir un diagrama de flujo que ilustre las relaciones causales entre los conceptos.",
    ],
    BloomLevel.APPLY: [
        "Resolver un ejercicio práctico estándar siguiendo el procedimiento presentado.",
        "Aplicar una herramienta o técnica específica a un caso proporcionado por el instructor.",
        "Simular un procedimiento operativo y documentar cada paso realizado.",
        "Implementar una solución técnica en un entorno controlado y registrar resultados.",
    ],
    BloomLevel.ANALYZE: [
        "Analizar un estudio de caso real y descomponerlo en sus componentes estructurales.",
        "Elaborar una matriz de diagnóstico identificando causas, efectos y correlaciones.",
        "Comparar dos soluciones existentes y documentar diferencias estructurales.",
        "Identificar patrones en un conjunto de datos o situaciones proporcionadas.",
    ],
    BloomLevel.EVALUATE: [
        "Evaluar dos o más alternativas de solución usando una rúbrica de criterios técnicos.",
        "Realizar un análisis de riesgos y beneficios de una decisión técnica.",
        "Participar en un debate estructurado defendiendo una postura con evidencia.",
        "Emitir un dictamen técnico justificado sobre un caso proporcionado.",
    ],
    BloomLevel.CREATE: [
        "Diseñar una propuesta de solución original para un problema no resuelto.",
        "Formular un proyecto integrador que combine conocimientos de todo el módulo.",
        "Desarrollar un prototipo o modelo conceptual y documentar el proceso creativo.",
        "Elaborar una guía o manual técnico propio basado en lo aprendido.",
    ],
}


# ============================================================
# CRITERIOS DE EVALUACIÓN POR NIVEL DE BLOOM
# ============================================================
ASSESSMENT_BY_BLOOM: dict[BloomLevel, list[str]] = {
    BloomLevel.REMEMBER: [
        "Identifica correctamente al menos el 90% de los términos técnicos en una prueba de reconocimiento.",
        "Reproduce definiciones clave con precisión terminológica.",
        "Lista los elementos de una clasificación o taxonomía sin omisiones significativas.",
    ],
    BloomLevel.UNDERSTAND: [
        "Explica los principios teóricos con sus propias palabras sin distorsión conceptual.",
        "Compara correctamente al menos dos enfoques identificando similitudes y diferencias.",
        "Interpreta relaciones causales y las representa en un diagrama coherente.",
    ],
    BloomLevel.APPLY: [
        "Aplica el procedimiento correcto a un problema estándar sin errores de ejecución.",
        "Implementa la técnica adecuada según el contexto del problema planteado.",
        "Resuelve el ejercicio dentro de los parámetros técnicos establecidos.",
    ],
    BloomLevel.ANALYZE: [
        "Descompone un problema complejo en sus elementos constitutivos de forma sistemática.",
        "Identifica patrones y correlaciones relevantes en los datos proporcionados.",
        "Diferencia entre causas raíz y síntomas en un caso de análisis.",
    ],
    BloomLevel.EVALUATE: [
        "Justifica su decisión con al menos tres argumentos técnicos fundamentados.",
        "Aplica criterios de evaluación explícitos y ponderados de forma consistente.",
        "Identifica riesgos y beneficios de cada alternativa antes de emitir juicio.",
    ],
    BloomLevel.CREATE: [
        "Presenta una propuesta original que integra conocimientos de múltiples lecciones.",
        "La solución propuesta es técnicamente viable y está documentada con rigor.",
        "El producto final demuestra pensamiento independiente y creatividad fundamentada.",
    ],
}


class WriterAgent:
    """
    Agente Redactor.
    Genera el contenido completo de cada lección a partir
    de la CourseMatrix aprobada y, si la recibe, de la intención del instructor.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._logger = logging.getLogger(
            f"{self._settings.system_name}.WriterAgent"
        )

    # ----------------------------------------------------------------
    # MÉTODO PÚBLICO PRINCIPAL
    # ----------------------------------------------------------------
    def process(
        self,
        matrix: CourseMatrix,
        brief: DirectorBrief | None = None,
    ) -> AgentMessage:
        """
        Genera el contenido completo del curso a partir de la CourseMatrix.
        Si se pasa `brief`, aplica la intención del instructor al contenido.
        Retorna un AgentMessage con el CourseContent como payload.
        """
        self._logger.info(
            "WriterAgent iniciado | Curso: %s | Módulos: %d | Intención: %s",
            matrix.course_id,
            len(matrix.modules),
            "SÍ" if brief is not None else "no",
        )

        intent = self._extract_intent(brief)

        lessons_content: list[LessonContent] = []
        for module in matrix.modules:
            self._logger.info(
                "Redactando módulo %s: '%s' (%d lecciones)",
                module.module_id,
                module.title,
                len(module.lessons),
            )
            for lesson in module.lessons:
                content = self._write_lesson(lesson, matrix.topic, intent)
                lessons_content.append(content)
                self._logger.info(
                    "  Lección %s redactada: '%s' [%s] (%.1fh)",
                    lesson.lesson_id,
                    lesson.title,
                    lesson.bloom_level.value,
                    lesson.estimated_hours,
                )

        course_content = CourseContent(
            course_id=matrix.course_id,
            course_title=matrix.course_title,
            lessons_content=lessons_content,
            generated_at=self._now_iso(),
        )

        self._logger.info(
            "CourseContent generado | Curso: %s | Lecciones: %d | "
            "Generado: %s",
            course_content.course_id,
            len(course_content.lessons_content),
            course_content.generated_at,
        )

        message = AgentMessage(
            sender=AgentRole.WRITER,
            receiver=AgentRole.DIRECTOR,
            message_type="course_content",
            payload=course_content.model_dump(mode="json"),
            timestamp=self._now_iso(),
        )
        self._logger.info(
            "AgentMessage emitido: Redactor → Director | Tipo: %s",
            message.message_type,
        )
        return message

    # ----------------------------------------------------------------
    # INTENCIÓN DEL INSTRUCTOR (normalización segura)
    # ----------------------------------------------------------------
    def _extract_intent(self, brief: DirectorBrief | None) -> dict[str, str | None]:
        """
        Extrae y normaliza los campos de intención del brief.
        Si brief es None, devuelve todo en None (comportamiento clásico).
        """
        def g(value: str | None) -> str | None:
            if value is None:
                return None
            text = value.strip()
            return text or None

        if brief is None:
            return {
                "voice": None,
                "tone": None,
                "goal": None,
                "deliverable": None,
                "scenario": None,
                "out_of_scope": None,
            }
        return {
            "voice": g(brief.creator_authority),
            "tone": g(brief.tone),
            "goal": g(brief.operational_goal),
            "deliverable": g(brief.final_deliverable),
            "scenario": g(brief.application_context),
            "out_of_scope": g(brief.out_of_scope),
        }

    # ----------------------------------------------------------------
    # MÉTODOS PRIVADOS - REDACCIÓN
    # ----------------------------------------------------------------
    def _write_lesson(
        self,
        lesson: Lesson,
        topic: str,
        intent: dict[str, str | None],
    ) -> LessonContent:
        full_content = self._build_full_content(lesson, topic, intent)
        activities = self._get_activities(lesson.bloom_level)
        assessment = self._get_assessment_criteria(lesson.bloom_level)
        return LessonContent(
            lesson_id=lesson.lesson_id,
            title=lesson.title,
            full_content=full_content,
            activities=activities,
            assessment_criteria=assessment,
            estimated_hours=lesson.estimated_hours,
        )

    def _build_full_content(
        self,
        lesson: Lesson,
        topic: str,
        intent: dict[str, str | None],
    ) -> str:
        parts: list[str] = []

        # --- Título ---
        parts.append(f"# {lesson.title}\n")

        # --- Metadatos (incluye voz/registro para producción TTS/video) ---
        meta = (
            f"**ID:** {lesson.lesson_id} | "
            f"**Nivel de Bloom:** {lesson.bloom_level.value} | "
            f"**Duración estimada:** {lesson.estimated_hours}h"
        )
        if intent["voice"]:
            meta += f"\n**Voz del narrador:** {intent['voice']}"
        if intent["tone"]:
            meta += f"\n**Registro:** {intent['tone']}"
        parts.append(meta + "\n")

        # --- Objetivo de aprendizaje ---
        parts.append(f"\n## Objetivo de Aprendizaje\n\n{lesson.learning_objective}\n")

        # --- Introducción ---
        intro_template = CONTENT_INTRO_TEMPLATES.get(
            lesson.bloom_level,
            "En esta lección se abordarán los contenidos fundamentales de {topic}.",
        )
        intro = intro_template.format(topic=topic)
        if intent["scenario"]:
            intro += (
                f" Mantén siempre presente el escenario real de aplicación: "
                f"{intent['scenario']}."
            )
        parts.append(f"\n## Introducción\n\n{intro}\n")

        # --- Desarrollo (secciones por cada key_topic) ---
        sections_text = ""
        body_template = CONTENT_SECTION_BODIES.get(
            lesson.bloom_level,
            "Se desarrollan los contenidos principales del tema.",
        )
        for idx, subtopic in enumerate(lesson.key_topics, 1):
            section = CONTENT_SECTION_TEMPLATE.format(
                index=idx,
                subtopic=subtopic,
                body=body_template,
            )
            sections_text += section
        development = CONTENT_DEVELOPMENT_TEMPLATE.format(sections=sections_text)
        parts.append(development)

        # --- Síntesis y cierre (con anclas de backward design) ---
        key_points = ", ".join(lesson.key_topics)
        closing = CONTENT_CLOSING_TEMPLATE.format(
            objective=lesson.learning_objective,
            key_points=key_points,
            topic=topic,
        )
        if intent["goal"]:
            closing += f" Todo lo visto aporta a que el alumno logre: {intent['goal']}."
        if intent["deliverable"]:
            closing += (
                f" Recuerda que el artefacto final del curso es: "
                f"{intent['deliverable']}; cada lección suma una pieza hacia él."
            )
        parts.append(closing)

        # --- Nota de producción: fuera de alcance (no desarrollar en audio/video) ---
        if intent["out_of_scope"]:
            parts.append(
                "\n\n## Fuera de alcance (NO desarrollar)\n\n"
                f"{intent['out_of_scope']}\n\n"
                "_Nota de producción: estos temas quedan excluidos del guion "
                "y del audio para mantener el curso acotado._"
            )

        return "".join(parts)

    def _get_activities(self, bloom_level: BloomLevel) -> list[str]:
        return ACTIVITIES_BY_BLOOM.get(bloom_level, [
            "Realizar las actividades propuestas por el instructor.",
        ])

    def _get_assessment_criteria(
        self, bloom_level: BloomLevel
    ) -> list[str]:
        return ASSESSMENT_BY_BLOOM.get(bloom_level, [
            "Cumplir con los criterios de evaluación establecidos por el instructor.",
        ])

    # ----------------------------------------------------------------
    # UTILIDADES
    # ----------------------------------------------------------------
    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()