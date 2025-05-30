from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import uuid

from app.models import GradeEnum


''' Модель для описании продукта '''
class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Название продукта")
    description: Optional[str] = Field(None, description="Описание продукта")
    price: Decimal = Field(..., gt=0, decimal_places=2, description="Цена продукта")
    grade: GradeEnum = Field(..., description="Grade продукта")
    manufacturer: str = Field(..., min_length=1, max_length=100, description="Производитель продукта")
    series: Optional[str] = Field(None, max_length=100, description="Серия продукта")
    scale: Optional[str] = Field(None, max_length=20, description="Масштаб продукта")
    difficulty: Optional[int] = Field(None, ge=1, le=10, description="Сложность сборки (1-10)")
    in_stock: int = Field(default=0, ge=0, description="Количество товара на складе")
    main_image: Optional[str] = Field(None, max_length=255, description="URL основного изображения")
    additional_images: Optional[List[str]] = Field(None, description="Список URL дополнительных изображений")

    @field_validator('additional_images', mode='before')
    @classmethod
    def validate_additional_images(cls, v):
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, dict) and 'images' in v:
            return v['images']
        return v

    class Config:
        from_attributes = True
        use_enum_values = True


''' Модель для создания нового продукта '''
class ProductCreate(ProductBase):
    name: str = Field(..., min_length=1, max_length=200)
    price: Decimal = Field(..., gt=0, decimal_places=2)
    grade: GradeEnum
    manufacturer: str = Field(..., min_length=1, max_length=100)

    @field_validator('price', mode='before')
    @classmethod
    def validate_price(cls, v):
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        if isinstance(v, str):
            return Decimal(v)
        return v


''' Модель для внесения изменений продукту '''
class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    grade: Optional[GradeEnum] = None
    manufacturer: Optional[str] = Field(None, min_length=1, max_length=100)
    series: Optional[str] = Field(None, max_length=100)
    scale: Optional[str] = Field(None, max_length=20)
    difficulty: Optional[int] = Field(None, ge=1, le=10)
    in_stock: Optional[int] = Field(None, ge=0)
    main_image: Optional[str] = Field(None, max_length=255)
    additional_images: Optional[List[str]] = None

    @field_validator('price', mode='before')
    @classmethod
    def validate_price(cls, v):
        if v is None:
            return v
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        if isinstance(v, str):
            return Decimal(v)
        return v

    class Config:
        use_enum_values = True


''' Метод для ответа при загрузки изображения '''
class ProductImageUpload(BaseModel):
    main_image: Optional[str] = Field(None, description="URL основного изображения")
    additional_images: Optional[List[str]] = Field(None, description="Список URL дополнительных изображений")

    class Config:
        json_schema_extra = {
            "example": {
                "main_image": "https://example.com/main_image.jpg",
                "additional_images": [
                    "https://example.com/image1.jpg",
                    "https://example.com/image2.jpg"
                ]
            }
        }


