"""
api/app/core/security.py
Primitivas de seguridad: hash de contraseñas y JWT.
No depende de la DB ni de los modelos.
"""

from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

from api.app.core.config import settings


# bcrypt fijado a 4.0.1 en requirements para evitar incompatibilidad con passlib.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Retorna el hash bcrypt de una contraseña en texto plano.
    
    bcrypt tiene un límite de 72 bytes, se trunca la contraseña si es necesario.
    """
    # bcrypt limita contraseñas a 72 bytes, truncamos para evitar error
    if len(plain_password) > 72:
        plain_password = plain_password[:72]
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña en texto plano contra su hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Crea un JWT firmado (HS256).
    `data` debe incluir al menos: sub, tenant_id, role.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """
    Decodifica y valida un JWT.
    Retorna el payload o None si el token es inválido/expirado.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        return None