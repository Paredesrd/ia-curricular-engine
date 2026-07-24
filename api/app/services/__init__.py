"""
api/app/services/__init__.py
Lógica de negocio que orquesta el núcleo de IA.
Al importar este subpaquete se registra core/ en sys.path,
de modo que cualquier servicio puede importar los agentes del núcleo.
"""

from api.app.core.path_setup import ensure_core_on_path

ensure_core_on_path()