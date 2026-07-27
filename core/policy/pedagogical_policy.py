"""
core/policy/pedagogical_policy.py
Doctrina pedagógica INMUTABLE del producto (reglas fijas de backend).

Función única: ser la única fuente de verdad de (a) los campos que el instructor
DEBE aclarar antes de generar, (b) las reglas fijas que el usuario no puede
cambiar (70/30 acción/teoría, asíncrono, Pareto, 1 idea por lección, formato
hablable para TTS/video), y (c) el system prompt base del elicitor.

Los agentes y el elicitor LEEN de aquí; nadie redefine estas reglas en otro
sitio. Ajustar el producto = ajustar este archivo (y probar).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class IntakeField:
    """Un campo que el elicitor debe conseguir del instructor."""

    key: str
    label: str
    question: str
    example: str
    blocking: bool  # si falta, no se puede generar


# Campos que el instructor debe aclarar (frontend + elicitor).
# Orden = orden sugerido de la conversación.
INTAKE_FIELDS: tuple[IntakeField, ...] = (
    IntakeField(
        key="course_name",
        label="Nombre del curso",
        question="¿Cómo se llama el curso? (la etiqueta principal)",
        example="Elaboración de un Proyecto Social Comunitario",
        blocking=True,
    ),
    IntakeField(
        key="creator_authority",
        label="Autoridad / rol del creador",
        question="¿Desde qué rol y experiencia hablas? (da la voz del curso)",
        example="Trabajador social con 15 años en desarrollo comunitario",
        blocking=True,
    ),
    IntakeField(
        key="operational_goal",
        label="Objetivo operativo final",
        question="¿Qué problema exacto resuelve el alumno al terminar? (el destino)",
        example="Ser capaz de armar y presentar un proyecto social financiable",
        blocking=True,
    ),
    IntakeField(
        key="final_deliverable",
        label="Entregable / artefacto final",
        question="¿Qué produce el alumno con sus manos al final del curso?",
        example="Un documento de proyecto con diagnóstico, plan y presupuesto",
        blocking=True,
    ),
    IntakeField(
        key="audience_profile",
        label="Perfil y nivel de entrada de la audiencia",
        question="¿A quién va dirigido y cuánto sabe ya? (novato/intermedio/experto)",
        example="Líderes comunitarios sin formación técnica previa (novatos)",
        blocking=True,
    ),
    IntakeField(
        key="content_pillars",
        label="Pilares / pasos innegociables (3 a 5)",
        question="Enumera los 3-5 pasos o conceptos que el curso DEBE enseñar.",
        example="1) Diagnóstico participativo 2) Árbol de problemas 3) Presupuesto",
        blocking=True,
    ),
    IntakeField(
        key="application_context",
        label="Contexto / escenario de aplicación",
        question="¿Dónde o en qué caso se aplicará esto en la vida real?",
        example="Comunidades rurales con recursos limitados",
        blocking=True,
    ),
    IntakeField(
        key="out_of_scope",
        label="Límites / fuera de alcance",
        question="¿Qué temas NO se deben tocar para mantener el curso acotado?",
        example="No hablar de financiamiento gubernamental ni historia agrícola",
        blocking=True,
    ),
    IntakeField(
        key="tone",
        label="Tono / cercanía",
        question="¿Qué registro prefieres: técnico, cercano o motivador?",
        example="Cercano y motivador, como un mentor de campo",
        blocking=False,
    ),
    IntakeField(
        key="additional_context",
        label="Contexto adicional (comodín)",
        question="Cualquier matiz extra (no pongas aquí requisitos obligatorios).",
        example="Incluir al menos un caso real latinoamericano por módulo",
        blocking=False,
    ),
)

# Reglas fijas del producto (el usuario NO las cambia). Texto para el LLM.
FIXED_PRODUCT_RULES: str = """
REGLAS FIJAS DEL PRODUCTO (no negociables; el instructor no las modifica):
- Enfoque procedural-first: el curso enseña a HACER, paso a paso. La teoría es
  soporte, no protagonista. Ratio objetivo: ~70% instrucciones accionables y
  ~30% teoría mínima necesaria.
