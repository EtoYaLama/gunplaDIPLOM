from typing import Optional
from fastapi import Depends, Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.services.auth_service import JWTManager, AuthService
from app.models import User
from app.database import get_db

security = HTTPBearer(auto_error=False)


def get_token_from_request(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Optional[str]:
    """
    Получает токен из заголовка Authorization или из cookie.
    Приоритет: заголовок Authorization -> cookie
    """
    # Сначала пытаемся получить токен из заголовка
    if credentials:
        return credentials.credentials

    # Если в заголовке нет токена, ищем в cookie
    return JWTManager.get_token_from_cookie(request)


def get_current_user(
        token: Optional[str] = Depends(get_token_from_request),
        db: Session = Depends(get_db)
) -> User:
    """
    Получает текущего пользователя на основе JWT токена.
    Токен может быть передан в заголовке Authorization или в cookie.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Проверяем токен
    user_data = JWTManager.verify_token(token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Получаем пользователя из базы данных
    user = AuthService.get_user_by_id(db, user_data['user_id'])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Получает текущего активного пользователя.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def get_current_user_from_cookie_only(
        request: Request,
        db: Session = Depends(get_db)
) -> User:
    """
    Получает текущего пользователя ТОЛЬКО из cookie (игнорирует заголовки).
    Полезно для веб-интерфейса.
    """
    token = JWTManager.get_token_from_cookie(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication cookie found"
        )

    user_data = JWTManager.verify_token(token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication cookie"
        )

    user = AuthService.get_user_by_id(db, user_data['user_id'])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return user