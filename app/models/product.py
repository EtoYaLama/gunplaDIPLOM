from sqlalchemy import Column, String, Text, DECIMAL, Integer, JSON, Enum
from sqlalchemy.orm import relationship
from app.models import BaseModel
import enum


''' Таблица видов (Grade) модельки '''
class GradeEnum(enum.Enum):
    HG = "HG"  # High Grade 1/144
    RG = "RG"  # Real Grade 1/144
    MG = "MG"  # Master Grade 1/100
    MR_VER_KA = "MR_VER_KA"  # Ver.Ka
    MGEX = "MGEX"  # Master Grade Extreme
    PG = "PG"  # Perfect Grade 1/60


''' Таблица продукта '''
class Product(BaseModel):
    __tablename__ = "products"

    name = Column(String(200), nullable=False, index=True) # Название продукта
    description = Column(Text, nullable=True) # Описание продукта
    price = Column(DECIMAL(10, 2), nullable=False) # Цена продукта
    grade = Column(Enum(GradeEnum), nullable=False, index=True) # Grade продукта
    manufacturer = Column(String(100), nullable=False, index=True)  # Производитель продукта
    series = Column(String(100), nullable=True, index=True)  # Серия продукта
    scale = Column(String(20), nullable=True)  # Масштаб продукта
    difficulty = Column(Integer, nullable=True)  # Сложность сборки
    in_stock = Column(Integer, default=0, nullable=False) # Количество товара на скаде

    ''' Изображения '''
    main_image = Column(String(255), nullable=True) # Ссылка на основное изображение
    additional_images = Column(JSON, nullable=True) # JSON-структура с массивом дополнительных изображений

    ''' Поля рейтинга '''
    average_rating = Column(DECIMAL(3, 2), default=0.0) # Средний рейтинг
    total_reviews = Column(Integer, default=0) # Общее количество отзывов

    ''' Создаем связь между таблицами OrderItem, Cart, Review, ViewHistory, Favorite '''
    order_items = relationship("OrderItem", back_populates="product")
    cart_items = relationship("Cart", back_populates="product")


    ''' Пример отображения объекта '''
    def __repr__(self):
        return f"<Product(name='{self.name}', grade='{self.grade.value}')>"


    ''' Проверка на наличие на складе '''
    @property
    def is_in_stock(self):
        return self.in_stock > 0


    ''' Количество звезд для отображения (1-5) '''
    @property
    def rating_stars(self):
        return round(float(self.average_rating or 0))


    ''' Отформатированная цена '''
    @property
    def formatted_price(self):
        return f"{self.price:,.0f}".replace(",", " ")