"""
api/app/core/path_setup.py
Puente de imports entre la capa SaaS (api/) y el núcleo de IA (core/).

El núcleo usa imports top-level (from domain..., from agents..., from config...)
que solo resuelven cuando core/ está en sys.path. Esta función registra core/
una sola vez, de forma idempotente, sin tocar el núcleo ni romper sus tests.
"""

import sys
from pathlib import Path


def ensure_core_on_path() -> None:
    """
    Añade la carpeta core/ (núcleo de IA) al sys.path si no está ya.
    Ruta: este archivo está en api/app/core/, la raíz del proyecto es parents[3].
    """
    core_dir = (Path(__file__).resolve().parents[3] / "core")
    core_dir_str = str(core_dir)
    if core_dir_str not in sys.path:
        sys.path.insert(0, core_dir_str)