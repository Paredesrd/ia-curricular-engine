"""
test_alembic.py
Verifica que Alembic se configuró correctamente y que la migración inicial se aplicó.

Ejecutar: python test_alembic.py
"""

import sqlite3
import sys
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "ia_curricular_dev.db"


def main() -> None:
    print("=" * 60)
    print("TEST DE ALEMBIC (MIGRACIONES)")
    print("=" * 60)

    if not DB_PATH.exists():
        print(f"✗ La base de datos no existe: {DB_PATH}")
        print("  Ejecuta: alembic upgrade head")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Verificar que alembic_version existe y tiene una fila
    print("[1/3] Verificando tabla alembic_version ...")
    try:
        cursor.execute("SELECT version_num FROM alembic_version")
        rows = cursor.fetchall()
        if len(rows) == 0:
            print("      ✗ alembic_version está vacía (migración no aplicada)")
            sys.exit(1)
        version_hash = rows[0][0]
        print(f"      ✓ alembic_version existe | hash={version_hash}")
    except sqlite3.OperationalError as e:
        print(f"      ✗ alembic_version no existe: {e}")
        print("      Ejecuta: alembic upgrade head")
        sys.exit(1)

    # 2. Verificar que las tablas del modelo existen
    print("[2/3] Verificando tablas del modelo (tenants, users, courses) ...")
    expected_tables = {"tenants", "users", "courses"}
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row[0] for row in cursor.fetchall()}
    missing = expected_tables - existing_tables
    if missing:
        print(f"      ✗ Faltan tablas: {missing}")
        sys.exit(1)
    print(f"      ✓ Todas las tablas existen: {expected_tables}")

    # 3. Verificar que las tablas tienen columnas (schema no vacío)
    print("[3/3] Verificando schema de tablas ...")
    for table in expected_tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        if len(columns) == 0:
            print(f"      ✗ Tabla {table} no tiene columnas")
            sys.exit(1)
        print(f"      ✓ {table}: {len(columns)} columnas")

    conn.close()

    print("=" * 60)
    print("ALEMBIC OK")
    print("=" * 60)


if __name__ == "__main__":
    main()