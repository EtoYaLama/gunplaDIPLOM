import re
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
import uuid



''' Модель пользователя (Базовая) '''
class UserBaseSchemas(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None



''' Модель создания пользователя '''
class UserCreateSchemas(UserBaseSchemas):
    password: str

    ''' Валидация password '''
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        errors = []

        if len(v) < 8:
            errors.append('минимум 8 символов')

        if not re.search(r'[A-Z]', v):
            errors.append('хотя бы одну заглавную букву')

        if not re.search(r'[a-z]', v):
            errors.append('хотя бы одну строчную букву')

        if not re.search(r'\d', v):
            errors.append('хотя бы одну цифру')

        if errors:
            raise ValueError(f'Пароль должен содержать {", ".join(errors)}')

        return v

    ''' Валидация username '''
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 20:
            raise ValueError('Имя пользователя должно быть от 3 до 20 символов')

        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Недопустимые символы в имени пользователя')

        return v



''' Метод для авторизации пользователя в системе '''
class UserLoginSchemas(BaseModel):
    email: EmailStr
    password: str



''' Метод для ответа '''
class UserResponseSchemas(UserBaseSchemas):
    id: uuid.UUID
    phone: Optional[str] | None
    address: Optional[str] | None
    is_admin: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True



''' Модель профиля пользователя '''
class UserProfileSchemas(UserResponseSchemas):
    pass


class UserUpdateSchemas(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


''' Схема для токена '''
class TokenSchemas(BaseModel):
    access_token: str
    token_type: str