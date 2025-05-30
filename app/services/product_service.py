from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from decimal import Decimal
import uuid
import math

from app.models.product import Product, GradeEnum
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductFilter,
    ProductListResponse,
    ProductResponse
)


class ProductService:
    """Сервис для работы с продуктами"""
    def __init__(self, db: Session):
        self.db = db

    def get_products(
            self,
            filters: Optional[ProductFilter] = None,
            page: int = 1,
            size: int = 20
    ) -> ProductListResponse:
        """Получить список продуктов с фильтрацией и пагинацией"""
        query = self.db.query(Product)

        # Применяем фильтры
        if filters:
            query = self._apply_filters(query, filters)

        # Общее количество записей
        total = query.count()

        # Применяем сортировку
        if filters and filters.sort_by:
            query = self._apply_sorting(query, filters.sort_by, filters.sort_order)
        else:
            query = query.order_by(desc(Product.created_at))

        # Применяем пагинацию
        offset = (page - 1) * size
        products = query.offset(offset).limit(size).all()

        # Вычисляем метаданные пагинации
        pages = math.ceil(total / size) if size > 0 else 0

        return ProductListResponse(
            items=[self._to_response(product) for product in products],
            total=total,
            page=page,
            size=size,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )

    def create_product(self, product_data: ProductCreate) -> ProductResponse:
        """Создать новый продукт"""

        # Подготавливаем данные для создания
        product_dict = product_data.dict()

        # Обрабатываем additional_images как JSON
        if product_dict.get('additional_images'):
            product_dict['additional_images'] = {"images": product_dict['additional_images']}

        # Создаем объект продукта
        db_product = Product(**product_dict)

        # Сохраняем в базу данных
        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)

        return self._to_response(db_product)

    def get_product(self, product_id: uuid.UUID) -> Optional[ProductResponse]:
        """Получить продукт по ID"""

        product = self.db.query(Product).filter(Product.id == product_id).first()

        if not product:
            return None

        return self._to_response(product)

    def update_product(
            self,
            product_id: uuid.UUID,
            product_data: ProductUpdate
    ) -> Optional[ProductResponse]:
        """Обновить продукт"""

        product = self.db.query(Product).filter(Product.id == product_id).first()

        if not product:
            return None

        # Получаем только не None значения
        update_data = product_data.dict(exclude_unset=True)

        # Обрабатываем additional_images
        if 'additional_images' in update_data and update_data['additional_images'] is not None:
            update_data['additional_images'] = {"images": update_data['additional_images']}

        # Обновляем поля
        for field, value in update_data.items():
            setattr(product, field, value)

        self.db.commit()
        self.db.refresh(product)

        return self._to_response(product)

    def delete_product(self, product_id: uuid.UUID) -> bool:
        """Удалить продукт"""

        product = self.db.query(Product).filter(Product.id == product_id).first()

        if not product:
            return False

        self.db.delete(product)
        self.db.commit()

        return True

    def get_filter_options(self) -> Dict[str, Any]:
        """Получить опции для фильтрации"""

        # Получаем уникальные значения для фильтров
        grades = [grade.value for grade in GradeEnum]

        manufacturers = self.db.query(Product.manufacturer) \
            .distinct() \
            .filter(Product.manufacturer.isnot(None)) \
            .all()
        manufacturers = [m[0] for m in manufacturers]

        series = self.db.query(Product.series) \
            .distinct() \
            .filter(Product.series.isnot(None)) \
            .all()
        series = [s[0] for s in series]

        # Получаем диапазоны цен
        price_range = self.db.query(
            func.min(Product.price).label('min_price'),
            func.max(Product.price).label('max_price')
        ).first()

        # Получаем диапазон сложности
        difficulty_range = self.db.query(
            func.min(Product.difficulty).label('min_difficulty'),
            func.max(Product.difficulty).label('max_difficulty')
        ).filter(Product.difficulty.isnot(None)).first()

        return {
            "grades": grades,
            "manufacturers": sorted(manufacturers),
            "series": sorted(series),
            "price_range": {
                "min": float(price_range.min_price) if price_range.min_price else 0,
                "max": float(price_range.max_price) if price_range.max_price else 0
            },
            "difficulty_range": {
                "min": difficulty_range.min_difficulty if difficulty_range.min_difficulty else 1,
                "max": difficulty_range.max_difficulty if difficulty_range.max_difficulty else 10
            }
        }


    def _apply_filters(self, query, filters: ProductFilter):
        """Применить фильтры к запросу"""

        if filters.name:
            query = query.filter(Product.name.ilike(f"%{filters.name}%"))

        if filters.grade:
            query = query.filter(Product.grade.in_(filters.grade))

        if filters.manufacturer:
            query = query.filter(Product.manufacturer.in_(filters.manufacturer))

        if filters.series:
            query = query.filter(Product.series.in_(filters.series))

        if filters.min_price is not None:
            query = query.filter(Product.price >= filters.min_price)

        if filters.max_price is not None:
            query = query.filter(Product.price <= filters.max_price)

        if filters.min_difficulty is not None:
            query = query.filter(Product.difficulty >= filters.min_difficulty)

        if filters.max_difficulty is not None:
            query = query.filter(Product.difficulty <= filters.max_difficulty)

        if filters.in_stock_only:
            query = query.filter(Product.in_stock > 0)

        if filters.min_rating is not None:
            query = query.filter(Product.average_rating >= filters.min_rating)

        return query

    def _apply_sorting(self, query, sort_by: str, sort_order: str):
        """Применить сортировку к запросу"""

        sort_field = getattr(Product, sort_by, None)
        if not sort_field:
            sort_field = Product.created_at

        if sort_order == "asc":
            query = query.order_by(asc(sort_field))
        else:
            query = query.order_by(desc(sort_field))

        return query

    def _to_response(self, product: Product) -> ProductResponse:
        """Преобразовать объект Product в ProductResponse"""

        # Обрабатываем additional_images
        additional_images = []
        if product.additional_images:
            if isinstance(product.additional_images, dict) and 'images' in product.additional_images:
                additional_images = product.additional_images['images']
            elif isinstance(product.additional_images, list):
                additional_images = product.additional_images

        return ProductResponse(
            id=product.id,
            name=product.name,
            description=product.description,
            price=product.price,
            grade=product.grade,
            manufacturer=product.manufacturer,
            series=product.series,
            scale=product.scale,
            difficulty=product.difficulty,
            in_stock=product.in_stock,
            main_image=product.main_image,
            additional_images=additional_images,
            average_rating=product.average_rating or Decimal('0.0'),
            total_reviews=product.total_reviews or 0,
            created_at=product.created_at,
            updated_at=product.updated_at,
            is_in_stock=product.is_in_stock,
            rating_stars=product.rating_stars,
            formatted_price=product.formatted_price
        )