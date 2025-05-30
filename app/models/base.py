import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


''' Базовая модель для упрощения кода '''
class BaseModel(Base):
    __abstract__ = True # Указывает, что класс не будет создавать отдельную таблицу

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) # Генерация уникального ID
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False) # Время создания
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc),onupdate=datetime.now(timezone.utc), nullable=False) # Время обновления