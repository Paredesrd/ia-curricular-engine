"""
api/app/main.py
Aplicación FastAPI - Punto de entrada de la API SaaS.

Ejecutar (desde la raíz del proyecto):
  uvicorn api.app.main:app --reload --port 8000

En producción, antes de arrancar el servidor:
  alembic upgrade head
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


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "running",
        "endpoints": {
            "health": "/health",
            "health_db": "/health/db",
            "auth_register": "/api/v1/auth/register",
            "auth_login": "/api/v1/auth/login",
            "auth_me": "/api/v1/auth/me",
            "tenants_me": "/api/v1/tenants/me",
            "tenants_rules": "/api/v1/tenants/me/rules",
            "courses_create": "/api/v1/courses",
            "courses_list": "/api/v1/courses",
            "courses_get": "/api/v1/courses/{course_id}",
            "docs": "/docs",
        },
    }


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
            content={"status": "unhealthy", "database": {"connected": False, "error": str(exc)}},
        )


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