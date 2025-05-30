from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.orm import relationship
from app.models import BaseModel

''' Таблица пользователей '''
class User(BaseModel):
    __tablename__ = 'users'

    email = Column(String(250), unique=True, index=True, nullable=False)
    username = Column(String(20), unique=True, index=True, nullable=False)
    password_hash = Column(String(250), nullable=False)
    full_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


    ''' Создаем связь между таблицами Order, Cart, Review, ViewHistory, Favorite '''
    orders = relationship("Order", back_populates="user")
    cart_items = relationship("Cart", back_populates="user")

    ''' Пример отображения объекта '''
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"


    ''' Отображение имени пользователя '''
    @property
    def display_name(self):
        return self.full_name or self.username