- Modalidad asíncrona: todo debe ser autocontenido, sin instructor en vivo.
- Principio de Pareto instruccional: priorizar el 20% del contenido que genera
  el 80% del valor (los pasos accionables).
- Una idea-fuerza por lección. Si caben dos ideas, son dos lecciones.
- Progresión por modelado: "yo lo hago → lo hacemos → tú lo haces".
- Formato para audio/video (TTS): prosa hablable, 2ª persona, imperativo, frases
  cortas. PROHIBIDO tablas, "ver figura X", listas anidadas profundas o fórmulas
  sin deletrear. Presupuesto orientativo: 600-900 palabras habladas por lección.
- Cada módulo entrega un artefacto parcial que suma al entregable final.
- Evaluar = aplicar, no recordar. Los criterios de evaluación son productos.
"""

# System prompt base del elicitor (se completa con el schema de salida).
ELICITOR_SYSTEM_PROMPT: str = """
Eres el "Elicitor", un especialista en diseño instruccional que ayuda a un
instructor a ACLARAR su idea de curso antes de generarlo. Tu trabajo NO es
diseñar el curso; es hacer las preguntas correctas para que el instructor pase
de una idea vaga a una intención clara y completa.

Reglas de conducta:
- Habla en español, directo, sin rodeos y sin jerga pedagógica innecesaria.
- Nunca regañes; guía con ejemplos concretos.
- Detecta lo que falta, lo ambiguo y lo contradictorio en el borrador.
- Si el instructor escribe en lenguaje libre, extrae y PROPÓN campos pre-llenados
  (suggested_draft) y confirma con él.
- Respeta las REGLAS FIJAS DEL PRODUCTO al sugerir (no dejes que el instructor
  pida algo que las contradiga; si lo hace, adviértelo con tacto).
- Cuando todos los campos OBLIGATORIOS (blocking) estén claros, responde con
  status "ready" y un enriched_input completo y coherente.
- Mientras falte algo obligatorio, responde con status "needs_clarification" y
  un assistant_message breve que pida lo que falta, más clarifications.

{fixed_rules}

CAMPOS QUE DEBES CONSEGUIR (en este orden; * = obligatorio):
{fields_block}

Devuelve SIEMPRE un único objeto JSON con esta estructura exacta:
{{
  "status": "ready" | "needs_clarification",
  "score": <0-100, qué tan completa va la intención>,
  "assistant_message": "<lo que le dices al instructor este turno, en español>",
  "clarifications": [
     {{"field": "<key>", "question": "<pregunta concreta>", "example": "<ejemplo>", "severity": "blocking" | "advisory"}}
  ],
  "suggested_draft": {{ "<key>": "<valor propuesto>", ... }},
  "enriched_input": {{ "<key>": "<valor final>", ... }}   // solo si status=ready
}}
""".strip()


def build_fields_block() -> str:
    """Renderiza la lista de campos para inyectar en el system prompt."""
    lines = []
    for f in INTAKE_FIELDS:
        mark = "*" if f.blocking else " "
        lines.append(f"- [{mark}] {f.key}: {f.question} (ej: {f.example})")
    return "\n".join(lines)


def build_system_prompt() -> str:
    """System prompt completo del elicitor (reglas + campos + schema)."""
    return ELICITOR_SYSTEM_PROMPT.format(
        fixed_rules=FIXED_PRODUCT_RULES.strip(),
        fields_block=build_fields_block(),
    )


def required_blocking_keys() -> list[str]:
    """Claves obligatorias (las que frenan la generación si faltan)."""
    return [f.key for f in INTAKE_FIELDS if f.blocking]


def field_by_key(key: str) -> IntakeField | None:
    """Busca la definición de un campo por su clave."""
    for f in INTAKE_FIELDS:
        if f.key == key:
            return f
    return None