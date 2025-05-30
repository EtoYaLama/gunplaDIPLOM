# app/database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Создание движка базы данных
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_recycle=300,   #
    echo=True,          # Установите True для отладки SQL запросов
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Контекстный менеджер для работы с базой данных.
    Использовать когда нужно явно управлять транзакциями.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Ошибка в контексте базы данных: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """Создание всех таблиц"""
    Base.metadata.create_all(bind=engine)