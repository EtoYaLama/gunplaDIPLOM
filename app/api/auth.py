from datetime import timedelta
from fastapi import APIRouter, Depends, Response, Request, status
from sqlalchemy.orm import Session

from app.services.auth_service import AuthService, JWTManager
from app.utils.exceptions import AuthException
from app.utils.dependencies import get_current_active_user
from app.schemas.user import UserCreateSchemas, UserResponseSchemas, TokenSchemas, UserLoginSchemas, UserProfileSchemas, UserUpdateSchemas
from app.database import get_db
from app.models import User
from app.config import settings



router = APIRouter(tags=["Авторизация"])



@router.post("/register", response_model=UserResponseSchemas, status_code=status.HTTP_201_CREATED)
async def register_user(
        user: UserCreateSchemas,
        db: Session = Depends(get_db),
):
    """ Регистрация нового пользователя Проверяет уникальность email и username, создает пользователя в БД """
    # Проверяем, что пользователь с таким email не существует
    if AuthService.get_user_by_email(db, email=user.email):
        raise AuthException.USER_ALREADY_EXISTS

    # Проверяем, что username не занят
    if AuthService.get_user_by_username(db, username=user.username):
        raise AuthException.USERNAME_TAKEN

    # Создаем пользователя в базе данных
    db_user = AuthService.create_user(
        db=db,
        email=user.email,
        username=user.username,
        password=user.password,
        full_name=user.full_name
    )

    return db_user


@router.post("/login", response_model=TokenSchemas)
async def login_user(
        user_credentials: UserLoginSchemas,
        response: Response,
        db: Session = Depends(get_db)
):
    """ Авторизация пользователя Проверяет учетные данные, создает JWT токен и сохраняет его в cookies """
    # Аутентификация пользователя по email и паролю
    user = AuthService.authenticate_user(db, user_credentials.email, user_credentials.password)

    # Проверяем, найден ли пользователь с правильными учетными данными
    if not user:
        raise AuthException.INVALID_CREDENTIALS

    # Проверяем, активен ли пользователь
    if not user.is_active:
        raise AuthException.INACTIVE_USER

    # Создаем JWT токен с указанным временем жизни
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = JWTManager.create_access_token(
        user_id=user.id,
        email=user.email,
        expires_delta=access_token_expires
    )

    # Сохраняем токен в HTTP-only cookie для безопасности
    JWTManager.set_token_cookie(response, access_token, access_token_expires)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout_user(response: Response):
    """ Выход пользователя из системы Удаляет токен авторизации из cookies """
    JWTManager.remove_token_cookie(response)
    return {"message": "Logged out successfully"}


@router.get('/current_user_profile', response_model=UserProfileSchemas)
async def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    """ Получение профиля текущего авторизованного пользователя Требует действующий токен авторизации """
    return current_user



@router.put('/update_profile', response_model=UserProfileSchemas)
async def update_current_user_profile(
        user_update: UserUpdateSchemas,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ):
    """ Обновление профиля текущего пользователя """
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.phone is not None:
        current_user.phone = user_update.phone
    if user_update.address is not None:
        current_user.address = user_update.address

    db.commit()
    db.refresh(current_user)
    return current_user



@router.get('/token-info')
async def get_token_info(request: Request):
    """ Получение информации о пользователе из токена в cookie Возвращает user_id, email и статус авторизации """
    # Сначала получаем токен из cookie
    token = JWTManager.get_token_from_cookie(request)
    if not token:
        raise AuthException.INVALID_TOKEN

    # Проверяем токен и получаем данные пользователя
    user_data = JWTManager.verify_token(token)
    if not user_data:
        raise AuthException.INVALID_TOKEN

    return {
        "user_id": str(user_data['user_id']),  # Конвертируем UUID в строку для JSON
        "email": user_data['email'],
        "authenticated": True
    }


@router.post('/verify-token')
async def verify_token_from_header(token: str):
    """ Проверка действительности токена, переданного в параметре Возвращает данные пользователя, если токен валиден """
    # Проверяем валидность токена
    user_data = JWTManager.verify_token(token)
    if not user_data:
        raise AuthException.INVALID_TOKEN

    return {"user_data": user_data}


@router.get("/check_connection")
def check_database_connection(db: Session = Depends(get_db)):
    """ Проверка подключения к базе данных
    Выполняет простой SQL запрос для тестирования соединения """
    # Простой запрос для проверки соединения с БД
    db.execute("SELECT 1")
    return {"message": "Соединение с базой данных установлено успешно!"}