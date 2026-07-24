"""
api/tests/test_tenants.py
Tests del router de tenants: consulta del colegio y edición de reglas
de acreditación (incluye control de rol admin/instructor).
"""


VALID_RULES = {
    "min_total_hours": 30,
    "max_total_hours": 50,
    "min_module_hours": 5,
    "max_module_hours": 12,
    "required_bloom_levels": ["remember", "apply", "create"],
    "min_lessons_per_module": 3,
    "max_lessons_per_module": 6,
    "custom_restrictions": "Regla custom de test",
}


def test_get_my_tenant(client, auth_token):
    """/tenants/me con token retorna 200 con slug y reglas por defecto."""
    resp = client.get(
        "/api/v1/tenants/me",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "colegio-test"
    assert "min_total_hours" in data["accreditation_rules"]


def test_update_rules_as_admin(client, auth_token):
    """Admin actualiza reglas y el cambio persiste en /tenants/me."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    resp = client.put("/api/v1/tenants/me/rules", json=VALID_RULES, headers=headers)
    assert resp.status_code == 200

    resp2 = client.get("/api/v1/tenants/me", headers=headers)
    rules = resp2.json()["accreditation_rules"]
    assert rules["min_total_hours"] == 30
    assert rules["max_total_hours"] == 50
    assert "create" in rules["required_bloom_levels"]
    assert rules["custom_restrictions"] == "Regla custom de test"


def test_update_rules_invalid_range(client, auth_token):
    """Rango inconsistente (max < min) retorna 422."""
    bad = dict(VALID_RULES)
    bad["min_total_hours"] = 50
    bad["max_total_hours"] = 20
    resp = client.put(
        "/api/v1/tenants/me/rules",
        json=bad,
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 422


def test_update_rules_as_instructor_forbidden(client, auth_token_instructor):
    """Instructor intentando editar reglas retorna 403."""
    resp = client.put(
        "/api/v1/tenants/me/rules",
        json=VALID_RULES,
        headers={"Authorization": f"Bearer {auth_token_instructor}"},
    )
    assert resp.status_code == 403


def test_get_my_tenant_without_token(client):
    """/tenants/me sin token retorna 401."""
    resp = client.get("/api/v1/tenants/me")
    assert resp.status_code == 401