from pydantic_settings import BaseSettings
from pydantic import ValidationError
from authx import AuthXConfig

from dotenv import find_dotenv

config = AuthXConfig()


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    config.JWT_TOKEN_LOCATION = ["cookies"]
    config.JWT_ACCESS_COOKIE_NAME = "gunpla_access_token"


    # Автоматическое подставлением данных с .env файла
    class Config:
        env_file = find_dotenv()


try:
    settings = Settings()
except ValidationError as e:
    print(f'Ошибка загрузки переменных окружения: {e}')
    exit(1)


print(settings.DATABASE_URL)