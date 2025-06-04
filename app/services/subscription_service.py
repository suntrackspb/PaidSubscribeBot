"""
Сервис подписок для PaidSubscribeBot.
Управляет созданием, обновлением и проверкой подписок пользователей.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.orm import selectinload

from app.database.models.user import User
from app.database.models.subscription import Subscription, SubscriptionStatus
from app.database.models.payment import Payment, PaymentStatus
from app.database.models.channel import Channel
from app.config.database import AsyncSessionLocal
from app.utils.logger import get_logger


class SubscriptionService:
    """
    Сервис для работы с подписками.
    
    Обеспечивает:
    - Создание новых подписок
    - Активацию/деактивацию подписок
    - Проверку статуса подписок
    - Продление подписок
    - Управление доступом к каналам
    """
    
    def __init__(self):
        self.logger = get_logger("services.subscription")
    
    async def create_subscription(
        self,
        user_id: int,
        channel_id: int,
        duration_days: int,
        price: Decimal,
        payment_id: Optional[int] = None
    ) -> Subscription:
        """
        Создание новой подписки.
        
        Args:
            user_id: ID пользователя
            channel_id: ID канала
            duration_days: Длительность подписки в днях
            price: Стоимость подписки
            payment_id: ID связанного платежа
            
        Returns:
            Subscription: Созданная подписка
        """
        async with AsyncSessionLocal() as session:
            # Проверяем существование пользователя и канала
            user_stmt = select(User).where(User.id == user_id)
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise ValueError(f"Пользователь с ID {user_id} не найден")
            
            channel_stmt = select(Channel).where(Channel.id == channel_id)
            channel_result = await session.execute(channel_stmt)
            channel = channel_result.scalar_one_or_none()
            
            if not channel:
                raise ValueError(f"Канал с ID {channel_id} не найден")
            
            # Создаем подписку
            now = datetime.utcnow()
            expires_at = now + timedelta(days=duration_days)
            
            subscription = Subscription(
                user_id=user_id,
                channel_id=channel_id,
                status=SubscriptionStatus.PENDING,
                price=price,
                duration_days=duration_days,
                starts_at=now,
                expires_at=expires_at,
                payment_id=payment_id,
                created_at=now,
                updated_at=now
            )
            
            session.add(subscription)
            await session.commit()
            await session.refresh(subscription)
            
            self.logger.info(
                "Создана новая подписка",
                subscription_id=subscription.id,
                user_id=user_id,
                channel_id=channel_id,
                duration_days=duration_days,
                price=float(price)
            )
            
            return subscription
    
    async def activate_subscription(self, subscription_id: int) -> bool:
        """
        Активация подписки.
        
        Args:
            subscription_id: ID подписки
            
        Returns:
            bool: True если подписка активирована
        """
        async with AsyncSessionLocal() as session:
            stmt = select(Subscription).where(Subscription.id == subscription_id)
            result = await session.execute(stmt)
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                self.logger.error("Подписка не найдена", subscription_id=subscription_id)
                return False
            
            # Активируем подписку
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.is_active = True
            subscription.activated_at = datetime.utcnow()
            subscription.updated_at = datetime.utcnow()
            
            await session.commit()
            
            self.logger.info(
                "Подписка активирована",
                subscription_id=subscription_id,
                user_id=subscription.user_id
            )
            
            return True
    
    async def deactivate_subscription(self, subscription_id: int, reason: str = "manual") -> bool:
        """
        Деактивация подписки.
        
        Args:
            subscription_id: ID подписки
            reason: Причина деактивации
            
        Returns:
            bool: True если подписка деактивирована
        """
        async with AsyncSessionLocal() as session:
            stmt = select(Subscription).where(Subscription.id == subscription_id)
            result = await session.execute(stmt)
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                self.logger.error("Подписка не найдена", subscription_id=subscription_id)
                return False
            
            # Деактивируем подписку
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.is_active = False
            subscription.cancelled_at = datetime.utcnow()
            subscription.updated_at = datetime.utcnow()
            
            await session.commit()
            
            self.logger.info(
                "Подписка деактивирована",
                subscription_id=subscription_id,
                user_id=subscription.user_id,
                reason=reason
            )
            
            return True
    
    async def get_user_subscription(self, user_id: int, channel_id: int) -> Optional[Subscription]:
        """
        Получение активной подписки пользователя на канал.
        
        Args:
            user_id: ID пользователя
            channel_id: ID канала
            
        Returns:
            Optional[Subscription]: Активная подписка или None
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Subscription)
                .where(
                    and_(
                        Subscription.user_id == user_id,
                        Subscription.channel_id == channel_id,
                        Subscription.is_active == True,
                        Subscription.expires_at > datetime.utcnow()
                    )
                )
                .order_by(Subscription.expires_at.desc())
            )
            
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def get_user_subscriptions(self, user_id: int, active_only: bool = True) -> List[Subscription]:
        """
        Получение всех подписок пользователя.
        
        Args:
            user_id: ID пользователя
            active_only: Только активные подписки
            
        Returns:
            List[Subscription]: Список подписок
        """
        async with AsyncSessionLocal() as session:
            stmt = select(Subscription).where(Subscription.user_id == user_id)
            
            if active_only:
                stmt = stmt.where(
                    and_(
                        Subscription.is_active == True,
                        Subscription.expires_at > datetime.utcnow()
                    )
                )
            
            stmt = stmt.order_by(Subscription.created_at.desc())
            
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def check_subscription_access(self, user_id: int, channel_id: int) -> bool:
        """
        Проверка доступа пользователя к каналу.
        
        Args:
            user_id: ID пользователя
            channel_id: ID канала
            
        Returns:
            bool: True если доступ есть
        """
        subscription = await self.get_user_subscription(user_id, channel_id)
        return subscription is not None
    
    async def extend_subscription(
        self,
        subscription_id: int,
        additional_days: int,
        payment_id: Optional[int] = None
    ) -> bool:
        """
        Продление подписки.
        
        Args:
            subscription_id: ID подписки
            additional_days: Дополнительные дни
            payment_id: ID связанного платежа
            
        Returns:
            bool: True если подписка продлена
        """
        async with AsyncSessionLocal() as session:
            stmt = select(Subscription).where(Subscription.id == subscription_id)
            result = await session.execute(stmt)
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                self.logger.error("Подписка не найдена", subscription_id=subscription_id)
                return False
            
            # Продлеваем подписку
            subscription.expires_at += timedelta(days=additional_days)
            subscription.duration_days += additional_days
            subscription.updated_at = datetime.utcnow()
            
            if payment_id:
                subscription.payment_id = payment_id
            
            await session.commit()
            
            self.logger.info(
                "Подписка продлена",
                subscription_id=subscription_id,
                additional_days=additional_days,
                new_expires_at=subscription.expires_at.isoformat()
            )
            
            return True
    
    async def get_expiring_subscriptions(self, days_ahead: int = 3) -> List[Subscription]:
        """
        Получение подписок, которые скоро истекают.
        
        Args:
            days_ahead: За сколько дней до истечения
            
        Returns:
            List[Subscription]: Список истекающих подписок
        """
        cutoff_date = datetime.utcnow() + timedelta(days=days_ahead)
        
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Subscription)
                .where(
                    and_(
                        Subscription.is_active == True,
                        Subscription.expires_at <= cutoff_date,
                        Subscription.expires_at > datetime.utcnow()
                    )
                )
                .order_by(Subscription.expires_at.asc())
            )
            
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def get_expired_subscriptions(self) -> List[Subscription]:
        """
        Получение истекших подписок.
        
        Returns:
            List[Subscription]: Список истекших подписок
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Subscription)
                .where(
                    and_(
                        Subscription.is_active == True,
                        Subscription.expires_at <= datetime.utcnow()
                    )
                )
                .order_by(Subscription.expires_at.asc())
            )
            
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def process_expired_subscriptions(self) -> int:
        """
        Обработка истекших подписок.
        
        Returns:
            int: Количество обработанных подписок
        """
        expired_subscriptions = await self.get_expired_subscriptions()
        processed_count = 0
        
        for subscription in expired_subscriptions:
            if await self.deactivate_subscription(subscription.id, "expired"):
                processed_count += 1
        
        if processed_count > 0:
            self.logger.info(
                "Обработаны истекшие подписки",
                count=processed_count
            )
        
        return processed_count
    
    async def get_subscription_stats(self, channel_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Получение статистики подписок.
        
        Args:
            channel_id: ID канала (опционально)
            
        Returns:
            Dict[str, Any]: Статистика подписок
        """
        async with AsyncSessionLocal() as session:
            base_query = select(Subscription)
            
            if channel_id:
                base_query = base_query.where(Subscription.channel_id == channel_id)
            
            # Общее количество подписок
            total_result = await session.execute(base_query)
            total_subscriptions = len(list(total_result.scalars().all()))
            
            # Активные подписки
            active_query = base_query.where(
                and_(
                    Subscription.is_active == True,
                    Subscription.expires_at > datetime.utcnow()
                )
            )
            active_result = await session.execute(active_query)
            active_subscriptions = len(list(active_result.scalars().all()))
            
            # Истекшие подписки
            expired_query = base_query.where(
                or_(
                    Subscription.is_active == False,
                    Subscription.expires_at <= datetime.utcnow()
                )
            )
            expired_result = await session.execute(expired_query)
            expired_subscriptions = len(list(expired_result.scalars().all()))
            
            # Подписки, истекающие в ближайшие 7 дней
            soon_expire_date = datetime.utcnow() + timedelta(days=7)
            expiring_query = base_query.where(
                and_(
                    Subscription.is_active == True,
                    Subscription.expires_at <= soon_expire_date,
                    Subscription.expires_at > datetime.utcnow()
                )
            )
            expiring_result = await session.execute(expiring_query)
            expiring_subscriptions = len(list(expiring_result.scalars().all()))
            
            return {
                "total": total_subscriptions,
                "active": active_subscriptions,
                "expired": expired_subscriptions,
                "expiring_soon": expiring_subscriptions
            }

    async def get_active_subscriptions_count(self) -> int:
        """
        Получение количества активных подписок.
        
        Returns:
            int: Количество активных подписок
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Subscription)
                .where(
                    and_(
                        Subscription.is_active == True,
                        Subscription.expires_at > datetime.utcnow()
                    )
                )
            )
            result = await session.execute(stmt)
            subscriptions = result.scalars().all()
            return len(list(subscriptions))

    async def get_expired_subscriptions_count(self) -> int:
        """
        Получение количества истекших подписок.
        
        Returns:
            int: Количество истекших подписок
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Subscription)
                .where(
                    or_(
                        Subscription.is_active == False,
                        Subscription.expires_at <= datetime.utcnow()
                    )
                )
            )
            result = await session.execute(stmt)
            subscriptions = result.scalars().all()
            return len(list(subscriptions))

    async def get_payments_count(self, days: int = 30) -> int:
        """
        Получение количества платежей за период.
        
        Args:
            days: Количество дней
            
        Returns:
            int: Количество платежей
        """
        async with AsyncSessionLocal() as session:
            since_date = datetime.utcnow() - timedelta(days=days)
            stmt = (
                select(Payment)
                .where(
                    and_(
                        Payment.status == PaymentStatus.COMPLETED,
                        Payment.created_at >= since_date
                    )
                )
            )
            result = await session.execute(stmt)
            payments = result.scalars().all()
            return len(list(payments))

    async def get_revenue(self, days: int = 30) -> float:
        """
        Получение общей выручки за период.
        
        Args:
            days: Количество дней
            
        Returns:
            float: Сумма выручки
        """
        async with AsyncSessionLocal() as session:
            since_date = datetime.utcnow() - timedelta(days=days)
            stmt = (
                select(Payment)
                .where(
                    and_(
                        Payment.status == PaymentStatus.COMPLETED,
                        Payment.created_at >= since_date
                    )
                )
            )
            result = await session.execute(stmt)
            payments = list(result.scalars().all())
            
            total_revenue = sum(float(payment.amount) for payment in payments)
            return total_revenue

    async def get_subscriptions_paginated(
        self, 
        limit: int = 20, 
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[Subscription]:
        """
        Получение подписок с пагинацией и фильтрацией.
        
        Args:
            limit: Количество записей
            offset: Смещение
            status_filter: Фильтр по статусу (active, expired, cancelled)
            
        Returns:
            List[Subscription]: Список подписок
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Subscription)
                .options(
                    # Подгружаем связанные объекты
                    selectinload(Subscription.user),
                    selectinload(Subscription.channel)
                )
                .order_by(Subscription.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            
            # Применяем фильтр по статусу
            if status_filter == 'active':
                stmt = stmt.where(
                    and_(
                        Subscription.is_active == True,
                        or_(
                            Subscription.expires_at.is_(None),
                            Subscription.expires_at > datetime.utcnow()
                        )
                    )
                )
            elif status_filter == 'expired':
                stmt = stmt.where(
                    and_(
                        Subscription.expires_at.is_not(None),
                        Subscription.expires_at <= datetime.utcnow()
                    )
                )
            elif status_filter == 'cancelled':
                stmt = stmt.where(Subscription.status == SubscriptionStatus.CANCELLED)
            
            result = await session.execute(stmt)
            subscriptions = result.scalars().all()
            
            return list(subscriptions)
    
    async def get_subscriptions_count(self, status_filter: Optional[str] = None) -> int:
        """
        Получение общего количества подписок с учетом фильтра.
        
        Args:
            status_filter: Фильтр по статусу
            
        Returns:
            int: Количество подписок
        """
        async with AsyncSessionLocal() as session:
            stmt = select(func.count(Subscription.id))
            
            # Применяем фильтр по статусу
            if status_filter == 'active':
                stmt = stmt.where(
                    and_(
                        Subscription.is_active == True,
                        or_(
                            Subscription.expires_at.is_(None),
                            Subscription.expires_at > datetime.utcnow()
                        )
                    )
                )
            elif status_filter == 'expired':
                stmt = stmt.where(
                    and_(
                        Subscription.expires_at.is_not(None),
                        Subscription.expires_at <= datetime.utcnow()
                    )
                )
            elif status_filter == 'cancelled':
                stmt = stmt.where(Subscription.status == SubscriptionStatus.CANCELLED)
            
            result = await session.execute(stmt)
            count = result.scalar()
            
            return count or 0

    async def delete_subscription(self, subscription_id: int) -> bool:
        """
        Удаление подписки.
        
        Args:
            subscription_id: ID подписки
            
        Returns:
            bool: True если подписка удалена
        """
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(Subscription).where(Subscription.id == subscription_id)
                result = await session.execute(stmt)
                subscription = result.scalar_one_or_none()
                
                if not subscription:
                    self.logger.error("Подписка не найдена", subscription_id=subscription_id)
                    return False
                
                await session.delete(subscription)
                await session.commit()
                
                self.logger.info(
                    "Подписка удалена",
                    subscription_id=subscription_id,
                    user_id=subscription.user_id
                )
                
                return True
            except Exception as e:
                self.logger.error("Ошибка удаления подписки", error=str(e))
                await session.rollback()
                return False 