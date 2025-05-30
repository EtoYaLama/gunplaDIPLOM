from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import uuid

from app.database import get_db
from app.services.product_service import ProductService
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    ProductFilter
)
from app.models.product import GradeEnum

router = APIRouter(prefix="/products", tags=["products"])


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    """Dependency для получения ProductService"""
    return ProductService(db)


@router.get("/products/", response_model=ProductListResponse, summary="Get Products")
async def get_products(
        # Параметры пагинации
        page: int = Query(1, ge=1, description="Номер страницы"),
        size: int = Query(20, ge=1, le=100, description="Размер страницы"),

        # Параметры фильтрации
        name: Optional[str] = Query(None, description="Поиск по названию"),
        grade: Optional[List[GradeEnum]] = Query(None, description="Фильтр по grade"),
        manufacturer: Optional[List[str]] = Query(None, description="Фильтр по производителю"),
        series: Optional[List[str]] = Query(None, description="Фильтр по серии"),
        min_price: Optional[float] = Query(None, ge=0, description="Минимальная цена"),
        max_price: Optional[float] = Query(None, ge=0, description="Максимальная цена"),
        min_difficulty: Optional[int] = Query(None, ge=1, le=10, description="Минимальная сложность"),
        max_difficulty: Optional[int] = Query(None, ge=1, le=10, description="Максимальная сложность"),
        in_stock_only: bool = Query(False, description="Только товары в наличии"),
        min_rating: Optional[float] = Query(None, ge=0, le=5, description="Минимальный рейтинг"),
        sort_by: str = Query("created_at", description="Сортировка"),
        sort_order: str = Query("desc", description="Порядок сортировки"),

        # Зависимости
        product_service: ProductService = Depends(get_product_service)
):
    """ Получить список продуктов с фильтрацией и пагинацией """
    try:
        # Создаем объект фильтра
        filters = ProductFilter(
            name=name,
            grade=grade,
            manufacturer=manufacturer,
            series=series,
            min_price=min_price,
            max_price=max_price,
            min_difficulty=min_difficulty,
            max_difficulty=max_difficulty,
            in_stock_only=in_stock_only,
            min_rating=min_rating,
            sort_by=sort_by,
            sort_order=sort_order
        )

        return product_service.get_products(filters=filters, page=page, size=size)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка валидации фильтров: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера: {str(e)}"
        )


@router.post("/products/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED,
             summary="Create Product")
async def create_product(
        product_data: ProductCreate,
        product_service: ProductService = Depends(get_product_service)
):
    """ Создать новый продукт """
    try:
        return product_service.create_product(product_data)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка валидации данных: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании продукта: {str(e)}"
        )


@router.get("/products/{product_id}", response_model=ProductResponse, summary="Get Product")
async def get_product(
        product_id: uuid.UUID,
        product_service: ProductService = Depends(get_product_service)
):
    """ Получить продукт по ID """
    try:
        product = product_service.get_product(product_id)

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Продукт с ID {product_id} не найден"
            )

        return product

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении продукта: {str(e)}"
        )


@router.put("/products/{product_id}", response_model=ProductResponse, summary="Update Product")
async def update_product(
        product_id: uuid.UUID,
        product_data: ProductUpdate,
        product_service: ProductService = Depends(get_product_service)
):
    """ Обновить продукт """
    try:
        product = product_service.update_product(product_id, product_data)

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Продукт с ID {product_id} не найден"
            )

        return product

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка валидации данных: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении продукта: {str(e)}"
        )


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Product")
async def delete_product(
        product_id: uuid.UUID,
        product_service: ProductService = Depends(get_product_service)
):
    """ Удалить продукт """
    try:
        success = product_service.delete_product(product_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Продукт с ID {product_id} не найден"
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении продукта: {str(e)}"
        )


@router.get("/products/filters/options", response_model=Dict[str, Any], summary="Get Filter Options")
async def get_filter_options(
        product_service: ProductService = Depends(get_product_service)
):
    """ Получить опции для фильтрации продуктов """
    try:
        return product_service.get_filter_options()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении опций фильтрации: {str(e)}"
        )