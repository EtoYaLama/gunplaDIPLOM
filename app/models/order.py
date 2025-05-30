from sqlalchemy import Column, String, DECIMAL, Integer, ForeignKey, Enum, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models import BaseModel
import enum


''' Перечислимые значения статусов заказов '''
class OrderStatusEnum(enum.Enum):
    PENDING = "pending" # Заказ находить в ожидании подтверждения
    CONFIRMED = "confirmed" # Заказ подтвержден
    SHIPPED = "shipped" # Заказ отправлен
    DELIVERED = "delivered" # Заказ доставлен
    CANCELLED = "cancelled" # Заказ отменен


''' Таблица заказов '''
class Order(BaseModel):
    __tablename__ = "orders"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False) # ID Пользователя
    total_amount = Column(DECIMAL(10, 2), nullable=False) # Итоговая сумма заказа
    status = Column(Enum(OrderStatusEnum), default=OrderStatusEnum.PENDING, nullable=False) # Статус заказа
    payment_method = Column(String(50), nullable=True) # Способ оплаты
    payment_id = Column(String(100), nullable=True) # ID транзакции платежной системы
    delivery_address = Column(Text, nullable=False) # Адрес доставки заказа
    estimated_delivery = Column(DateTime, nullable=True) # Дата и время предполагаемой доставки

    ''' Создаем связь между таблицами User и OrderItem '''
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

    ''' Пример отображения объекта '''
    def __repr__(self):
        return f"<Order(id='{self.id}', status='{self.status.value}')>"


''' Таблица элементов заказа '''
class OrderItem(BaseModel):
    __tablename__ = "order_items"

    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False) # ID Заказа
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False) # ID Продукта
    quantity = Column(Integer, nullable=False) # Количество данного товара в заказе
    price = Column(DECIMAL(10, 2), nullable=False)  # Цена на момент заказа

    ''' Создаем связь между таблицами Order и Product '''
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    ''' Пример отображения объекта '''
    def __repr__(self):
        return f"<OrderItem(product_id='{self.product_id}', quantity={self.quantity})>"


''' Корзина пользователя '''
class Cart(BaseModel):
    __tablename__ = "cart"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False) # ID Пользователя
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False) # ID Продукта
    quantity = Column(Integer, default=1, nullable=False) # Количество данного товара в корзине

    ''' Создаем связь между таблицами User и Product '''
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")

    ''' Пример отображения объекта '''
    def __repr__(self):
        return f"<Cart(user_id='{self.user_id}', product_id='{self.product_id}')>"