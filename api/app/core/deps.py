"""
api/app/core/deps.py
Dependencias de FastAPI: extracción y validación del usuario autenticado.
"""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from api.app.core.db import get_db
from api.app.core.security import decode_access_token
from api.app.crud.user import get_user_by_id
from api.app.models.user import User


# tokenUrl debe coincidir con la ruta final del login (prefijo incluido).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudieron validar las credenciales.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Decodifica el JWT y retorna el usuario autenticado.
    Lanza 401 ante cualquier inconsistencia del token.
    """
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        raise credentials_exception

    try:
        user_id = UUID(user_id_raw)
    except ValueError:
        raise credentials_exception

    user = get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Garantiza que el usuario autenticado esté activo."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta inactiva.",
        )
    return current_user