"""
domain/models.py
Contratos de datos (Pydantic) para la comunicación entre agentes.
Estos modelos son la única interfaz entre los 4 agentes del sistema.
"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================
# ENUMERACIONES
# ============================================================
class BloomLevel(str, Enum):
    """Taxonomía de Bloom - Niveles cognitivos"""

    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


class AgentRole(str, Enum):
    """Roles de los agentes del sistema"""

    DIRECTOR = "director"
    ARCHITECT = "architect"
    AUDITOR = "auditor"
    WRITER = "writer"


class ValidationStatus(str, Enum):
    """Estado de validación de calidad"""

    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


# ============================================================
# MODELOS DE ENTRADA (Input del sistema)
# ============================================================
class TenantRules(BaseModel):
    """
    Reglas de acreditación definidas por el administrador del Tenant.
    Este es el input que el Director gestiona y aplica.
    """

    tenant_id: str = Field(..., description="Identificador único del colegio")
    tenant_name: str = Field(..., description="Nombre del colegio profesional")
    min_total_hours: int = Field(..., ge=1, description="Horas mínimas totales del curso")
    max_total_hours: int = Field(..., ge=1, description="Horas máximas totales del curso")
    min_module_hours: int = Field(..., ge=1, description="Horas mínimas por módulo")
    max_module_hours: int = Field(..., ge=1, description="Horas máximas por módulo")
    required_bloom_levels: List[BloomLevel] = Field(
        ...,
        description="Niveles de Bloom que DEBEN estar presentes en el curso",
    )
    max_lessons_per_module: int = Field(..., ge=1, description="Máximo de lecciones por módulo")
    min_lessons_per_module: int = Field(..., ge=1, description="Mínimo de lecciones por módulo")
    custom_restrictions: Optional[str] = Field(
        None,
        description="Restricciones adicionales en lenguaje natural",
    )

    @field_validator("max_total_hours")
    @classmethod
    def validate_hours_range(cls, v, info):
        if "min_total_hours" in info.data and v < info.data["min_total_hours"]:
            raise ValueError("max_total_hours debe ser >= min_total_hours")
        return v

    @field_validator("max_module_hours")
    @classmethod
    def validate_module_hours_range(cls, v, info):
        if "min_module_hours" in info.data and v < info.data["min_module_hours"]:
            raise ValueError("max_module_hours debe ser >= min_module_hours")
        return v

    @field_validator("max_lessons_per_module")
    @classmethod
    def validate_lessons_range(cls, v, info):
        if "min_lessons_per_module" in info.data and v < info.data["min_lessons_per_module"]:
            raise ValueError("max_lessons_per_module debe ser >= min_lessons_per_module")
        return v


class InstructorInput(BaseModel):
    """
    Input del instructor.

    Campos clásicos (topic/target_audience/additional_context) se conservan para
    retrocompatibilidad con el CLI y con la API actual. Los campos de intención
    del elicitor (course_name, operational_goal, content_pillars, etc.) son
    OPCIONALES: cuando el frontend envíe la intención enriquecida vendrán
    poblados y los agentes los usarán como "huesos" del curso; cuando no (CLI o
    llamada vieja), quedan en None y el motor cae al comportamiento por tema.
    """

    # --- Campos clásicos (retrocompatibles) ---
    topic: str = Field(..., min_length=5, description="Tema técnico del curso")
    target_audience: Optional[str] = Field(
        None,
        description="Descripción de la audiencia objetivo (opcional)",
    )
    additional_context: Optional[str] = Field(
        None,
        description="Contexto adicional proporcionado por el instructor",
    )

    # --- Intención enriquecida (elicitor) - todos opcionales ---
    course_name: Optional[str] = Field(
        None,
        description="Nombre/etiqueta principal del curso (tal como lo nombró el instructor).",
    )
    creator_authority: Optional[str] = Field(
        None,
        description="Rol y experiencia desde la que habla el creador (define la voz).",
    )
    operational_goal: Optional[str] = Field(
        None,
        description="Objetivo operativo final: qué problema resuelve / qué sabrá hacer el alumno.",
    )
    final_deliverable: Optional[str] = Field(
        None,
        description="Artefacto tangible que entrega el alumno al terminar.",
    )
    audience_profile: Optional[str] = Field(
        None,
        description="Perfil y nivel de entrada de la audiencia (novato/intermedio/experto).",
    )
    content_pillars: Optional[str] = Field(
        None,
        description="3-5 pilares/pasos innegociables (los 'huesos' del índice; cada uno = un módulo).",
    )
    application_context: Optional[str] = Field(
        None,
        description="Escenario/caso real donde se aplicará el conocimiento.",
    )
    out_of_scope: Optional[str] = Field(
        None,
        description="Temas que NO deben tocarse (acotan duración y evitan dispersión).",
    )
    tone: Optional[str] = Field(
        None,
        description="Registro/tono del curso (técnico/cercano/motivador).",
    )


# ============================================================
# MODELO DE BRIEF DEL DIRECTOR (Output del Director → Input del Arquitecto)
# ============================================================
class DirectorBrief(BaseModel):
    """
    Brief estructurado que el Director emite hacia el Arquitecto Curricular.
    Contiene el tema del instructor + todas las restricciones del Tenant
    ya procesadas + la intención enriquecida del instructor (si la hay),
    listas para ser aplicadas en el diseño curricular.
    """

    course_id: str = Field(..., description="ID único generado para el curso")
    topic: str = Field(..., min_length=5, description="Tema técnico del instructor")
    target_audience: Optional[str] = Field(
        None,
        description="Audiencia objetivo (si el instructor la proporcionó)",
    )
    additional_context: Optional[str] = Field(
        None,
        description="Contexto adicional del instructor",
    )

    # --- Intención enriquecida propagada desde InstructorInput (opcional) ---
    course_name: Optional[str] = Field(
        None,
        description="Nombre/etiqueta principal del curso.",
    )
    creator_authority: Optional[str] = Field(
        None,
        description="Voz/autoridad del creador.",
    )
    operational_goal: Optional[str] = Field(
        None,
        description="Objetivo operativo final (destino del backward design).",
    )
    final_deliverable: Optional[str] = Field(
        None,
        description="Entregable/artefacto final del alumno.",
    )
    audience_profile: Optional[str] = Field(
        None,
        description="Perfil y nivel de entrada de la audiencia.",
    )
    content_pillars: Optional[str] = Field(
        None,
        description="Pilares/pasos innegociables (esqueleto de módulos).",
    )
    application_context: Optional[str] = Field(
        None,
        description="Escenario real de aplicación.",
    )
    out_of_scope: Optional[str] = Field(
        None,
        description="Temas fuera de alcance.",
    )
    tone: Optional[str] = Field(
        None,
        description="Tono/registro del curso.",
    )

    # --- Restricciones del Tenant ---
    tenant_id: str = Field(..., description="ID del Tenant (colegio)")
    tenant_name: str = Field(..., description="Nombre del colegio profesional")
    min_total_hours: int = Field(..., ge=1, description="Horas mínimas totales")
    max_total_hours: int = Field(..., ge=1, description="Horas máximas totales")
    min_module_hours: int = Field(..., ge=1, description="Horas mínimas por módulo")
    max_module_hours: int = Field(..., ge=1, description="Horas máximas por módulo")
    required_bloom_levels: List[BloomLevel] = Field(
        ...,
        description="Niveles de Bloom obligatorios en el curso",
    )
    min_lessons_per_module: int = Field(..., ge=1, description="Mínimo de lecciones por módulo")
    max_lessons_per_module: int = Field(..., ge=1, description="Máximo de lecciones por módulo")
    custom_restrictions: Optional[str] = Field(
        None,
        description="Restricciones adicionales del Tenant",
    )
    constraints_summary: List[str] = Field(
        ...,
        min_length=1,
        description="Resumen explícito de todas las restricciones en lenguaje claro",
    )
    created_at: str = Field(..., description="Timestamp de creación del brief (ISO 8601)")


# ============================================================
# MODELOS DE ARQUITECTURA CURRICULAR (Output del Arquitecto)
# ============================================================
class Lesson(BaseModel):
    """
    Una lección individual dentro de un módulo.
    """

    lesson_id: str = Field(..., description="ID único de la lección (ej: M1L1)")
    title: str = Field(..., min_length=3, description="Título de la lección")
    bloom_level: BloomLevel = Field(..., description="Nivel de Bloom de esta lección")
    estimated_hours: float = Field(..., gt=0, description="Horas estimadas de la lección")
    learning_objective: str = Field(
        ...,
        min_length=10,
        description="Objetivo de aprendizaje específico",
    )
    key_topics: List[str] = Field(
        ...,
        min_length=1,
        description="Temas clave que cubre la lección",
    )


class Module(BaseModel):
    """
    Un módulo del curso, compuesto por múltiples lecciones.
    """

    module_id: str = Field(..., description="ID único del módulo (ej: M1)")
    title: str = Field(..., min_length=3, description="Título del módulo")
    description: str = Field(..., min_length=10, description="Descripción del módulo")
    estimated_hours: float = Field(..., gt=0, description="Horas totales del módulo")
    lessons: List[Lesson] = Field(..., min_length=1, description="Lecciones del módulo")

    @field_validator("lessons")
    @classmethod
    def validate_lesson_count(cls, v):
        if len(v) == 0:
            raise ValueError("Un módulo debe tener al menos una lección")
        return v


class CourseMatrix(BaseModel):
    """
    Matriz curricular completa: output del Agente Arquitecto.
    Esta es la estructura que el Auditor validará.
    """

    course_id: str = Field(..., description="ID único del curso")
    course_title: str = Field(..., min_length=5, description="Título del curso")
    topic: str = Field(..., description="Tema técnico original del instructor")
    total_estimated_hours: float = Field(..., gt=0, description="Horas totales del curso")
    modules: List[Module] = Field(..., min_length=1, description="Módulos del curso")
    bloom_distribution: dict[BloomLevel, int] = Field(
        ...,
        description="Distribución de niveles de Bloom en el curso",
    )

    @field_validator("modules")
    @classmethod
    def validate_module_count(cls, v):
        if len(v) == 0:
            raise ValueError("Un curso debe tener al menos un módulo")
        return v


# ============================================================
# MODELOS DE AUDITORÍA (Output del Auditor)
# ============================================================
class QualityIssue(BaseModel):
    """
    Un problema específico detectado por el Auditor.
    """

    issue_id: str = Field(..., description="ID único del problema")
    severity: str = Field(..., pattern="^(critical|major|minor)$", description="Severidad del problema")
    component: str = Field(..., description="Componente afectado (module_id o lesson_id)")
    description: str = Field(..., min_length=10, description="Descripción del problema")
    suggestion: str = Field(..., min_length=10, description="Sugerencia de corrección")


class RevisionFeedback(BaseModel):
    """
    Feedback estructurado que el Auditor devuelve al Arquitecto cuando el
    curso NO es aprobado. Es lo que hace funcional al loop de revisión:
    el Arquitecto aplica estos ajustes en `revise()` en vez de regenerar
    a ciegas (que, al ser determinista, produciría el mismo resultado).

    Todos los campos son opcionales; solo se llenan los que aplican.
    """

    module_hours_cap: Optional[float] = Field(
        None,
        description=(
            "Techo de horas por módulo que el Arquitecto debe respetar en la "
            "revisión (p.ej. la carga cognitiva máxima). Si es None, no cambia."
        ),
    )
    missing_bloom_levels: List[BloomLevel] = Field(
        default_factory=list,
        description="Niveles de Bloom requeridos que faltan y deben añadirse.",
    )
    add_lessons: bool = Field(
        default=False,
        description="Indica que hay módulos con déficit de lecciones/horas.",
    )
    notes: List[str] = Field(
        default_factory=list,
        description="Notas accionables derivadas de los issues detectados.",
    )


class QualityReport(BaseModel):
    """
    Reporte de calidad: output del Agente Auditor.
    """

    course_id: str = Field(..., description="ID del curso auditado")
    status: ValidationStatus = Field(..., description="Estado de la validación")
    total_issues: int = Field(..., ge=0, description="Número total de problemas")
    critical_issues: int = Field(..., ge=0, description="Número de problemas críticos")
    issues: List[QualityIssue] = Field(..., description="Lista de problemas detectados")
    summary: str = Field(..., min_length=10, description="Resumen ejecutivo de la auditoría")
    recommendations: List[str] = Field(..., description="Recomendaciones generales")
    feedback: Optional[RevisionFeedback] = Field(
        None,
        description=(
            "Feedback estructurado para el Arquitecto. Solo presente cuando "
            "el estado NO es APPROVED."
        ),
    )


# ============================================================
# MODELOS DE CONTENIDO FINAL (Output del Redactor)
# ============================================================
class LessonContent(BaseModel):
    """
    Contenido completo de una lección: output del Agente Redactor.
    """

    lesson_id: str = Field(..., description="ID de la lección")
    title: str = Field(..., description="Título de la lección")
    full_content: str = Field(
        ...,
        min_length=100,
        description="Contenido completo de la lección en formato estructurado",
    )
    activities: List[str] = Field(..., description="Actividades de aprendizaje")
    assessment_criteria: List[str] = Field(..., description="Criterios de evaluación")
    estimated_hours: float = Field(..., gt=0, description="Horas estimadas")


class CourseContent(BaseModel):
    """
    Contenido completo del curso: output final del sistema.
    """

    course_id: str = Field(..., description="ID del curso")
    course_title: str = Field(..., description="Título del curso")
    lessons_content: List[LessonContent] = Field(
        ...,
        min_length=1,
        description="Contenido de todas las lecciones",
    )
    generated_at: str = Field(..., description="Timestamp de generación (ISO 8601)")


# ============================================================
# MODELOS DE COMUNICACIÓN INTER-AGENTES
# ============================================================
class AgentMessage(BaseModel):
    """
    Mensaje genérico entre agentes.
    Todos los agentes se comunican EXCLUSIVAMENTE con este formato.
    """

    sender: AgentRole = Field(..., description="Agente que envía el mensaje")
    receiver: AgentRole = Field(..., description="Agente que recibe el mensaje")
    message_type: str = Field(..., description="Tipo de mensaje (ej: 'director_brief', 'course_matrix', 'quality_report')")
    payload: dict = Field(..., description="Datos del mensaje (debe validar contra el modelo correspondiente)")
    timestamp: str = Field(..., description="Timestamp del mensaje (ISO 8601)")