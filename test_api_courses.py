"""
test_api_courses.py
Valida el módulo de cursos con UN comando: pide generar un curso, confirma que
la cadena de 4 agentes lo produce, que queda guardado, que se lista, que se
consulta por ID, que el aislamiento multi-tenant bloquea a otro colegio, y que
sin token se rechaza.

Usa SOLO la librería estándar. Re-ejecutable (409 de registro lo maneja solo).

PRE-REQUISITO: uvicorn corriendo en OTRA terminal.
Ejecutar: python test_api_courses.py
"""

import json
import sys
import uuid
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = "http://127.0.0.1:8000"

# Tenant 1 (reutiliza el del test de auth si ya existe)
T1_NAME = "Colegio de Ingenieros del Perú"
T1_SLUG = "colegio-ingenieros-peru"
T1_EMAIL = "admin@cip.pe"
T1_PASS = "SuperSecret123"
T1_FULL = "Ana Administradora"

# Tenant 2 (para probar aislamiento multi-tenant)
T2_NAME = "Colegio de Arquitectos del Perú"
T2_SLUG = "colegio-arquitectos-peru"
T2_EMAIL = "admin@cap.pe"
T2_PASS = "SuperSecret456"
T2_FULL = "Luis Administrador"

TOPIC = "Diseño de Estructuras de Acero"


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
    body = urllib.parse.urlencode(fields).encode("utf-8")
    return _request(
        "POST", path, body,
        {"Content-Type": "application/x-www-form-urlencoded"},
    )


def get(path: str, token: str | None = None) -> tuple[int, dict]:
    headers = {"Authorization": f"Bearer {token}"} if token else None
    return _request("GET", path, None, headers)


def register_and_login(slug: str, name: str, email: str,
                       password: str, full: str) -> str:
    """Registra (o reutiliza) un colegio y devuelve su JWT."""
    status, data = post_json("/api/v1/auth/register", {
        "tenant_name": name, "tenant_slug": slug,
        "email": email, "password": password, "full_name": full,
    })
    if status not in (201, 409):
        print(f"      ✗ register {slug} falló ({status}): {data}")
        sys.exit(1)
    status, data = post_form("/api/v1/auth/login", {
        "tenant_slug": slug, "username": email, "password": password,
    })
    if status != 200:
        print(f"      ✗ login {slug} falló ({status}): {data}")
        sys.exit(1)
    return data["access_token"]


# ============================================================
# TEST
# ============================================================

def main() -> None:
    print("=" * 60)
    print("TEST DEL MÓDULO DE CURSOS (API)")
    print("=" * 60)

    # 1. Tokens de dos colegios
    print("[1/7] Autenticando tenant 1 y tenant 2 ...")
    token1 = register_and_login(T1_SLUG, T1_NAME, T1_EMAIL, T1_PASS, T1_FULL)
    token2 = register_and_login(T2_SLUG, T2_NAME, T2_EMAIL, T2_PASS, T2_FULL)
    print("      ✓ dos colegios autenticados")

    # 2. Pedir generación de curso (dispara los 4 agentes)
    print("[2/7] POST /api/v1/courses (generando curso, puede tardar unos segundos) ...")
    status, data = post_json(
        "/api/v1/courses",
        {"topic": TOPIC, "target_audience": "Ingenieros civiles con 2+ años"},
        token1,
    )
    if status != 201:
        print(f"      ✗ crear curso falló ({status}): {data}")
        sys.exit(1)
    course_id = data["id"]
    if data["status"] != "completed":
        print(f"      ✗ status={data['status']} (esperado completed). error={data.get('error_message')}")
        sys.exit(1)
    content = data.get("course_content") or {}
    lessons = content.get("lessons_content") or []
    if len(lessons) == 0:
        print("      ✗ el curso no trae lecciones en course_content")
        sys.exit(1)
    print(f"      ✓ 201 | curso {course_id} | lecciones={len(lessons)} | status=completed")

    # 3. Listar cursos del tenant 1
    print("[3/7] GET /api/v1/courses (listar) ...")
    status, data = get("/api/v1/courses", token1)
    if status != 200 or not isinstance(data, list) or len(data) < 1:
        print(f"      ✗ listar falló ({status}): {data}")
        sys.exit(1)
    print(f"      ✓ 200 | cursos del colegio={len(data)}")

    # 4. Consultar el curso por ID (mismo tenant)
    print("[4/7] GET /api/v1/courses/{id} (mismo colegio) ...")
    status, data = get(f"/api/v1/courses/{course_id}", token1)
    if status != 200 or data.get("topic") != TOPIC:
        print(f"      ✗ consultar falló ({status}): {data}")
        sys.exit(1)
    print(f"      ✓ 200 | topic='{data['topic']}' | status={data['status']}")

    # 5. Aislamiento multi-tenant: tenant 2 NO debe ver el curso de tenant 1
    print("[5/7] GET /api/v1/courses/{id} con token de OTRO colegio (debe 404) ...")
    status, _ = get(f"/api/v1/courses/{course_id}", token2)
    if status != 404:
        print(f"      ✗ aislamiento roto: otro colegio obtuvo {status} (esperado 404)")
        sys.exit(1)
    print("      ✓ 404 | aislamiento multi-tenant correcto")

    # 6. ID inexistente -> 404
    print("[6/7] GET /api/v1/courses/{id inexistente} (debe 404) ...")
    fake_id = str(uuid.uuid4())
    status, _ = get(f"/api/v1/courses/{fake_id}", token1)
    if status != 404:
        print(f"      ✗ id inexistente devolvió {status} (esperado 404)")
        sys.exit(1)
    print("      ✓ 404 | id inexistente manejado")

    # 7. Sin token -> 401
    print("[7/7] POST /api/v1/courses sin token (debe 401) ...")
    status, _ = post_json("/api/v1/courses", {"topic": TOPIC})
    if status not in (401, 403):
        print(f"      ✗ sin token devolvió {status} (esperado 401/403)")
        sys.exit(1)
    print("      ✓ rechazado (401/403)")

    print("=" * 60)
    print("COURSES API OK")
    print("=" * 60)


if __name__ == "__main__":
    main()