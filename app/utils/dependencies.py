from typing import Optional
from fastapi import Depends, Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.services.auth_service import JWTManager
from app.utils.exceptions import AuthException
from app.models import User
from app.database import get_db

security = HTTPBearer(auto_error=False)


def get_token_from_request(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Optional[str]:
    """ Извлекает JWT токен из заголовка Authorization или из cookie Приоритет: заголовок Authorization -> cookie """
    # Сначала пытаемся получить токен из заголовка Authorization
    if credentials:
        return credentials.credentials

    # Если в заголовке нет токена, ищем в cookie
    return JWTManager.get_token_from_cookie(request)


def get_current_user(
        token: Optional[str] = Depends(get_token_from_request),
        db: Session = Depends(get_db)
) -> User:
    """ Получает текущего пользователя на основе JWT токена Токен может быть передан в заголовке Authorization или в cookie """
    # Проверяем наличие токена
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Не удалось подтвердить учетные данные',
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Проверяем валидность токена и извлекаем данные
    user_data = JWTManager.verify_token(token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Не удалось подтвердить учетные данные',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    # Получаем пользователя из базы данных по ID
    user = db.query(User).filter(User.id == user_data['user_id']).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Пользователь не найден'
        )

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """ Получает текущего активного пользователя Проверяет, что пользователь не заблокирован """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Неактивный пользователь'
        )
    return current_user



async def get_current_admin_user(
        current_user: User = Depends(get_current_active_user)
) -> User:
    """ Зависимость для получения пользователя с правами администратора """
    if not current_user.is_admin == True:
        raise AuthException.PERMISSION_DENIED
    return current_user



def get_current_user_from_cookie_only(
        request: Request,
        db: Session = Depends(get_db)
) -> User:
    """ Получает текущего пользователя ТОЛЬКО из cookie (игнорирует заголовки) Используется для веб-интерфейса, где токен передается только через cookie """
    # Извлекаем токен только из cookie
    token = JWTManager.get_token_from_cookie(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Не найден файл cookie для аутентификации'
        )

    # Проверяем валидность токена
    user_data = JWTManager.verify_token(token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Недействительный файл cookie для аутентификации'
        )

    # Получаем пользователя из БД
    user = db.query(User).filter(User.id == user_data['user_id']).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Пользователь не найден'
        )

    # Проверяем, что пользователь активен
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Неактивный пользователь'
        )

    return user