''' Модель для фильтрации продукта '''
class ProductFilter(BaseModel):
    name: Optional[str] = Field(None, description="Поиск по названию")
    grade: Optional[List[GradeEnum]] = Field(None, description="Фильтр по grade")
    manufacturer: Optional[List[str]] = Field(None, description="Фильтр по производителю")
    series: Optional[List[str]] = Field(None, description="Фильтр по серии")
    min_price: Optional[Decimal] = Field(None, ge=0, description="Минимальная цена")
    max_price: Optional[Decimal] = Field(None, ge=0, description="Максимальная цена")
    min_difficulty: Optional[int] = Field(None, ge=1, le=10, description="Минимальная сложность")
    max_difficulty: Optional[int] = Field(None, ge=1, le=10, description="Максимальная сложность")
    in_stock_only: Optional[bool] = Field(False, description="Только товары в наличии")
    min_rating: Optional[Decimal] = Field(None, ge=0, le=5, description="Минимальный рейтинг")
    sort_by: Optional[str] = Field("created_at", description="Сортировка: name, price, rating, created_at")
    sort_order: Optional[str] = Field("desc", description="Порядок сортировки: asc, desc")

    @field_validator('max_price')
    @classmethod
    def validate_price_range(cls, v, info):
        if v is not None and 'min_price' in info.data and info.data['min_price'] is not None:
            if v < info.data['min_price']:
                raise ValueError('max_price должна быть больше min_price')
        return v

    @field_validator('max_difficulty')
    @classmethod
    def validate_difficulty_range(cls, v, info):
        if v is not None and 'min_difficulty' in info.data and info.data['min_difficulty'] is not None:
            if v < info.data['min_difficulty']:
                raise ValueError('max_difficulty должна быть больше min_difficulty')
        return v

    @field_validator('sort_by')
    @classmethod
    def validate_sort_by(cls, v):
        allowed_sorts = ['name', 'price', 'rating', 'created_at', 'average_rating', 'total_reviews']
        if v not in allowed_sorts:
            raise ValueError(f'sort_by должно быть одним из: {", ".join(allowed_sorts)}')
        return v

    @field_validator('sort_order')
    @classmethod
    def validate_sort_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('sort_order должно быть "asc" или "desc"')
        return v

    class Config:
        use_enum_values = True


''' Модель для отображения данных о продукте в ответе API '''
class ProductResponse(ProductBase):
    id: uuid.UUID = Field(..., description="ID продукта")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    # Вычисляемые поля из модели
    is_in_stock: bool = Field(..., description="Есть ли товар в наличии")
    rating_stars: int = Field(..., description="Рейтинг в звездах (1-5)")
    formatted_price: str = Field(..., description="Отформатированная цена")

    # Поля рейтинга
    average_rating: Decimal = Field(default=Decimal('0.0'), description="Средний рейтинг")
    total_reviews: int = Field(default=0, description="Общее количество отзывов")

    @field_validator('additional_images', mode='before')
    @classmethod
    def parse_additional_images(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, dict) and 'images' in v:
            return v['images']
        if isinstance(v, str):
            import json
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                if isinstance(parsed, dict) and 'images' in parsed:
                    return parsed['images']
            except json.JSONDecodeError:
                pass
        return []

    class Config:
        from_attributes = True
        use_enum_values = True
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


''' Модель для возвращения списка товаров с поддержкой пагинации '''
class ProductListResponse(BaseModel):
    items: List[ProductResponse] = Field(..., description="Список продуктов")
    total: int = Field(..., description="Общее количество продуктов")
    page: int = Field(..., description="Текущая страница")
    size: int = Field(..., description="Размер страницы")
    pages: int = Field(..., description="Общее количество страниц")
    has_next: bool = Field(..., description="Есть ли следующая страница")
    has_prev: bool = Field(..., description="Есть ли предыдущая страница")

    @field_validator('pages', mode='after')
    @classmethod
    def calculate_pages(cls, v, info):
        if 'total' in info.data and 'size' in info.data and info.data['size'] > 0:
            import math
            return math.ceil(info.data['total'] / info.data['size'])
        return v or 0

    @field_validator('has_next', mode='after')
    @classmethod
    def calculate_has_next(cls, v, info):
        if 'page' in info.data and 'pages' in info.data:
            return info.data['page'] < info.data['pages']
        return False

    @field_validator('has_prev', mode='after')
    @classmethod
    def calculate_has_prev(cls, v, info):
        if 'page' in info.data:
            return info.data['page'] > 1
        return False

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class ProductSearchResponse(BaseModel):
    """Ответ для поиска продуктов"""
    query: str = Field(..., description="Поисковый запрос")
    results: ProductListResponse = Field(..., description="Результаты поиска")
    suggestions: List[str] = Field(default=[], description="Предложения для поиска")
    filters_applied: ProductFilter = Field(..., description="Примененные фильтры")

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }