"""
test_api_auth.py
Valida el bloque de autenticación de la API con UN comando.
Hace: register -> login -> me -> /health/db -> me-sin-token.
Usa SOLO la librería estándar (no instala nada).
Es re-ejecutable: si el colegio ya existe (409), no falla, sigue con login.

PRE-REQUISITO: uvicorn corriendo en OTRA terminal.
Ejecutar: python test_api_auth.py
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = "http://127.0.0.1:8000"

TENANT_NAME = "Colegio de Ingenieros del Perú"
TENANT_SLUG = "colegio-ingenieros-peru"
EMAIL = "admin@cip.pe"
PASSWORD = "SuperSecret123"
FULL_NAME = "Ana Administradora"


# ============================================================
# CLIENTE HTTP MÍNIMO (stdlib, sin requests/httpx)
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


def post_json(path: str, payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    return _request("POST", path, body, {"Content-Type": "application/json"})


def post_form(path: str, fields: dict) -> tuple[int, dict]:
    body = urllib.parse.urlencode(fields).encode("utf-8")
    return _request(
        "POST", path, body,
        {"Content-Type": "application/x-www-form-urlencoded"},
    )


def get(path: str, token: str | None = None) -> tuple[int, dict]:
    headers = {"Authorization": f"Bearer {token}"} if token else None
    return _request("GET", path, None, headers)


# ============================================================
# TEST
# ============================================================

def main() -> None:
    print("=" * 60)
    print("TEST DE AUTENTICACIÓN (API)")
    print("=" * 60)

    # 1. Registro
    print("[1/4] POST /api/v1/auth/register ...")
    status, data = post_json("/api/v1/auth/register", {
        "tenant_name": TENANT_NAME,
        "tenant_slug": TENANT_SLUG,
        "email": EMAIL,
        "password": PASSWORD,
        "full_name": FULL_NAME,
    })
    if status == 201:
        print(f"      ✓ 201 | colegio creado: {data.get('tenant', {}).get('slug')}")
    elif status == 409:
        print("      ✓ 409 | el colegio ya existía, sigo con login")
    else:
        print(f"      ✗ status {status}: {data}")
        if status == 500 and "bcrypt" in json.dumps(data).lower():
            print("      → arregla con: pip install bcrypt==4.0.1 --force-reinstall")
        sys.exit(1)

    # 2. Login
    print("[2/4] POST /api/v1/auth/login ...")
    status, data = post_form("/api/v1/auth/login", {
        "tenant_slug": TENANT_SLUG,
        "username": EMAIL,
        "password": PASSWORD,
    })
    if status != 200:
        print(f"      ✗ login falló ({status}): {data}")
        sys.exit(1)
    token = data.get("access_token")
    if not token:
        print("      ✗ el login no devolvió access_token")
        sys.exit(1)
    print(f"      ✓ 200 | token OK ({token[:20]}...)")

    # 3. Me (con token)
    print("[3/4] GET /api/v1/auth/me ...")
    status, data = get("/api/v1/auth/me", token)
    if status != 200:
        print(f"      ✗ /me falló ({status}): {data}")
        sys.exit(1)
    if data.get("email") != EMAIL or data.get("tenant", {}).get("slug") != TENANT_SLUG:
        print(f"      ✗ /me devolvió datos inconsistentes: {data}")
        sys.exit(1)
    print(f"      ✓ 200 | {data.get('email')} | rol={data.get('role')} | colegio={data.get('tenant', {}).get('slug')}")

    # 4. Persistencia en base de datos
    print("[4/4] GET /health/db ...")
    status, data = get("/health/db")
    if status != 200:
        print(f"      ✗ /health/db falló ({status}): {data}")
        sys.exit(1)
    tenant_count = data.get("database", {}).get("tenants", 0)
    if tenant_count < 1:
        print(f"      ✗ tenants={tenant_count} (esperado >= 1)")
        sys.exit(1)
    print(f"      ✓ 200 | conectado | tenants={tenant_count}")

    # Extra: /me sin token debe rechazar
    print("[+ ] GET /api/v1/auth/me sin token (debe rechazar) ...")
    status, _ = get("/api/v1/auth/me")
    if status in (401, 403):
        print(f"      ✓ rechazado ({status})")
    else:
        print(f"      ✗ sin token devolvió {status} (esperado 401/403)")
        sys.exit(1)

    print("=" * 60)
    print("AUTH API OK")
    print("=" * 60)


if __name__ == "__main__":
    main()