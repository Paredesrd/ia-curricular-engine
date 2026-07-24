FROM python:3.13-slim

WORKDIR /app

# Dependencias del sistema para psycopg2 (PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY api/requirements.txt ./api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

# Copiar el proyecto completo (núcleo + API + alembic)
COPY . .

# Exponer puerto de la API
EXPOSE 8000

# Comando por defecto (docker-compose lo sobreescribe para correr migraciones primero)
CMD ["uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]