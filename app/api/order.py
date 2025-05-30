from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from app.services.order_service import OrderService
from app.schemas.order import (
    CartItemCreate, CartItemUpdate, CartResponse, CartItemResponse,
    OrderCreate, OrderUpdate, OrderResponse, OrderListResponse,
    OrderStatsResponse, CartSummary
)
from app.database import get_db
from app.utils.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/cart", response_model=CartResponse, summary="Получить корзину пользователя")
async def get_cart(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """ Получить содержимое корзины текущего пользователя """
    service = OrderService(db)
    return service.get_user_cart(current_user.id)


@router.post("/cart/add", response_model=CartItemResponse, summary="Добавить товар в корзину")
async def add_to_cart(
        cart_item: CartItemCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """ Добавить товар в корзину пользователя. Если товар уже есть в корзине, увеличивается его количество """
    service = OrderService(db)
    return service.add_to_cart(current_user.id, cart_item)


@router.put("/cart/{item_id}", response_model=CartItemResponse, summary="Обновить товар в корзине")
async def update_cart_item(
        item_id: uuid.UUID = Path(..., description="ID элемента корзины"),
        update_data: CartItemUpdate = ...,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """ Обновить количество товара в корзине """
    service = OrderService(db)
    return service.update_cart_item(current_user.id, item_id, update_data)


@router.delete("/cart/{item_id}", summary="Удалить товар из корзины")
async def remove_from_cart(
        item_id: uuid.UUID = Path(..., description="ID элемента корзины"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """ Удалить товар из корзины пользователя """
    service = OrderService(db)
    service.remove_from_cart(current_user.id, item_id)
    return {"message": "Товар удален из корзины"}


@router.delete("/cart/clear", summary="Очистить корзину")
async def clear_cart(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """ Очистить всю корзину пользователя """
    service = OrderService(db)
    service.clear_cart(current_user.id)
    return {"message": "Корзина очищена"}


@router.get("/cart/summary", response_model=CartSummary, summary="Краткая информация о корзине")
async def get_cart_summary(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """ Получить краткую информацию о корзине (количество товаров и общая сумма) """
    service = OrderService(db)
    cart = service.get_user_cart(current_user.id)
    return CartSummary(
        items_count=cart.total_items,
        total_amount=cart.total_amount
    )


# ==================== РОУТЫ ДЛЯ ЗАКАЗОВ ====================

@router.post("/create", response_model=OrderResponse, summary="Создать заказ из корзины")
async def create_order(
        order_data: OrderCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """ Создать новый заказ из содержимого корзины пользователя. После создания заказа корзина автоматически очищается """
    service = OrderService(db)
    return service.create_order_from_cart(current_user.id, order_data)


@router.get("/", response_model=List[OrderListResponse], summary="Получить список заказов")
async def get_orders(
        skip: int = Query(0, ge=0, description="Количество заказов для пропуска"),
        limit: int = Query(10, ge=1, le=100, description="Максимальное количество заказов"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """ Получить список заказов текущего пользователя с пагинацией """
    service = OrderService(db)
    return service.get_user_orders(current_user.id, skip, limit)


@router.get("/{order_id}", response_model=OrderResponse, summary="Получить заказ по ID")
async def get_order(
        order_id: uuid.UUID = Path(..., description="ID заказа"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """ Получить подробную информацию о конкретном заказе """
    service = OrderService(db)
    return service.get_order_by_id(current_user.id, order_id)


@router.put("/{order_id}", response_model=OrderResponse, summary="Обновить заказ")
async def update_order(
        order_id: uuid.UUID = Path(..., description="ID заказа"),
        update_data: OrderUpdate = ...,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """ Обновить информацию о заказе. Нельзя изменять заказы со статусом "отправлен" или "доставлен" """
    service = OrderService(db)
    return service.update_order(current_user.id, order_id, update_data)


@router.patch("/{order_id}/cancel", response_model=OrderResponse, summary="Отменить заказ")
async def cancel_order(
        order_id: uuid.UUID = Path(..., description="ID заказа"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """ Отменить заказ. Нельзя отменить заказы со статусом "отправлен" или "доставлен" """
    service = OrderService(db)
    return service.cancel_order(current_user.id, order_id)


@router.get("/stats/summary", response_model=OrderStatsResponse, summary="Статистика заказов пользователя")
async def get_user_order_stats(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Получить статистику заказов текущего пользователя. Включает информацию о количестве заказов по статусам,
    общую сумму, среднюю стоимость заказа и статистику за текущий месяц.
    """
    service = OrderService(db)
    return service.get_order_stats(current_user.id)


@router.get("/{order_id}/items", response_model=List, summary="Получить товары в заказе")
async def get_order_items(
        order_id: uuid.UUID = Path(..., description="ID заказа"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """ Получить список товаров в конкретном заказе """
    service = OrderService(db)
    order = service.get_order_by_id(current_user.id, order_id)
    return order.items


@router.get("/status/{status}", response_model=List[OrderListResponse], summary="Получить заказы по статусу")
async def get_orders_by_status(
        status: str = Path(..., description="Статус заказа"),
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """ Получить заказы пользователя с определенным статусом. Доступные статусы: pending, confirmed, shipped, delivered, cancelled """
    from app.models.order import OrderStatusEnum

    # Проверяем валидность статуса
    try:
        status_enum = OrderStatusEnum(status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Неверный статус. Доступные: {[s.value for s in OrderStatusEnum]}"
        )

    service = OrderService(db)
    orders = service.get_user_orders(current_user.id, skip, limit)

    # Фильтруем по статусу
    filtered_orders = [order for order in orders if order.status == status_enum]
    return filtered_orders


@router.get("/admin/stats/global", response_model=OrderStatsResponse, summary="Глобальная статистика заказов")
async def get_global_order_stats(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """ Получить глобальную статистику всех заказов. Доступно только администраторам """
    # Проверка на права администратора
    if not current_user.is_admin:  # Предполагаем, что есть поле is_admin
        raise HTTPException(
            status_code=403,
            detail="Недостаточно прав для просмотра глобальной статистики"
        )

    service = OrderService(db)
    return service.get_order_stats()  # Без user_id = глобальная статистика