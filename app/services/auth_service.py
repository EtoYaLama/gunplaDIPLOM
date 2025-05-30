from fastapi import Response, Request
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import EmailStr
import jwt
from email_validator import validate_email
import uuid

from app.models import User
from app.config import settings



''' Контекст для хеширования паролей '''
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")



class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """ Проверка соответствия введенного пароля c хешированным """
        return pwd_context.verify(plain_password, hashed_password)



    @staticmethod
    def get_password_hash(password: str) -> str:
        """ Создание хеша пароля для безопасного хранения """
        return pwd_context.hash(password)



    @staticmethod
    def create_user(
        db: Session,
        email: EmailStr,
        username: str,
        password: str,
        full_name: str = None
    ) -> User:
        """ Создание нового пользователя в базе данных Хеширует пароль и сохраняет пользователя """
        hashed_password = AuthService.get_password_hash(password)

        db_user = User(
            email=email,
            username=username,
            password_hash=hashed_password,
            full_name=full_name,
            is_admin=False,
            is_active=True
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user



    @staticmethod
    def get_user_by_email(db: Session, email: EmailStr) -> Optional[User]:
        """ Поиск пользователя по email адресу """
        stmt = select(User).where(email == User.email)
        result = db.execute(stmt).scalar_one_or_none()
        return result



    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """ Поиск пользователя по имени пользователя """
        stmt = select(User).where(username == User.username)
        result = db.execute(stmt).scalar_one_or_none()
        return result



    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """ Аутентификация пользователя по email и паролю Возвращает пользователя, если учетные данные верны """
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not AuthService.verify_password(password, user.password_hash):
            return None
        return user



class JWTManager:
    @staticmethod
    def create_access_token(
        user_id: uuid.UUID,
        email: EmailStr,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """ Создание JWT токена для авторизации Включает user_id, email и время истечения """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            'sub': str(user_id),  # Конвертируем UUID в строку
            'email': email,
            'exp': expire,
            'iat': datetime.now(timezone.utc)
        }

        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)



    @staticmethod
    def set_token_cookie(
        response: Response,
        token: str,
        expires_delta: Optional[timedelta] = None
    ) -> None:
        """ Установка JWT токена в HTTP-only cookie. Обеспечивает безопасное хранение токена в браузере """
        if expires_delta:
            max_age = int(expires_delta.total_seconds())
        else:
            max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        response.set_cookie(
            key="access_token",
            value=f"Bearer {token}",
            max_age=max_age,
            httponly=True,  # Защита от XSS
            secure=True,    # Только HTTPS
            samesite="lax"  # Защита от CSRF
        )



    @staticmethod
    def get_token_from_cookie(request: Request) -> Optional[str]:
        """ Извлечение JWT токена из cookie. Убирает префикс 'Bearer' если он есть """
        cookie_value = request.cookies.get("access_token")
        if cookie_value and cookie_value.startswith("Bearer "):
            return cookie_value[7:]
        return None



    @staticmethod
    def remove_token_cookie(response: Response) -> None:
        """ Удаление JWT токена из cookie при выходе """
        response.delete_cookie(
            key="access_token",
            httponly=True,
            secure=True,
            samesite="lax"
        )



    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """ Проверка валидности JWT токена Возвращает данные пользователя, если токен действителен """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )

            user_id_str = payload.get('sub')
            email = payload.get('email')

            if not user_id_str or not email:
                return None

            # Конвертируем строку обратно в UUID
            try:
                user_id = uuid.UUID(user_id_str)
            except (ValueError, TypeError):
                return None

            return {
                'user_id': user_id,
                'email': email
            }

        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, ValueError):
            return None



    @staticmethod
    def get_user_id_from_token(token: str) -> Optional[uuid.UUID]:
        """ Извлечение user_id из JWT токена """
        user_data = JWTManager.verify_token(token)
        return user_data['user_id'] if user_data else None



    @staticmethod
    def get_email_from_token(token: str) -> Optional[str]:
        """ Извлечение email из JWT токена """
        user_data = JWTManager.verify_token(token)
        if user_data:
            try:
                _, email = validate_email(user_data['email'])
                return email
            except Exception:
                return None
        return None



    @staticmethod
    def get_user_id_from_cookie(request: Request) -> Optional[uuid.UUID]:
        """ Извлечение user_id из cookie с токеном """
        token = JWTManager.get_token_from_cookie(request)
        if token:
            return JWTManager.get_user_id_from_token(token)
        return None



    @staticmethod
    def get_email_from_cookie(request: Request) -> Optional[str]:
        """ Извлечение email из cookie с токеном """
        token = JWTManager.get_token_from_cookie(request)
        if token:
            return JWTManager.get_email_from_token(token)
        return None