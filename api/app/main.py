"""
api/app/main.py
Aplicación FastAPI - Punto de entrada de la API SaaS.
Ejecutar (desde la raíz del proyecto):
    uvicorn api.app.main:app --reload --port 8000
En producción, antes de arrancar el servidor:
    alembic upgrade head

NOTA DE ARRANQUE (feature-toggle del elicitor):
El router de intake (/api/v1/intake) se carga de forma DEFENSIVA. Si el módulo
aún no existe o le falta alguna dependencia del núcleo (core/llm, core/policy,
core/agents/elicitor, core/domain/elicitor_models, core/config/llm_settings),
el servidor ARRANCA IGUAL sin ese router y lo reporta en /health/intake como
available=false. Así un módulo opcional nunca tumba el resto de la API.
Un SyntaxError real en intake.py NO se silencia (debe verse y corregirse).
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.app.core.config import settings
from api.app.core.db import get_db, init_db, check_db_connection
from api.app.api.auth import router as auth_router
from api.app.api.courses import router as courses_router
from api.app.api.tenants import router as tenants_router

# ----------------------------------------------------------------------
# Carga defensiva del router de intake (agente Elicitor)
# ----------------------------------------------------------------------
INTAKE_AVAILABLE = False
try:
    from api.app.api.intake import router as intake_router
    INTAKE_AVAILABLE = True
except (ModuleNotFoundError, ImportError) as exc:
    logging.warning(
        "Router de intake NO cargado (%s). "
        "El endpoint /api/v1/intake quedará fuera (404) hasta que existan "
        "api/app/api/intake.py y sus dependencias del núcleo. "
        "El resto de la API arranca con normalidad.",
        exc,
    )


# ============================================================
# LIFESPAN (startup/shutdown)
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Iniciando API SaaS...")
    if settings.ENVIRONMENT == "development":
        init_db()
    yield
    logging.info("Cerrando API SaaS...")


# ============================================================
# APP
# ============================================================
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API SaaS para el Motor de IA Curricular",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# MANEJO GLOBAL DE ERRORES
# ============================================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error("Error no controlado: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal Server Error", "detail": str(exc)},
    )


# ============================================================
# ROUTERS
# ============================================================
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(courses_router, prefix="/api/v1/courses", tags=["Courses"])
app.include_router(tenants_router, prefix="/api/v1/tenants", tags=["Tenants"])
if INTAKE_AVAILABLE:
    app.include_router(intake_router, prefix="/api/v1/intake", tags=["Intake"])


# ============================================================
# ROOT
# ============================================================
@app.get("/", tags=["Root"])
async def root():
    endpoints = {
        "health": "/health",
        "health_db": "/health/db",
        "health_intake": "/health/intake",
        "auth_register": "/api/v1/auth/register",
        "auth_login": "/api/v1/auth/login",
        "auth_me": "/api/v1/auth/me",
        "tenants_me": "/api/v1/tenants/me",
        "tenants_rules": "/api/v1/tenants/me/rules",
        "courses_create": "/api/v1/courses",
        "courses_list": "/api/v1/courses",
        "courses_get": "/api/v1/courses/{course_id}",
        "docs": "/docs",
    }
    if INTAKE_AVAILABLE:
        endpoints["intake_turn"] = "/api/v1/intake"
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "running",
        "intake_available": INTAKE_AVAILABLE,
        "endpoints": endpoints,
    }


# ============================================================
# HEALTH
# ============================================================
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/db", tags=["Health"])
async def health_db(db: Session = Depends(get_db)):
    try:
        info = check_db_connection()
        return {"status": "healthy", "database": info}
    except Exception as exc:
        logging.error("Health check de DB falló: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": {"connected": False, "error": str(exc)},
            },
        )


@app.get("/health/intake", tags=["Health"])
async def health_intake():
    """
    Reporta si el router del elicitor quedó cargado en este arranque.
    available=false → faltan archivos del elicitor; el resto de la API está bien.
    """
    if INTAKE_AVAILABLE:
        return {
            "available": True,
            "route": "/api/v1/intake",
            "note": "Elicitor cargado. El modo (rules/llm) lo indica cada respuesta de /api/v1/intake en el campo 'mode'.",
        }
    return {
        "available": False,
        "route": "/api/v1/intake",
        "note": (
            "Elicitor NO cargado. Crea api/app/api/intake.py y los módulos del "
            "núcleo (core/agents/elicitor.py, core/llm/*, core/policy/*, "
            "core/domain/elicitor_models.py, core/config/llm_settings.py) y "
            "reinicia uvicorn. El resto de la API funciona igual."
        ),
    }


# ============================================================
# EJECUCIÓN DIRECTA (desarrollo)
# ============================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )