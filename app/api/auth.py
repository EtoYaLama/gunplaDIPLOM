from datetime import timedelta
from fastapi import APIRouter, Depends, Response, Request, status, HTTPException
from sqlalchemy.orm import Session
import logging

from app.services.auth_service import AuthService, JWTManager
from app.utils.exceptions import AuthException
from app.utils.dependencies import get_current_active_user
from app.schemas.user import UserCreateSchemas, UserResponseSchemas, TokenSchemas, UserLoginSchemas, UserProfileSchemas
from app.database import get_db
from app.models import User
from app.config import settings, config

# Настройка логирования для отладки
logging.basicConfig(handlers=[logging.FileHandler('app.log', encoding='utf-8')],
                    level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger(__name__)

root_logger = logging.getLogger()
file_handler = logging.FileHandler('app.log')
file_handler.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)

router = APIRouter(tags=["Авторизация"])


@router.post("/register", response_model=UserResponseSchemas, status_code=status.HTTP_201_CREATED)
async def register_user(
        user: UserCreateSchemas,
        db: Session = Depends(get_db),
):
    """ Регистрация пользователя """
    try:
        logger.info(f"Регистрация пользователя: {user.email}")

        # Проверяем, что пользователь с таким email не существует
        if AuthService.get_user_by_email(db, email=user.email):
            logger.warning(f"Пользователь с email {user.email} уже существует")
            raise AuthException.USER_ALREADY_EXISTS

        # Проверяем, что username не занят
        if AuthService.get_user_by_username(db, username=user.username):
            logger.warning(f"Username {user.username} уже занят")
            raise AuthException.USERNAME_TAKEN

        # Создаем пользователя
        db_user = AuthService.create_user(
            db=db,
            email=user.email,
            username=user.username,
            password=user.password,
            full_name=user.full_name
        )

        logger.info(f"Пользователь {user.email} успешно зарегистрирован")
        return db_user

    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя: {str(e)}")
        # Важно: не перехватываем исключения AuthException, пусть они проходят дальше
        if isinstance(e, (AuthException.USER_ALREADY_EXISTS, AuthException.USERNAME_TAKEN)):
            raise
        # Для других исключений создаем общую ошибку
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при регистрации пользователя"
        )


@router.post("/login", response_model=TokenSchemas)
async def login_user(
        user_credentials: UserLoginSchemas,
        response: Response,
        db: Session = Depends(get_db)
):
    """ Авторизация пользователя с сохранением токена в cookies """

    try:
        logger.info(f"Попытка входа пользователя: {user_credentials.email}")

        # Аутентификация пользователя
        user = AuthService.authenticate_user(db, user_credentials.email, user_credentials.password)

        # Проверка пользователя
        if not user:
            logger.warning(f"Неверные учетные данные для {user_credentials.email}")
            raise AuthException.INVALID_CREDENTIALS

        # Проверяем, активен ли пользователь
        if not user.is_active:
            logger.warning(f"Пользователь {user_credentials.email} неактивен")
            raise AuthException.INACTIVE_USER

        logger.info(f"Пользователь {user.email} успешно аутентифицирован")

        # Создаем токен с временем истечения
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = JWTManager.create_access_token(
            user_id=user.id,
            email=user.email,
            expires_delta=access_token_expires
        )

        logger.info(f"Токен создан для пользователя {user.email}")

        # Сохраняем токен в cookie используя новый метод
        JWTManager.set_token_cookie(response, access_token, access_token_expires)

        logger.info(f"Токен сохранен в cookie для пользователя {user.email}")

        # ВАЖНО: явно коммитим транзакцию, если она не закоммичена
        try:
            if db.in_transaction():
                db.commit()
                logger.info("Транзакция успешно закоммичена")
        except Exception as commit_error:
            logger.error(f"Ошибка при коммите: {str(commit_error)}")
            db.rollback()
            raise

        return {"access_token": access_token, "token_type": "bearer"}

    except Exception as e:
        logger.error(f"Ошибка при входе пользователя {user_credentials.email}: {str(e)}")

        # Откатываем транзакцию при ошибке
        try:
            if db.in_transaction():
                db.rollback()
                logger.info("Транзакция откачена из-за ошибки")
        except Exception as rollback_error:
            logger.error(f"Ошибка при откате транзакции: {str(rollback_error)}")
            raise

        # Для других исключений создаем общую ошибку
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при входе в систему"
        )


@router.post("/logout")
async def logout_user(response: Response):
    """ Выход пользователя - удаление токена из cookies """
    try:
        JWTManager.remove_token_cookie(response)
        logger.info("Пользователь успешно вышел из системы")
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Ошибка при выходе: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при выходе из системы"
        )


@router.get('/current_user_profile', response_model=UserProfileSchemas)
async def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    """ Получение профиля текущего пользователя """
    try:
        logger.info(f"Получение профиля пользователя: {current_user.email}")
        return current_user
    except Exception as e:
        logger.error(f"Ошибка при получении профиля: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении профиля пользователя"
        )


@router.get('/token-info')
async def get_token_info(request: Request):
    """ Получение информации о пользователе из токена в cookie """
    try:
        logger.info("Получение информации о токене из cookie")

        user_id = JWTManager.get_user_id_from_cookie(request)
        email = JWTManager.get_email_from_cookie(request)

        if not user_id or not email:
            logger.warning("Токен в cookie недействителен или отсутствует")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing authentication token"
            )

        logger.info(f"Информация о токене получена для пользователя: {email}")
        return {
            "user_id": user_id,
            "email": email,
            "authenticated": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении информации о токене: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении информации о токене"
        )


@router.post('/verify-token')
async def verify_token_from_header(token: str):
    """ Проверка действительности токена переданного в параметре """
    try:
        logger.info("Проверка токена из параметра")

        user_data = JWTManager.verify_token(token)
        if not user_data:
            logger.warning("Недействительный токен")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        logger.info(f"Токен действителен для пользователя: {user_data.get('email')}")
        return {"user_data": user_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при проверке токена: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при проверке токена"
        )


# Проверка подключения к Базе данных
@router.get("/check_connection")
def read_root(db: Session = Depends(get_db)):
    try:
        # Простой запрос для проверки соединения
        db.execute("SELECT 1")
        return {"message": "Соединение с базой данных установлено успешно!"}
    except Exception as e:
        logger.error(f"Ошибка соединения с БД: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка соединения с базой данных"
        )