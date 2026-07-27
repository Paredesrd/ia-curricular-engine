"""
api/tests/test_auth.py
Tests de autenticación: registro, login, /me.

CONTRATO: el login NO usa tenant_slug (el backend deduce el colegio desde el
email). El registro SÍ lo usa (crea el tenant con ese slug). Estos tests
reflejan ese contrato.
"""


def test_register_success(client):
    """Registro exitoso retorna 201 con usuario y tenant."""
    resp = client.post("/api/v1/auth/register", json={
        "tenant_name": "Colegio de Test",
        "tenant_slug": "colegio-test",
        "email": "test@test.com",
        "password": "TestPass123",
        "full_name": "Test User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "test@test.com"
    assert data["tenant"]["slug"] == "colegio-test"


def test_register_duplicate_slug(client):
    """Registro con slug duplicado retorna 409."""
    client.post("/api/v1/auth/register", json={
        "tenant_name": "Colegio de Test",
        "tenant_slug": "colegio-test",
        "email": "test@test.com",
        "password": "TestPass123",
        "full_name": "Test User",
    })
    resp = client.post("/api/v1/auth/register", json={
        "tenant_name": "Colegio de Test Duplicado",
        "tenant_slug": "colegio-test",
        "email": "test2@test.com",
        "password": "TestPass456",
        "full_name": "Test User 2",
    })
    assert resp.status_code == 409


def test_login_success(client):
    """Login exitoso retorna 200 con access_token (sin tenant_slug)."""
    client.post("/api/v1/auth/register", json={
        "tenant_name": "Colegio de Test",
        "tenant_slug": "colegio-test",
        "email": "test@test.com",
        "password": "TestPass123",
        "full_name": "Test User",
    })
    resp = client.post("/api/v1/auth/login", data={
        "username": "test@test.com",
        "password": "TestPass123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_invalid_credentials(client):
    """Login con contraseña incorrecta retorna 401 (sin tenant_slug)."""
    client.post("/api/v1/auth/register", json={
        "tenant_name": "Colegio de Test",
        "tenant_slug": "colegio-test",
        "email": "test@test.com",
        "password": "TestPass123",
        "full_name": "Test User",
    })
    resp = client.post("/api/v1/auth/login", data={
        "username": "test@test.com",
        "password": "WrongPass",
    })
    assert resp.status_code == 401


def test_me_with_token(client, auth_token):
    """/me con token válido retorna 200 con datos del usuario."""
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@test.com"


def test_me_without_token(client):
    """/me sin token retorna 401."""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401