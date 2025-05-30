from fastapi import HTTPException, status

class AuthException:
    INVALID_CREDENTIALS = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Неверный email или пароль",
        headers={"WWW-Authenticate": "Bearer"},
    )

    INVALID_TOKEN = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Недействительный токен авторизации",
        headers={"WWW-Authenticate": "Bearer"},
    )

    INACTIVE_USER = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Неактивный пользователь"
    )

    USER_ALREADY_EXISTS = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Пользователь с таким email уже существует"
    )

    USERNAME_TAKEN = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Имя пользователя уже занято"
    )

    PERMISSION_DENIED = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Недостаточно прав доступа"
    )