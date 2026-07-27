"""
test_api_intake.py
Valida el intake conversacional (agente Elicitor) con UN comando.
Hace: register -> login -> /health/intake -> turno 1 (parcial) ->
turno 2 (completo) -> intake-sin-token.
Usa SOLO la librería estándar. Re-ejecutable (409 de registro lo maneja solo).
PRE-REQUISITO: uvicorn corriendo en OTRA terminal.
Ejecutar: python test_api_intake.py
"""
import json
import sys
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8000"

TENANT_NAME = "Colegio Intake Test"
TENANT_SLUG = "intake-test-colegio"
EMAIL = "intake-test@local.dev"
PASSWORD = "TestPass123"
FULL_NAME = "Intake Tester"


# ============================================================
# CLIENTE HTTP MÍNIMO (stdlib)
# ============================================================
def _request(method: str, path: str, body: bytes | None = None,
             headers: dict | None = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, data=body, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"detail": raw}
    except urllib.error.URLError as e:
        print(f"\n✗ No hay servidor en {BASE_URL}: {e.reason}")
        print("  Enciende uvicorn en OTRA terminal y reintenta.")
        sys.exit(1)


def post_json(path: str, payload: dict, token: str | None = None) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return _request("POST", path, body, headers)


def post_form(path: str, fields: dict) -> tuple[int, dict]:
    body = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in fields.items())
    return _request(
        "POST", path, body.encode("utf-8"),
        {"Content-Type": "application/x-www-form-urlencoded"},
    )


def get(path: str, token: str | None = None) -> tuple[int, dict]:
    headers = {"Authorization": f"Bearer {token}"} if token else None
    return _request("GET", path, None, headers)


def register_and_login() -> str:
    status, data = post_json("/api/v1/auth/register", {
        "tenant_name": TENANT_NAME, "tenant_slug": TENANT_SLUG,
        "email": EMAIL, "password": PASSWORD, "full_name": FULL_NAME,
    })
    if status not in (201, 409):
        print(f"      ✗ register falló ({status}): {data}")
        sys.exit(1)
    # Login SIN slug (contrato actual del backend).
    status, data = post_form("/api/v1/auth/login", {
        "username": EMAIL, "password": PASSWORD,
    })
    if status != 200:
        print(f"      ✗ login falló ({status}): {data}")
        sys.exit(1)
    return data["access_token"]


def _valid_response(data: dict) -> bool:
    """Comprueba el contrato mínimo de ElicitorResponse."""
    return (
        isinstance(data.get("score"), int)
        and isinstance(data.get("assistant_message"), str)
        and data.get("assistant_message", "").strip() != ""
        and data.get("mode") in ("rules", "llm")
        and data.get("status") in ("ready", "needs_clarification")
    )


# ============================================================
# TEST
# ============================================================
def main() -> None:
    print("=" * 60)
    print("TEST DEL INTAKE / ELICITOR (API)")
    print("=" * 60)

    # 1. Token
    print("[1/5] Autenticando colegio de test ...")
    token = register_and_login()
    print(f"      ✓ token OK ({token[:20]}...)")

    # 2. Health del intake (¿quedó cargado el router?)
    print("[2/5] GET /health/intake ...")
    status, data = get("/health/intake")
    if status != 200:
        print(f"      ✗ /health/intake devolvió {status}: {data}")
        print("      → tu api/app/main.py no tiene el endpoint; pégalo de nuevo.")
        sys.exit(1)
    if not data.get("available"):
        print("      ✗ intake NO cargado en este arranque:")
        print(f"        {data.get('note')}")
        sys.exit(1)
    print("      ✓ intake cargado y disponible")

    # 3. Turno 1: draft parcial -> debe pedir aclaraciones
    print("[3/5] POST /api/v1/intake (turno 1, draft parcial) ...")
    status, data = post_json("/api/v1/intake", {
        "draft": {"course_name": "Elaboracion de un Proyecto Social Comunitario"},
        "free_text": "Quiero ensenar a hacer proyectos sociales paso a paso para lideres de comunidades con pocos recursos.",
        "history": [],
    }, token)
    if status != 200 or not _valid_response(data):
        print(f"      ✗ turno 1 falló ({status}): {data}")
        sys.exit(1)
    print(f"      ✓ 200 | status={data['status']} | score={data['score']} | mode={data['mode']}")
    print(f"        → {data['assistant_message'][:90]}")

    # 4. Turno 2: draft completo -> en modo rules debe quedar ready
    print("[4/5] POST /api/v1/intake (turno 2, draft completo) ...")
    full_draft = {
        "course_name": "Elaboracion de un Proyecto Social Comunitario",
        "creator_authority": "Trabajador social con 15 anios en desarrollo comunitario",
        "operational_goal": "Que el alumno arme y presente un proyecto social financiable",
        "final_deliverable": "Un documento de proyecto con diagnostico, plan y presupuesto",
        "audience_profile": "Lideres comunitarios sin formacion tecnica previa, nivel novato",
        "content_pillars": "1) Diagnostico participativo 2) Arbol de problemas 3) Plan de accion 4) Presupuesto basico",
        "application_context": "Comunidades rurales con recursos limitados",
        "out_of_scope": "No hablar de financiamiento gubernamental ni historia agricola",
        "tone": "cercano",
        "additional_context": "",
    }
    status, data = post_json("/api/v1/intake", {
        "draft": full_draft,
        "free_text": "",
        "history": [],
    }, token)
    if status != 200 or not _valid_response(data):
        print(f"      ✗ turno 2 falló ({status}): {data}")
        sys.exit(1)
    if data["mode"] == "rules" and data["status"] != "ready":
        print(f"      ✗ en modo rules con draft completo se esperaba ready, salió {data['status']}")
        sys.exit(1)
    ready_ok = data["status"] == "ready" and data.get("enriched_input") is not None
    print(f"      ✓ 200 | status={data['status']} | score={data['score']} | mode={data['mode']} | enriched_input={'sí' if ready_ok else 'n/a'}")

    # 5. Sin token -> 401
    print("[5/5] POST /api/v1/intake sin token (debe rechazar) ...")
    status, _ = post_json("/api/v1/intake", {"draft": {}, "free_text": "hola", "history": []})
    if status not in (401, 403):
        print(f"      ✗ sin token devolvió {status} (esperado 401/403)")
        sys.exit(1)
    print(f"      ✓ rechazado ({status})")

    print("=" * 60)
    print("INTAKE API OK")
    print("=" * 60)


if __name__ == "__main__":
    main()