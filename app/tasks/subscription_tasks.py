"""
Задачи для автоматического управления подписками в PaidSubscribeBot.
Включает проверку истекающих подписок, отправку уведомлений и очистку данных.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List

from aiogram import Bot

from app.services.user_service import UserService
from app.services.subscription_service import SubscriptionService
from app.services.channel_service import ChannelService
from app.services.notification_service import NotificationService
from app.database.models.subscription import Subscription
from app.database.models.user import User
from app.utils.logger import get_logger


class SubscriptionTaskManager:
    """
    Менеджер задач для управления подписками.
    
    Автоматически:
    - Проверяет истекающие подписки
    - Отправляет уведомления
    - Деактивирует просроченные подписки
    - Удаляет пользователей из каналов
    """
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.user_service = UserService()
        self.subscription_service = SubscriptionService()
        self.channel_service = ChannelService(bot)
        self.notification_service = NotificationService(bot)
        self.logger = get_logger("tasks.subscription")
        
        # Настройки уведомлений
        self.expiry_warning_days = [7, 3, 1]  # За сколько дней предупреждать
        self.task_interval = 3600  # Интервал выполнения задач в секундах (1 час)
        
        self._running = False
    
    async def start_tasks(self):
        """Запуск всех автоматических задач"""
        if self._running:
            self.logger.warning("Задачи уже запущены")
            return
        
        self._running = True
        self.logger.info("Запуск автоматических задач")
        
        # Запускаем основной цикл задач
        while self._running:
            try:
                await self._run_all_tasks()
                await asyncio.sleep(self.task_interval)
            except Exception as e:
                self.logger.error("Ошибка в цикле задач", error=str(e))
                await asyncio.sleep(300)  # Ждем 5 минут при ошибке
    
    async def stop_tasks(self):
        """Остановка всех задач"""
        self.logger.info("Остановка автоматических задач")
        self._running = False
    
    async def _run_all_tasks(self):
        """Выполнение всех задач"""
        try:
            # Проверяем истекающие подписки
            await self.check_expiring_subscriptions()
            
            # Обрабатываем истекшие подписки
            await self.process_expired_subscriptions()
            
            # Очистка старых данных
            await self.cleanup_old_data()
            
            self.logger.debug("Все задачи выполнены успешно")
            
        except Exception as e:
            self.logger.error("Ошибка выполнения задач", error=str(e))
    
    async def check_expiring_subscriptions(self):
        """Проверка истекающих подписок и отправка уведомлений"""
        try:
            # Проверяем для каждого периода уведомлений
            for days in self.expiry_warning_days:
                subscriptions = await self.subscription_service.get_expiring_subscriptions(days)
                
                for subscription in subscriptions:
                    await self._send_expiry_warning(subscription, days)
            
            self.logger.info(
                "Проверка истекающих подписок завершена",
                warning_days=self.expiry_warning_days
            )
            
        except Exception as e:
            self.logger.error("Ошибка проверки истекающих подписок", error=str(e))
    
    async def _send_expiry_warning(self, subscription: Subscription, days_left: int):
        """
        Отправка предупреждения об истечении подписки.
        
        Args:
            subscription: Подписка
            days_left: Дней до истечения
        """
        try:
            # Получаем пользователя
            user = await self.user_service.get_user_by_telegram_id(subscription.user_id)
            if not user:
                self.logger.error(
                    "Пользователь не найден для уведомления",
                    subscription_id=subscription.id,
                    user_id=subscription.user_id
                )
                return
            
            # Проверяем, не отправляли ли уже уведомление
            # TODO: Добавить проверку истории уведомлений
            
            # Отправляем уведомление
            success = await self.notification_service.send_subscription_expiring_notification(
                user=user,
                subscription=subscription,
                days_left=days_left
            )
            
            if success:
                self.logger.info(
                    "Отправлено уведомление об истечении подписки",
                    user_id=user.telegram_id,
                    subscription_id=subscription.id,
                    days_left=days_left
                )
            
        except Exception as e:
            self.logger.error(
                "Ошибка отправки уведомления об истечении",
                subscription_id=subscription.id,
                error=str(e)
            )
    
    async def process_expired_subscriptions(self):
        """Обработка истекших подписок"""
        try:
            # Получаем истекшие подписки
            expired_subscriptions = await self.subscription_service.get_expired_subscriptions()
            
            processed_count = 0
            
            for subscription in expired_subscriptions:
                if await self._process_expired_subscription(subscription):
                    processed_count += 1
            
            if processed_count > 0:
                self.logger.info(
                    "Обработаны истекшие подписки",
                    count=processed_count
                )
            
        except Exception as e:
            self.logger.error("Ошибка обработки истекших подписок", error=str(e))
    
    async def _process_expired_subscription(self, subscription: Subscription) -> bool:
        """
        Обработка одной истекшей подписки.
        
        Args:
            subscription: Истекшая подписка
            
        Returns:
            bool: True если обработка прошла успешно
        """
        try:
            # Деактивируем подписку
            await self.subscription_service.deactivate_subscription(
                subscription.id,
                reason="expired"
            )
            
            # Получаем пользователя и канал
            user = await self.user_service.get_user_by_telegram_id(subscription.user_id)
            channel = await self.channel_service.get_channel_by_id(subscription.channel_id)
            
            if user and channel:
                # Удаляем пользователя из канала
                await self.channel_service.remove_user_from_channel(
                    user_telegram_id=user.telegram_id,
                    channel_telegram_id=channel.telegram_id
                )
                
                # Отправляем уведомление об истечении
                await self.notification_service.send_subscription_expired_notification(
                    user=user,
                    subscription=subscription
                )
            
            self.logger.info(
                "Истекшая подписка обработана",
                subscription_id=subscription.id,
                user_id=user.telegram_id if user else None
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Ошибка обработки истекшей подписки",
                subscription_id=subscription.id,
                error=str(e)
            )
            return False
    
    async def cleanup_old_data(self):
        """Очистка старых данных"""
        try:
            # Очистка неактивных пользователей (старше 90 дней)
            inactive_users = await self.user_service.get_inactive_users(days=90)
            
            # TODO: Реализовать архивирование или удаление неактивных пользователей
            
            # Очистка старых платежей
            # TODO: Реализовать очистку старых платежных данных
            
            self.logger.debug("Очистка старых данных завершена")
            
        except Exception as e:
            self.logger.error("Ошибка очистки данных", error=str(e))
    
    async def force_check_subscriptions(self):
        """Принудительная проверка всех подписок (для админа)"""
        try:
            self.logger.info("Запуск принудительной проверки подписок")
            
            await self.check_expiring_subscriptions()
            processed_count = await self.subscription_service.process_expired_subscriptions()
            
            return {
                "success": True,
                "processed_expired": processed_count,
                "message": f"Обработано истекших подписок: {processed_count}"
            }
            
        except Exception as e:
            self.logger.error("Ошибка принудительной проверки", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": "Ошибка при проверке подписок"
            }
    
    async def send_bulk_expiry_notifications(self, days_ahead: int = 3):
        """
        Массовая отправка уведомлений об истечении подписок.
        
        Args:
            days_ahead: За сколько дней до истечения отправлять
        """
        try:
            subscriptions = await self.subscription_service.get_expiring_subscriptions(days_ahead)
            
            sent_count = 0
            failed_count = 0
            
            for subscription in subscriptions:
                user = await self.user_service.get_user_by_telegram_id(subscription.user_id)
                if user:
                    success = await self.notification_service.send_subscription_expiring_notification(
                        user=user,
                        subscription=subscription,
                        days_left=days_ahead
                    )
                    
                    if success:
                        sent_count += 1
                    else:
                        failed_count += 1
                else:
                    failed_count += 1
            
            self.logger.info(
                "Массовая отправка уведомлений завершена",
                sent=sent_count,
                failed=failed_count,
                days_ahead=days_ahead
            )
            
            return {
                "sent": sent_count,
                "failed": failed_count,
                "total": len(subscriptions)
            }
            
        except Exception as e:
            self.logger.error("Ошибка массовой отправки уведомлений", error=str(e))
            return {"sent": 0, "failed": 0, "total": 0, "error": str(e)}


# Глобальный экземпляр менеджера задач
_task_manager = None


def get_task_manager(bot: Bot) -> SubscriptionTaskManager:
    """
    Получение глобального экземпляра менеджера задач.
    
    Args:
        bot: Экземпляр бота
        
    Returns:
        SubscriptionTaskManager: Менеджер задач
    """
    global _task_manager
    if _task_manager is None:
        _task_manager = SubscriptionTaskManager(bot)
    return _task_manager


async def start_background_tasks(bot: Bot):
    """
    Запуск фоновых задач.
    
    Args:
        bot: Экземпляр бота
    """
    task_manager = get_task_manager(bot)
    await task_manager.start_tasks()


async def stop_background_tasks(bot: Bot):
    """
    Остановка фоновых задач.
    
    Args:
        bot: Экземпляр бота
    """
    task_manager = get_task_manager(bot)
    await task_manager.stop_tasks() 