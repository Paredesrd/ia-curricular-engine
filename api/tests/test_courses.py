"""
api/tests/test_courses.py
Tests del módulo de cursos: creación, listado, consulta, aislamiento
multi-tenant y ELIMINACIÓN (opción A).
"""
import uuid


def test_create_course_success(client, auth_token):
    """Crear curso exitoso retorna 201 con status completed y lecciones."""
    resp = client.post(
        "/api/v1/courses",
        json={
            "topic": "Diseño de Estructuras de Acero",
            "target_audience": "Ingenieros civiles",
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "completed"
    assert len(data["course_content"]["lessons_content"]) > 0


def test_list_courses(client, auth_token):
    """Listar cursos del tenant retorna 200 con lista no vacía."""
    client.post(
        "/api/v1/courses",
        json={"topic": "Diseño de Estructuras de Acero"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    resp = client.get(
        "/api/v1/courses",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_course_by_id(client, auth_token):
    """Consultar curso por ID del mismo tenant retorna 200."""
    resp_create = client.post(
        "/api/v1/courses",
        json={"topic": "Diseño de Estructuras de Acero"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    course_id = resp_create.json()["id"]
    resp = client.get(
        f"/api/v1/courses/{course_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["topic"] == "Diseño de Estructuras de Acero"


def test_get_course_from_other_tenant(client, auth_token, auth_token_2):
    """Consultar curso de otro tenant retorna 404 (aislamiento multi-tenant)."""
    resp_create = client.post(
        "/api/v1/courses",
        json={"topic": "Diseño de Estructuras de Acero"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    course_id = resp_create.json()["id"]
    resp = client.get(
        f"/api/v1/courses/{course_id}",
        headers={"Authorization": f"Bearer {auth_token_2}"},
    )
    assert resp.status_code == 404


def test_create_course_without_token(client):
    """Crear curso sin token retorna 401."""
    resp = client.post(
        "/api/v1/courses",
        json={"topic": "Diseño de Estructuras de Acero"},
    )
    assert resp.status_code == 401


def test_get_nonexistent_course(client, auth_token):
    """Consultar curso inexistente retorna 404."""
    fake_id = str(uuid.uuid4())
    resp = client.get(
        f"/api/v1/courses/{fake_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 404


# ============================================================
# ELIMINACIÓN (opción A)
# ============================================================
def test_delete_course_success(client, auth_token):
    """Eliminar curso propio retorna 204 y el curso deja de existir (404)."""
    resp_create = client.post(
        "/api/v1/courses",
        json={"topic": "Diseño de Estructuras de Acero"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp_create.status_code == 201
    course_id = resp_create.json()["id"]

    resp_del = client.delete(
        f"/api/v1/courses/{course_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp_del.status_code == 204

    # Tras borrar, consultar el mismo id debe dar 404.
    resp_get = client.get(
        f"/api/v1/courses/{course_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp_get.status_code == 404


def test_delete_course_from_other_tenant(client, auth_token, auth_token_2):
    """Eliminar curso de otro tenant retorna 404 (aislamiento multi-tenant)."""
    resp_create = client.post(
        "/api/v1/courses",
        json={"topic": "Diseño de Estructuras de Acero"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    course_id = resp_create.json()["id"]

    resp_del = client.delete(
        f"/api/v1/courses/{course_id}",
        headers={"Authorization": f"Bearer {auth_token_2}"},
    )
    assert resp_del.status_code == 404

    # El curso del tenant 1 sigue existiendo (el 2 no lo tocó).
    resp_get = client.get(
        f"/api/v1/courses/{course_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp_get.status_code == 200


def test_delete_course_without_token(client, auth_token):
    """Eliminar curso sin token retorna 401."""
    resp_create = client.post(
        "/api/v1/courses",
        json={"topic": "Diseño de Estructuras de Acero"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    course_id = resp_create.json()["id"]

    resp_del = client.delete(f"/api/v1/courses/{course_id}")
    assert resp_del.status_code == 401


def test_delete_nonexistent_course(client, auth_token):
    """Eliminar curso inexistente retorna 404."""
    fake_id = str(uuid.uuid4())
    resp_del = client.delete(
        f"/api/v1/courses/{fake_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp_del.status_code == 404