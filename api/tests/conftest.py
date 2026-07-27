"""
api/tests/conftest.py
Fixtures de pytest: DB de test aislada, client de FastAPI, tokens de auth.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.app.core.db import Base, get_db
from api.app.core.security import hash_password
from api.app.crud.tenant import get_tenant_by_slug
from api.app.crud.user import create_user
from api.app.main import app
from api.app.models.user import ROLE_INSTRUCTOR

# DB de test en memoria (SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Crea una DB limpia para cada test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Client de FastAPI con la DB de test."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_token(client):
    """Registra un tenant+admin y retorna el JWT."""
    client.post("/api/v1/auth/register", json={
        "tenant_name": "Colegio de Test",
        "tenant_slug": "colegio-test",
        "email": "test@test.com",
        "password": "TestPass123",
        "full_name": "Test User",
    })
    # Login sin slug: el backend deduce el tenant del email.
    resp = client.post("/api/v1/auth/login", data={
        "username": "test@test.com",
        "password": "TestPass123",
    })
    return resp.json()["access_token"]


@pytest.fixture(scope="function")
def auth_token_2(client):
    """Registra un segundo tenant+admin y retorna su JWT (para aislamiento)."""
    client.post("/api/v1/auth/register", json={
        "tenant_name": "Colegio de Test 2",
        "tenant_slug": "colegio-test-2",
        "email": "test2@test.com",
        "password": "TestPass456",
        "full_name": "Test User 2",
    })
    resp = client.post("/api/v1/auth/login", data={
        "username": "test2@test.com",
        "password": "TestPass456",
    })
    return resp.json()["access_token"]


@pytest.fixture(scope="function")
def auth_token_instructor(client, db_session):
    """
    Crea un tenant con admin y, dentro del mismo, un usuario instructor.
    Retorna el JWT del instructor (rol != admin).
    """
    client.post("/api/v1/auth/register", json={
        "tenant_name": "Colegio de Instructores",
        "tenant_slug": "colegio-inst",
        "email": "admini@test.com",
        "password": "AdminPass123",
        "full_name": "Admin Inst",
    })
    tenant = get_tenant_by_slug(db_session, "colegio-inst")
    create_user(
        db_session,
        tenant_id=tenant.id,
        email="instr@test.com",
        hashed_password=hash_password("InstrPass123"),
        full_name="Instructor Test",
        role=ROLE_INSTRUCTOR,
    )
    db_session.commit()
    resp = client.post("/api/v1/auth/login", data={
        "username": "instr@test.com",
        "password": "InstrPass123",
    })
    return resp.json()["access_token"]