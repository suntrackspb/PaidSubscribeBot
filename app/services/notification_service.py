"""
Сервис для управления уведомлениями.
Расширенная система уведомлений с шаблонами, планированием и настройками пользователей.
"""

import asyncio
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
from decimal import Decimal

from aiogram import Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, update
from sqlalchemy.orm import selectinload

from app.database.connection import get_async_session
from app.database.models.notification import (
    Notification, NotificationTemplate, NotificationSettings, BroadcastCampaign,
    NotificationType, NotificationStatus, NotificationPriority
)
from app.database.models.user import User
from app.database.models.subscription import Subscription
from app.utils.logger import get_logger
from app.config.settings import get_settings

logger = get_logger("services.notification")


class NotificationService:
    """Сервис для работы с уведомлениями"""

    def __init__(self, bot: Optional[Bot] = None):
        self.bot = bot
        self.logger = logger
        self.settings = get_settings()

    async def _get_session(self) -> AsyncSession:
        """Получение сессии базы данных"""
        async for session in get_async_session():
            return session

    # Управление шаблонами
    async def create_template(
        self,
        name: str,
        type: NotificationType,
        message: str,
        title: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        delay_seconds: int = 0,
        retry_count: int = 3,
        conditions: Optional[Dict[str, Any]] = None,
        created_by: Optional[int] = None
    ) -> NotificationTemplate:
        """Создание шаблона уведомления"""
        async with await self._get_session() as session:
            template = NotificationTemplate(
                name=name,
                type=type,
                title=title,
                message=message,
                priority=priority,
                delay_seconds=delay_seconds,
                retry_count=retry_count,
                conditions=conditions,
                created_by=str(created_by) if created_by else None
            )
            
            session.add(template)
            await session.commit()
            await session.refresh(template)
            
            self.logger.info(
                "Создан шаблон уведомления",
                template_id=template.id,
                name=name,
                type=type.value,
                created_by=created_by
            )
            
            return template

    async def get_template(self, template_id: int) -> Optional[NotificationTemplate]:
        """Получение шаблона по ID"""
        async with await self._get_session() as session:
            query = select(NotificationTemplate).where(NotificationTemplate.id == template_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_templates_by_type(self, type: NotificationType) -> List[NotificationTemplate]:
        """Получение шаблонов по типу"""
        async with await self._get_session() as session:
            query = select(NotificationTemplate).where(
                and_(
                    NotificationTemplate.type == type,
                    NotificationTemplate.is_active == True
                )
            ).order_by(NotificationTemplate.created_at)
            
            result = await session.execute(query)
            return result.scalars().all()

    # Создание уведомлений
    async def create_notification(
        self,
        user_telegram_id: int,
        type: NotificationType,
        message: str,
        title: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        scheduled_at: Optional[datetime] = None,
        template_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """Создание уведомления"""
        async with await self._get_session() as session:
            notification = Notification(
                user_telegram_id=str(user_telegram_id),
                template_id=template_id,
                type=type,
                priority=priority,
                title=title,
                message=message,
                scheduled_at=scheduled_at,
                metadata=metadata
            )
            
            session.add(notification)
            await session.commit()
            await session.refresh(notification)
            
            self.logger.info(
                "Создано уведомление",
                notification_id=notification.id,
                user_id=user_telegram_id,
                type=type.value,
                scheduled=scheduled_at is not None
            )
            
            return notification

    async def create_notification_from_template(
        self,
        user_telegram_id: int,
        template_id: int,
        variables: Optional[Dict[str, Any]] = None,
        scheduled_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Notification]:
        """Создание уведомления на основе шаблона"""
        template = await self.get_template(template_id)
        if not template or not template.is_active:
            return None
        
        # Рендерим сообщение с переменными
        message = template.render_message(variables or {})
        
        # Применяем задержку из шаблона
        if scheduled_at is None and template.delay_seconds > 0:
            scheduled_at = datetime.utcnow() + timedelta(seconds=template.delay_seconds)
        
        return await self.create_notification(
            user_telegram_id=user_telegram_id,
            type=template.type,
            message=message,
            title=template.title,
            priority=template.priority,
            scheduled_at=scheduled_at,
            template_id=template_id,
            metadata=metadata
        )

    # Отправка уведомлений
    async def send_notification(self, notification_id: int) -> bool:
        """Отправка уведомления"""
        if not self.bot:
            self.logger.warning("Bot не инициализирован для отправки уведомлений")
            return False
        
        async with await self._get_session() as session:
            # Получаем уведомление с пользователем
            query = select(Notification).options(
                selectinload(Notification.user)
            ).where(Notification.id == notification_id)
            
            result = await session.execute(query)
            notification = result.scalar_one_or_none()
            
            if not notification:
                return False
            
            # Проверяем настройки пользователя
            settings = await self.get_user_settings(int(notification.user_telegram_id))
            if settings and not settings.is_type_enabled(notification.type):
                notification.cancel()
                await session.commit()
                self.logger.info(
                    "Уведомление отменено - отключено в настройках",
                    notification_id=notification_id,
                    user_id=notification.user_telegram_id
                )
                return False
            
            # Проверяем тихие часы
            if settings and settings.is_quiet_time(datetime.utcnow().hour):
                # Переносим на время после тихих часов
                if settings.quiet_hours_end:
                    tomorrow = datetime.utcnow().replace(hour=settings.quiet_hours_end, minute=0, second=0, microsecond=0)
                    if tomorrow <= datetime.utcnow():
                        tomorrow += timedelta(days=1)
                    notification.scheduled_at = tomorrow
                    await session.commit()
                    self.logger.info(
                        "Уведомление перенесено из-за тихих часов",
                        notification_id=notification_id,
                        new_time=tomorrow
                    )
                    return False
            
            try:
                # Отправляем сообщение
                message = await self.bot.send_message(
                    chat_id=int(notification.user_telegram_id),
                    text=notification.message,
                    parse_mode="HTML"
                )
                
                # Отмечаем как отправленное
                notification.mark_sent(message.message_id)
                await session.commit()
                
                self.logger.info(
                    "Уведомление отправлено",
                    notification_id=notification_id,
                    user_id=notification.user_telegram_id,
                    message_id=message.message_id
                )
                
                return True
                
            except TelegramForbiddenError:
                # Пользователь заблокировал бота
                notification.mark_failed("Пользователь заблокировал бота")
                await session.commit()
                
                self.logger.warning(
                    "Пользователь заблокировал бота",
                    user_id=notification.user_telegram_id
                )
                
                return False
                
            except TelegramBadRequest as e:
                # Ошибка Telegram API
                notification.mark_failed(f"Ошибка Telegram API: {str(e)}")
                await session.commit()
                
                self.logger.error(
                    "Ошибка отправки уведомления",
                    notification_id=notification_id,
                    error=str(e)
                )
                
                return False
                
            except Exception as e:
                # Общая ошибка
                notification.mark_failed(f"Неожиданная ошибка: {str(e)}")
                await session.commit()
                
                self.logger.error(
                    "Неожиданная ошибка при отправке уведомления",
                    notification_id=notification_id,
                    error=str(e),
                    exc_info=True
                )
                
                return False

    async def process_pending_notifications(self, limit: int = 100) -> int:
        """Обработка ожидающих уведомлений"""
        if not self.bot:
            return 0
        
        async with await self._get_session() as session:
            # Получаем уведомления для отправки
            query = select(Notification).where(
                and_(
                    Notification.status == NotificationStatus.PENDING,
                    or_(
                        Notification.scheduled_at.is_(None),
                        Notification.scheduled_at <= datetime.utcnow()
                    )
                )
            ).order_by(
                Notification.priority.desc(),
                Notification.created_at
            ).limit(limit)
            
            result = await session.execute(query)
            notifications = result.scalars().all()
            
            sent_count = 0
            
            for notification in notifications:
                try:
                    success = await self.send_notification(notification.id)
                    if success:
                        sent_count += 1
                    
                    # Небольшая задержка между отправками
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    self.logger.error(
                        "Ошибка обработки уведомления",
                        notification_id=notification.id,
                        error=str(e)
                    )
            
            self.logger.info(
                "Обработана партия уведомлений",
                total=len(notifications),
                sent=sent_count
            )
            
            return sent_count

    # Настройки пользователя
    async def get_user_settings(self, user_telegram_id: int) -> Optional[NotificationSettings]:
        """Получение настроек уведомлений пользователя"""
        async with await self._get_session() as session:
            query = select(NotificationSettings).where(
                NotificationSettings.user_telegram_id == str(user_telegram_id)
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def create_or_update_user_settings(
        self,
        user_telegram_id: int,
        **settings_data
    ) -> NotificationSettings:
        """Создание или обновление настроек пользователя"""
        async with await self._get_session() as session:
            # Пытаемся найти существующие настройки
            query = select(NotificationSettings).where(
                NotificationSettings.user_telegram_id == str(user_telegram_id)
            )
            result = await session.execute(query)
            settings = result.scalar_one_or_none()
            
            if settings:
                # Обновляем существующие настройки
                for key, value in settings_data.items():
                    if hasattr(settings, key):
                        setattr(settings, key, value)
            else:
                # Создаем новые настройки
                settings = NotificationSettings(
                    user_telegram_id=str(user_telegram_id),
                    **settings_data
                )
                session.add(settings)
            
            await session.commit()
            await session.refresh(settings)
            
            return settings

    # Массовые уведомления
    async def create_broadcast_campaign(
        self,
        name: str,
        message: str,
        created_by: int,
        target_all_users: bool = False,
        target_active_subscribers: bool = False,
        target_inactive_users: bool = False,
        target_user_ids: Optional[List[int]] = None,
        scheduled_at: Optional[datetime] = None
    ) -> BroadcastCampaign:
        """Создание кампании массовой рассылки"""
        async with await self._get_session() as session:
            campaign = BroadcastCampaign(
                name=name,
                message=message,
                created_by=str(created_by),
                target_all_users=target_all_users,
                target_active_subscribers=target_active_subscribers,
                target_inactive_users=target_inactive_users,
                target_user_ids=target_user_ids,
                scheduled_at=scheduled_at
            )
            
            session.add(campaign)
            await session.commit()
            await session.refresh(campaign)
            
            # Считаем количество получателей
            recipients_count = await self._count_broadcast_recipients(campaign)
            campaign.total_recipients = recipients_count
            
            await session.commit()
            
            self.logger.info(
                "Создана кампания рассылки",
                campaign_id=campaign.id,
                name=name,
                recipients=recipients_count,
                created_by=created_by
            )
            
            return campaign

    async def _count_broadcast_recipients(self, campaign: BroadcastCampaign) -> int:
        """Подсчет количества получателей для кампании"""
        async with await self._get_session() as session:
            query = select(func.count(User.telegram_id))
            
            if campaign.target_user_ids:
                query = query.where(User.telegram_id.in_(campaign.target_user_ids))
            elif campaign.target_all_users:
                query = query.where(User.is_active == True)
            elif campaign.target_active_subscribers:
                query = query.join(Subscription).where(
                    and_(
                        User.is_active == True,
                        Subscription.is_active == True
                    )
                )
            elif campaign.target_inactive_users:
                # Пользователи без активных подписок
                subquery = select(Subscription.user_id).where(Subscription.is_active == True)
                query = query.where(
                    and_(
                        User.is_active == True,
                        ~User.telegram_id.in_(subquery)
                    )
                )
            
            result = await session.execute(query)
            return result.scalar() or 0

    async def execute_broadcast_campaign(self, campaign_id: int) -> bool:
        """Выполнение кампании массовой рассылки"""
        async with await self._get_session() as session:
            query = select(BroadcastCampaign).where(BroadcastCampaign.id == campaign_id)
            result = await session.execute(query)
            campaign = result.scalar_one_or_none()
            
            if not campaign or not campaign.is_active:
                return False
            
            # Получаем список получателей
            recipients = await self._get_broadcast_recipients(campaign)
            
            # Создаем уведомления для каждого получателя
            for user_id in recipients:
                await self.create_notification(
                    user_telegram_id=user_id,
                    type=NotificationType.BROADCAST,
                    message=campaign.message,
                    priority=NotificationPriority.NORMAL
                )
            
            # Обновляем статус кампании
            campaign.started_at = datetime.utcnow()
            await session.commit()
            
            self.logger.info(
                "Запущена кампания рассылки",
                campaign_id=campaign_id,
                recipients=len(recipients)
            )
            
            return True

    async def _get_broadcast_recipients(self, campaign: BroadcastCampaign) -> List[int]:
        """Получение списка получателей для кампании"""
        async with await self._get_session() as session:
            query = select(User.telegram_id)
            
            if campaign.target_user_ids:
                query = query.where(User.telegram_id.in_(campaign.target_user_ids))
            elif campaign.target_all_users:
                query = query.where(User.is_active == True)
            elif campaign.target_active_subscribers:
                query = query.join(Subscription).where(
                    and_(
                        User.is_active == True,
                        Subscription.is_active == True
                    )
                )
            elif campaign.target_inactive_users:
                # Пользователи без активных подписок
                subquery = select(Subscription.user_id).where(Subscription.is_active == True)
                query = query.where(
                    and_(
                        User.is_active == True,
                        ~User.telegram_id.in_(subquery)
                    )
                )
            
            result = await session.execute(query)
            return [row[0] for row in result.fetchall()]

    # Специализированные уведомления
    async def notify_subscription_expiring(
        self,
        user_id: int,
        subscription_id: int,
        days_left: int
    ):
        """Уведомление об истечении подписки"""
        templates = await self.get_templates_by_type(NotificationType.SUBSCRIPTION_EXPIRING)
        
        if templates:
            template = templates[0]
            variables = {
                "days_left": days_left,
                "subscription_id": subscription_id,
                "user_id": user_id
            }
            
            await self.create_notification_from_template(
                user_telegram_id=user_id,
                template_id=template.id,
                variables=variables
            )
        else:
            # Создаем базовое уведомление
            message = f"⚠️ Ваша подписка истекает через {days_left} дн.! Продлите подписку, чтобы не потерять доступ."
            
            await self.create_notification(
                user_telegram_id=user_id,
                type=NotificationType.SUBSCRIPTION_EXPIRING,
                message=message,
                priority=NotificationPriority.HIGH
            )

    async def notify_payment_success(
        self,
        user_id: int,
        payment_id: int,
        amount: Decimal
    ):
        """Уведомление об успешной оплате"""
        templates = await self.get_templates_by_type(NotificationType.PAYMENT_SUCCESS)
        
        if templates:
            template = templates[0]
            variables = {
                "amount": float(amount),
                "payment_id": payment_id,
                "user_id": user_id
            }
            
            await self.create_notification_from_template(
                user_telegram_id=user_id,
                template_id=template.id,
                variables=variables
            )
        else:
            message = f"✅ Платеж на сумму {amount} ₽ успешно обработан! Ваша подписка активирована."
            
            await self.create_notification(
                user_telegram_id=user_id,
                type=NotificationType.PAYMENT_SUCCESS,
                message=message,
                priority=NotificationPriority.NORMAL
            )

    async def notify_referral_reward(
        self,
        user_id: int,
        reward_amount: Decimal,
        referred_user_id: int
    ):
        """Уведомление о реферальном вознаграждении"""
        templates = await self.get_templates_by_type(NotificationType.REFERRAL_REWARD)
        
        if templates:
            template = templates[0]
            variables = {
                "reward_amount": float(reward_amount),
                "referred_user_id": referred_user_id,
                "user_id": user_id
            }
            
            await self.create_notification_from_template(
                user_telegram_id=user_id,
                template_id=template.id,
                variables=variables
            )
        else:
            message = f"🎉 Вы получили реферальное вознаграждение {reward_amount} ₽ за приглашение друга!"
            
            await self.create_notification(
                user_telegram_id=user_id,
                type=NotificationType.REFERRAL_REWARD,
                message=message,
                priority=NotificationPriority.NORMAL
            )

    async def notify_promo_code_available(
        self,
        user_id: int,
        promo_code: str,
        discount_value: str
    ):
        """Уведомление о доступном промокоде"""
        templates = await self.get_templates_by_type(NotificationType.PROMO_CODE_AVAILABLE)
        
        if templates:
            template = templates[0]
            variables = {
                "promo_code": promo_code,
                "discount_value": discount_value,
                "user_id": user_id
            }
            
            await self.create_notification_from_template(
                user_telegram_id=user_id,
                template_id=template.id,
                variables=variables
            )
        else:
            message = f"🎟️ Для вас доступен промокод <code>{promo_code}</code> со скидкой {discount_value}!"
            
            await self.create_notification(
                user_telegram_id=user_id,
                type=NotificationType.PROMO_CODE_AVAILABLE,
                message=message,
                priority=NotificationPriority.NORMAL
            ) 