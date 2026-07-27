"""
core/agents/elicitor.py
Agente Elicitor: receptor de datos que ayuda al instructor a aclarar su idea.

Función única: convertir un borrador vago en una intención clara y completa,
mediante un loop conversacional humano-máquina (stateless: el historial viaja en
el request).

Dos cerebros, mismo contrato (ElicitorResponse):
  - modo "llm":   conversacional con IA real (si hay LLM configurado).
  - modo "rules": fallback determinista por checklist (si no hay LLM).
Así el endpoint funciona SIEMPRE; la IA se activa al poner la clave.

El Elicitor NO diseña el curso ni toca a los otros 4 agentes.
"""
import json
import logging

from config.settings import get_settings
from domain.elicitor_models import (
    Clarification,
    ElicitorRequest,
    ElicitorResponse,
    EnrichedInstructorInput,
    Turn,
)
from llm.client import get_llm_client
from policy.pedagogical_policy import (
    INTAKE_FIELDS,
    build_system_prompt,
    field_by_key,
    required_blocking_keys,
)


class ElicitorAgent:
    """Agente de elicitation conversacional con fallback de reglas."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._logger = logging.getLogger(
            f"{self._settings.system_name}.ElicitorAgent"
        )

    # ----------------------------------------------------------------
    # MÉTODO PÚBLICO
    # ----------------------------------------------------------------
    def clarify(self, req: ElicitorRequest) -> ElicitorResponse:
        """
        Procesa un turno del intake. Decide el cerebro (LLM o reglas) y devuelve
        la respuesta normalizada. Nunca lanza: si el LLM falla, cae a reglas.
        """
        draft = self._merge_draft(req)
        client = get_llm_client()

        if client is not None:
            try:
                return self._clarify_with_llm(client, req, draft)
            except Exception as exc:  # noqa: BLE001  (no explotar el turno)
                self._logger.warning(
                    "Elicitor LLM falló (%s). Cayendo a reglas este turno.", exc
                )

        return self._clarify_with_rules(req, draft)

    # ----------------------------------------------------------------
    # CEREBRO 1: LLM CONVERSACIONAL
    # ----------------------------------------------------------------
    def _clarify_with_llm(self, client, req: ElicitorRequest, draft: dict) -> ElicitorResponse:
        messages: list[dict] = [{"role": "system", "content": build_system_prompt()}]

        # Historial previo (stateless: viene del frontend)
        for turn in req.history:
            messages.append({"role": turn.role, "content": turn.content})

        # Turno actual: el borrador + lo que el usuario escribió libre
        user_payload = {
            "draft_actual": draft,
            "mensaje_libre_del_instructor": req.free_text or "(sin mensaje libre)",
            "instruccion": (
                "Revisa el draft y el mensaje libre. Devuelve el JSON con tu "
                "assistant_message y, si falta algo obligatorio, clarifications; "
                "si ya está completo, status=ready con enriched_input."
            ),
        }
        messages.append({"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)})

        raw = client.chat(messages, response_format_json=True)
        data = self._parse_json(raw)
        if data is None:
            raise ValueError("El LLM no devolvió JSON válido.")

        return self._response_from_llm_data(data)

    def _response_from_llm_data(self, data: dict) -> ElicitorResponse:
        """Normaliza el JSON del LLM al contrato (tolerante a campos faltantes)."""
        status = data.get("status", "needs_clarification")
        if status not in ("ready", "needs_clarification"):
            status = "needs_clarification"

        clarifications = [
            Clarification(
                field=str(c.get("field", "")),
                question=str(c.get("question", "¿Puedes aclarar este punto?")),
                example=str(c.get("example", "")),
                severity=c.get("severity", "blocking"),
            )
            for c in (data.get("clarifications") or [])
            if c.get("field")
        ]

        enriched = None
        if status == "ready" and data.get("enriched_input"):
            try:
                enriched = EnrichedInstructorInput(**data["enriched_input"])
            except Exception:  # noqa: BLE001
                enriched = None
                status = "needs_clarification"  # si no valida, no está ready

        return ElicitorResponse(
            status=status,
            score=int(data.get("score", 0) or 0),
            assistant_message=str(
                data.get("assistant_message") or "Cuéntame un poco más del curso."
            ),
            clarifications=clarifications,
            suggested_draft=dict(data.get("suggested_draft") or {}),
            enriched_input=enriched,
            mode="llm",
        )

    # ----------------------------------------------------------------
    # CEREBRO 2: REGLAS (fallback determinista)
    # ----------------------------------------------------------------
    def _clarify_with_rules(self, req: ElicitorRequest, draft: dict) -> ElicitorResponse:
        blocking = required_blocking_keys()
        missing_blocking = [k for k in blocking if not self._filled(draft.get(k))]
        missing_advisory = [
            f.key for f in INTAKE_FIELDS
            if not f.blocking and not self._filled(draft.get(f.key))
        ]

        total = len(INTAKE_FIELDS)
        filled = sum(1 for f in INTAKE_FIELDS if self._filled(draft.get(f.key)))
        score = round(100 * filled / total)

        if not missing_blocking:
            enriched = self._build_enriched(draft)
            return ElicitorResponse(
                status="ready",
                score=score,
                assistant_message=(
                    "Perfecto, ya tengo clara la intención del curso. "
                    "Con esto puedo construir la estructura y el contenido."
                ),
                clarifications=[
                    Clarification(
                        field=k,
                        question=(field_by_key(k).question if field_by_key(k) else k),
                        example=(field_by_key(k).example if field_by_key(k) else ""),
                        severity="advisory",
                    )
                    for k in missing_advisory
                ],
                suggested_draft={},
                enriched_input=enriched,
                mode="rules",
            )

        # Faltan obligatorios: pedirlos con ejemplo
        clarifications = []
        for k in missing_blocking:
            f = field_by_key(k)
            clarifications.append(Clarification(
                field=k,
                question=f.question if f else f"Define {k}",
                example=f.example if f else "",
                severity="blocking",
            ))

        lines = [f"- {c.question} (ej: {c.example})" for c in clarifications[:3]]
        message = (
            "Voy entendiendo tu curso. Para dejarlo bien definido, ayúdame con "
            "esto:\n" + "\n".join(lines)
        )
        return ElicitorResponse(
            status="needs_clarification",
            score=score,
            assistant_message=message,
            clarifications=clarifications,
            suggested_draft={},
            enriched_input=None,
            mode="rules",
        )

    # ----------------------------------------------------------------
    # UTILIDADES
    # ----------------------------------------------------------------
    def _merge_draft(self, req: ElicitorRequest) -> dict:
        """Junta el draft con lo que el LLM/frontend sugirió (el draft manda)."""
        return {k: v for k, v in (req.draft or {}).items() if v not in (None, "")}

    @staticmethod
    def _filled(value) -> bool:
        if value is None:
            return False
        return str(value).strip() != ""

    def _build_enriched(self, draft: dict) -> EnrichedInstructorInput:
        """Construye el input enriquecido desde el draft (modo reglas)."""
        def g(key: str, default: str = "") -> str:
            v = draft.get(key)
            return str(v).strip() if v not in (None, "") else default

        return EnrichedInstructorInput(
            course_name=g("course_name", "Curso sin nombre"),
            creator_authority=g("creator_authority", "Instructor"),
            operational_goal=g("operational_goal", "Resolver el problema del tema"),
            final_deliverable=g("final_deliverable", "Un entregable práctico"),
            audience_profile=g("audience_profile", "Audiencia general"),
            content_pillars=g("content_pillars", "1) Paso inicial 2) Paso final"),
            application_context=g("application_context", "Contexto profesional"),
            out_of_scope=g("out_of_scope", "Sin límites explícitos"),
            tone=g("tone", "cercano") or "cercano",
            additional_context=g("additional_context", ""),
        )

    @staticmethod
    def _parse_json(raw: str) -> dict | None:
        """Parsea JSON tolerante (el LLM a veces envuelve en ```json)."""
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            # Intento de rescate: buscar el primer { ... } balanceado
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    data = json.loads(text[start:end + 1])
                    return data if isinstance(data, dict) else None
                except json.JSONDecodeError:
                    return None
            return None