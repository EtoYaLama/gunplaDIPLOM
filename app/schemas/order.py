from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
import uuid
from enum import Enum


class OrderStatusEnum(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class CartItemCreate(BaseModel):
    """Модель добавления нового товара в корзину пользователя"""
    product_id: uuid.UUID = Field(..., description="ID товара")
    quantity: int = Field(default=1, ge=1, description="Количество товара")


class CartItemUpdate(BaseModel):
    """Модель для обновления количества товара в корзине"""
    quantity: int = Field(..., ge=1, description="Новое количество товара")


class CartItemResponse(BaseModel):
    """Модель для ответа, описывающая один элемент корзины"""
    id: uuid.UUID
    user_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    # Информация о товаре (если нужна)
    product_name: Optional[str] = None
    product_price: Optional[Decimal] = None
    total_price: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    """Модель для ответа с информацией о корзине"""
    items: List[CartItemResponse]
    total_items: int
    total_amount: Decimal

    class Config:
        from_attributes = True


class OrderItemCreate(BaseModel):
    """Модель для создания элемента заказа"""
    product_id: uuid.UUID
    quantity: int = Field(..., ge=1)
    price: Decimal = Field(..., ge=0)


class OrderItemResponse(BaseModel):
    """Модель для ответа элемента заказа"""
    id: uuid.UUID
    order_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    price: Decimal
    # Информация о товаре (если нужна)
    product_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    """Модель для создания заказа"""
    delivery_address: str = Field(..., min_length=10, max_length=500, description="Адрес доставки")
    payment_method: Optional[str] = Field(None, max_length=50, description="Способ оплаты")
    # Элементы заказа создаются автоматически из корзины
    # Но можно добавить возможность создания заказа с конкретными товарами
    items: Optional[List[OrderItemCreate]] = None


class OrderUpdate(BaseModel):
    """Модель для обновления заказа"""
    status: Optional[OrderStatusEnum] = None
    payment_method: Optional[str] = Field(None, max_length=50)
    payment_id: Optional[str] = Field(None, max_length=100)
    delivery_address: Optional[str] = Field(None, min_length=10, max_length=500)
    estimated_delivery: Optional[datetime] = None


class OrderResponse(BaseModel):
    """Модель для ответа о заказе"""
    id: uuid.UUID
    user_id: uuid.UUID
    total_amount: Decimal
    status: OrderStatusEnum
    payment_method: Optional[str]
    payment_id: Optional[str]
    delivery_address: str
    estimated_delivery: Optional[datetime]
    items: List[OrderItemResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """Модель для отображения списка заказов"""
    id: uuid.UUID
    total_amount: Decimal
    status: OrderStatusEnum
    payment_method: Optional[str]
    delivery_address: str
    estimated_delivery: Optional[datetime]
    items_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderStatsResponse(BaseModel):
    """Модель для статистики заказов"""
    total_orders: int
    pending_orders: int
    confirmed_orders: int
    shipped_orders: int
    delivered_orders: int
    cancelled_orders: int
    total_revenue: Decimal
    average_order_value: Decimal
    orders_this_month: int
    revenue_this_month: Decimal

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    """Модель для обновления только статуса заказа"""
    status: OrderStatusEnum


class CartSummary(BaseModel):
    """Краткая информация о корзине"""
    items_count: int
    total_amount: Decimal