from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import uuid

from app.models.order import Order, OrderItem, Cart, OrderStatusEnum
from app.models.product import Product
from app.schemas.order import (
    CartItemCreate, CartItemUpdate, CartResponse, CartItemResponse,
    OrderCreate, OrderUpdate, OrderResponse, OrderListResponse,
    OrderStatsResponse, OrderItemCreate, OrderItemResponse
)
from fastapi import HTTPException, status


class OrderService:
    """Сервис для работы с заказами и корзиной"""
    def __init__(self, db: Session):
        self.db = db

    def get_user_cart(self, user_id: uuid.UUID) -> CartResponse:
        """Получить корзину пользователя"""
        cart_items = (
            self.db.query(Cart)
            .filter(Cart.user_id == user_id)
            .all()
        )

        if not cart_items:
            return CartResponse(items=[], total_items=0, total_amount=Decimal('0.00'))

        # Загружаем информацию о товарах
        cart_response_items = []
        total_amount = Decimal('0.00')
        total_items = 0

        for item in cart_items:
            product = self.db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                item_total = product.price * item.quantity
                total_amount += item_total
                total_items += item.quantity

                cart_response_items.append(CartItemResponse(
                    id=item.id,
                    user_id=item.user_id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    product_name=product.name,
                    product_price=product.price,
                    total_price=item_total,
                    created_at=item.created_at,
                    updated_at=item.updated_at
                ))

        return CartResponse(
            items=cart_response_items,
            total_items=total_items,
            total_amount=total_amount
        )

    def add_to_cart(self, user_id: uuid.UUID, cart_item: CartItemCreate) -> CartItemResponse:
        """Добавить товар в корзину"""
        # Проверяем существование товара
        product = self.db.query(Product).filter(Product.id == cart_item.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Товар с ID {cart_item.product_id} не найден"
            )

        # Проверяем, есть ли уже этот товар в корзине
        existing_item = (
            self.db.query(Cart)
            .filter(and_(Cart.user_id == user_id, Cart.product_id == cart_item.product_id))
            .first()
        )

        if existing_item:
            # Увеличиваем количество
            existing_item.quantity += cart_item.quantity
            existing_item.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing_item)

            return CartItemResponse(
                id=existing_item.id,
                user_id=existing_item.user_id,
                product_id=existing_item.product_id,
                quantity=existing_item.quantity,
                product_name=product.name,
                product_price=product.price,
                total_price=product.price * existing_item.quantity,
                created_at=existing_item.created_at,
                updated_at=existing_item.updated_at
            )
        else:
            # Создаем новый элемент корзины
            new_cart_item = Cart(
                user_id=user_id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity
            )

            self.db.add(new_cart_item)
            self.db.commit()
            self.db.refresh(new_cart_item)

            return CartItemResponse(
                id=new_cart_item.id,
                user_id=new_cart_item.user_id,
                product_id=new_cart_item.product_id,
                quantity=new_cart_item.quantity,
                product_name=product.name,
                product_price=product.price,
                total_price=product.price * new_cart_item.quantity,
                created_at=new_cart_item.created_at,
                updated_at=new_cart_item.updated_at
            )

    def update_cart_item(self, user_id: uuid.UUID, item_id: uuid.UUID, update_data: CartItemUpdate) -> CartItemResponse:
        """Обновить количество товара в корзине"""
        cart_item = (
            self.db.query(Cart)
            .filter(and_(Cart.id == item_id, Cart.user_id == user_id))
            .first()
        )

        if not cart_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Элемент корзины не найден"
            )

        # Получаем информацию о товаре
        product = self.db.query(Product).filter(Product.id == cart_item.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Товар не найден"
            )

        # Обновляем количество
        cart_item.quantity = update_data.quantity
        cart_item.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(cart_item)

        return CartItemResponse(
            id=cart_item.id,
            user_id=cart_item.user_id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            product_name=product.name,
            product_price=product.price,
            total_price=product.price * cart_item.quantity,
            created_at=cart_item.created_at,
            updated_at=cart_item.updated_at
        )

    def remove_from_cart(self, user_id: uuid.UUID, item_id: uuid.UUID) -> bool:
        """Удалить товар из корзины"""
        cart_item = (
            self.db.query(Cart)
            .filter(and_(Cart.id == item_id, Cart.user_id == user_id))
            .first()
        )

        if not cart_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Элемент корзины не найден"
            )

        self.db.delete(cart_item)
        self.db.commit()
        return True

    def clear_cart(self, user_id: uuid.UUID) -> bool:
        """Очистить корзину пользователя"""
        cart_items = self.db.query(Cart).filter(Cart.user_id == user_id).all()

        for item in cart_items:
            self.db.delete(item)

        self.db.commit()
        return True

    def create_order_from_cart(self, user_id: uuid.UUID, order_data: OrderCreate) -> OrderResponse:
        """Создать заказ из корзины пользователя"""
        # Получаем корзину пользователя
        cart_items = self.db.query(Cart).filter(Cart.user_id == user_id).all()

        if not cart_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Корзина пуста"
            )

        # Вычисляем общую сумму заказа
        total_amount = Decimal('0.00')
        order_items_data = []

        for cart_item in cart_items:
            product = self.db.query(Product).filter(Product.id == cart_item.product_id).first()
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Товар с ID {cart_item.product_id} не найден"
                )

            item_total = product.price * cart_item.quantity
            total_amount += item_total

            order_items_data.append({
                'product_id': cart_item.product_id,
                'quantity': cart_item.quantity,
                'price': product.price
            })

        # Создаем заказ
        new_order = Order(
            user_id=user_id,
            total_amount=total_amount,
            status=OrderStatusEnum.PENDING,
            payment_method=order_data.payment_method,
            delivery_address=order_data.delivery_address,
            estimated_delivery=datetime.utcnow() + timedelta(days=3)  # Примерный срок доставки
        )

        self.db.add(new_order)
        self.db.flush()  # Получаем ID заказа

        # Создаем элементы заказа
        order_items = []
        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item_data['product_id'],
                quantity=item_data['quantity'],
                price=item_data['price']
            )
            self.db.add(order_item)
            order_items.append(order_item)

        # Очищаем корзину
        for cart_item in cart_items:
            self.db.delete(cart_item)

        self.db.commit()
        self.db.refresh(new_order)

        # Формируем ответ
        return self._build_order_response(new_order, order_items)

    def get_user_orders(self, user_id: uuid.UUID, skip: int = 0, limit: int = 10) -> List[OrderListResponse]:
        """Получить список заказов пользователя"""
        orders = (
            self.db.query(Order)
            .filter(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        result = []
        for order in orders:
            items_count = self.db.query(func.sum(OrderItem.quantity)).filter(
                OrderItem.order_id == order.id).scalar() or 0

            result.append(OrderListResponse(
                id=order.id,
                total_amount=order.total_amount,
                status=order.status,
                payment_method=order.payment_method,
                delivery_address=order.delivery_address,
                estimated_delivery=order.estimated_delivery,
                items_count=items_count,
                created_at=order.created_at,
                updated_at=order.updated_at
            ))

        return result

    def get_order_by_id(self, user_id: uuid.UUID, order_id: uuid.UUID) -> OrderResponse:
        """Получить заказ по ID"""
        order = (
            self.db.query(Order)
            .filter(and_(Order.id == order_id, Order.user_id == user_id))
            .first()
        )

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Заказ не найден"
            )

        order_items = self.db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

        return self._build_order_response(order, order_items)

    def update_order(self, user_id: uuid.UUID, order_id: uuid.UUID, update_data: OrderUpdate) -> OrderResponse:
        """Обновить заказ"""
        order = (
            self.db.query(Order)
            .filter(and_(Order.id == order_id, Order.user_id == user_id))
            .first()
        )

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Заказ не найден"
            )

        # Проверяем, можно ли изменять заказ
        if order.status in [OrderStatusEnum.SHIPPED, OrderStatusEnum.DELIVERED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя изменять отправленный или доставленный заказ"
            )

        # Обновляем поля
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(order, field, value)

        order.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(order)

        order_items = self.db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        return self._build_order_response(order, order_items)

    def cancel_order(self, user_id: uuid.UUID, order_id: uuid.UUID) -> OrderResponse:
        """Отменить заказ"""
        order = (
            self.db.query(Order)
            .filter(and_(Order.id == order_id, Order.user_id == user_id))
            .first()
        )

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Заказ не найден"
            )

        if order.status in [OrderStatusEnum.SHIPPED, OrderStatusEnum.DELIVERED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя отменить отправленный или доставленный заказ"
            )

        order.status = OrderStatusEnum.CANCELLED
        order.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(order)

        order_items = self.db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        return self._build_order_response(order, order_items)

    def get_order_stats(self, user_id: Optional[uuid.UUID] = None) -> OrderStatsResponse:
        """Получить статистику заказов"""
        query = self.db.query(Order)
        if user_id:
            query = query.filter(Order.user_id == user_id)

        orders = query.all()

        if not orders:
            return OrderStatsResponse(
                total_orders=0,
                pending_orders=0,
                confirmed_orders=0,
                shipped_orders=0,
                delivered_orders=0,
                cancelled_orders=0,
                total_revenue=Decimal('0.00'),
                average_order_value=Decimal('0.00'),
                orders_this_month=0,
                revenue_this_month=Decimal('0.00')
            )

        # Подсчитываем статистику
        stats = {
            'total_orders': len(orders),
            'pending_orders': len([o for o in orders if o.status == OrderStatusEnum.PENDING]),
            'confirmed_orders': len([o for o in orders if o.status == OrderStatusEnum.CONFIRMED]),
            'shipped_orders': len([o for o in orders if o.status == OrderStatusEnum.SHIPPED]),
            'delivered_orders': len([o for o in orders if o.status == OrderStatusEnum.DELIVERED]),
            'cancelled_orders': len([o for o in orders if o.status == OrderStatusEnum.CANCELLED]),
        }

        # Вычисляем финансовую статистику
        delivered_orders = [o for o in orders if o.status == OrderStatusEnum.DELIVERED]
        total_revenue = sum(o.total_amount for o in delivered_orders)
        average_order_value = total_revenue / len(delivered_orders) if delivered_orders else Decimal('0.00')

        # Статистика за текущий месяц
        current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month_orders = [o for o in orders if o.created_at >= current_month]
        this_month_delivered = [o for o in this_month_orders if o.status == OrderStatusEnum.DELIVERED]
        revenue_this_month = sum(o.total_amount for o in this_month_delivered)

        return OrderStatsResponse(
            total_orders=stats['total_orders'],
            pending_orders=stats['pending_orders'],
            confirmed_orders=stats['confirmed_orders'],
            shipped_orders=stats['shipped_orders'],
            delivered_orders=stats['delivered_orders'],
            cancelled_orders=stats['cancelled_orders'],
            total_revenue=total_revenue,
            average_order_value=average_order_value,
            orders_this_month=len(this_month_orders),
            revenue_this_month=revenue_this_month
        )

    def _build_order_response(self, order: Order, order_items: List[OrderItem]) -> OrderResponse:
        """Построить ответ с информацией о заказе"""
        items_response = []

        for item in order_items:
            product = self.db.query(Product).filter(Product.id == item.product_id).first()

            items_response.append(OrderItemResponse(
                id=item.id,
                order_id=item.order_id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price,
                product_name=product.name if product else None,
                created_at=item.created_at,
                updated_at=item.updated_at
            ))

        return OrderResponse(
            id=order.id,
            user_id=order.user_id,
            total_amount=order.total_amount,
            status=order.status,
            payment_method=order.payment_method,
            payment_id=order.payment_id,
            delivery_address=order.delivery_address,
            estimated_delivery=order.estimated_delivery,
            items=items_response,
            created_at=order.created_at,
            updated_at=order.updated_at
        )