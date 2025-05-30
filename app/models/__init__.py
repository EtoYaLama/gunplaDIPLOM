from app.models.base import BaseModel
from app.models.user import User


''' Экспортируем все модели для удобного импорта '''
__all__ = [
    "BaseModel",
    "User"
    ]