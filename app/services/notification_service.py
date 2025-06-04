"""
Сервис уведомлений для PaidSubscribeBot.
Управляет отправкой уведомлений пользователям и администраторам.
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.database.models.user import User
from app.database.models.subscription import Subscription
from app.database.models.payment import Payment
from app.config.settings import get_settings
from app.utils.logger import get_logger


class NotificationType(Enum):
    """Типы уведомлений"""
    SUBSCRIPTION_EXPIRING = "subscription_expiring"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    NEW_USER = "new_user"
    ADMIN_ALERT = "admin_alert"


class NotificationService:
    """
    Сервис для отправки уведомлений.
    
    Обеспечивает:
    - Отправку уведомлений пользователям
    - Уведомления администраторов
    - Массовые рассылки
    - Шаблоны сообщений
    """
    
    def __init__(self, bot: Optional[Bot] = None):
        self.logger = get_logger("services.notification")
        self.bot = bot
        self.settings = get_settings()
    
    async def send_subscription_expiring_notification(
        self,
        user: User,
        subscription: Subscription,
        days_left: int
    ) -> bool:
        """
        Уведомление о скором истечении подписки.
        
        Args:
            user: Пользователь
            subscription: Подписка
            days_left: Дней до истечения
            
        Returns:
            bool: True если уведомление отправлено
        """
        if not self.bot:
            self.logger.error("Bot не инициализирован")
            return False
        
        try:
            # Формируем текст сообщения
            if days_left == 1:
                text = (
                    "⚠️ <b>Ваша подписка истекает завтра!</b>\n\n"
                    f"Подписка на канал истекает: <b>{subscription.expires_at.strftime('%d.%m.%Y')}</b>\n\n"
                    "Продлите подписку, чтобы не потерять доступ к каналу."
                )
            else:
                text = (
                    f"⚠️ <b>Ваша подписка истекает через {days_left} дней</b>\n\n"
                    f"Подписка на канал истекает: <b>{subscription.expires_at.strftime('%d.%m.%Y')}</b>\n\n"
                    "Рекомендуем продлить подписку заранее."
                )
            
            # Создаем клавиатуру
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Продлить подписку", callback_data=f"renew_{subscription.id}")],
                [InlineKeyboardButton(text="ℹ️ Информация о подписке", callback_data=f"sub_info_{subscription.id}")]
            ])
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            
            self.logger.info(
                "Отправлено уведомление об истечении подписки",
                user_id=user.telegram_id,
                subscription_id=subscription.id,
                days_left=days_left
            )
            
            return True
            
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            self.logger.error(
                "Ошибка отправки уведомления об истечении подписки",
                user_id=user.telegram_id,
                error=str(e)
            )
            return False
    
    async def send_subscription_expired_notification(
        self,
        user: User,
        subscription: Subscription
    ) -> bool:
        """
        Уведомление об истечении подписки.
        
        Args:
            user: Пользователь
            subscription: Подписка
            
        Returns:
            bool: True если уведомление отправлено
        """
        if not self.bot:
            self.logger.error("Bot не инициализирован")
            return False
        
        try:
            text = (
                "❌ <b>Ваша подписка истекла</b>\n\n"
                f"Подписка на канал истекла: <b>{subscription.expires_at.strftime('%d.%m.%Y')}</b>\n\n"
                "Доступ к каналу приостановлен. Вы можете оформить новую подписку в любое время."
            )
            
            # Создаем клавиатуру
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оформить новую подписку", callback_data="new_subscription")],
                [InlineKeyboardButton(text="📞 Связаться с поддержкой", callback_data="support")]
            ])
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            
            self.logger.info(
                "Отправлено уведомление об истечении подписки",
                user_id=user.telegram_id,
                subscription_id=subscription.id
            )
            
            return True
            
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            self.logger.error(
                "Ошибка отправки уведомления об истечении подписки",
                user_id=user.telegram_id,
                error=str(e)
            )
            return False
    
    async def send_payment_success_notification(
        self,
        user: User,
        payment: Payment,
        subscription: Optional[Subscription] = None
    ) -> bool:
        """
        Уведомление об успешной оплате.
        
        Args:
            user: Пользователь
            payment: Платеж
            subscription: Подписка (если создана)
            
        Returns:
            bool: True если уведомление отправлено
        """
        if not self.bot:
            self.logger.error("Bot не инициализирован")
            return False
        
        try:
            text = (
                "✅ <b>Платеж успешно обработан!</b>\n\n"
                f"💰 Сумма: <b>{payment.amount} {payment.currency}</b>\n"
                f"📅 Дата: <b>{payment.created_at.strftime('%d.%m.%Y %H:%M')}</b>\n"
                f"🆔 ID платежа: <code>{payment.external_id}</code>\n\n"
            )
            
            if subscription:
                text += (
                    f"🎉 <b>Подписка активирована!</b>\n"
                    f"📅 Действует до: <b>{subscription.expires_at.strftime('%d.%m.%Y')}</b>\n\n"
                    "Теперь у вас есть доступ к каналу."
                )
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📱 Перейти в канал", url="https://t.me/your_channel")],
                    [InlineKeyboardButton(text="ℹ️ Информация о подписке", callback_data=f"sub_info_{subscription.id}")]
                ])
            else:
                text += "Спасибо за оплату!"
                keyboard = None
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            
            self.logger.info(
                "Отправлено уведомление об успешной оплате",
                user_id=user.telegram_id,
                payment_id=payment.id
            )
            
            return True
            
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            self.logger.error(
                "Ошибка отправки уведомления об успешной оплате",
                user_id=user.telegram_id,
                error=str(e)
            )
            return False
    
    async def send_payment_failed_notification(
        self,
        user: User,
        payment: Payment,
        reason: str = "Неизвестная ошибка"
    ) -> bool:
        """
        Уведомление о неудачной оплате.
        
        Args:
            user: Пользователь
            payment: Платеж
            reason: Причина неудачи
            
        Returns:
            bool: True если уведомление отправлено
        """
        if not self.bot:
            self.logger.error("Bot не инициализирован")
            return False
        
        try:
            text = (
                "❌ <b>Ошибка при обработке платежа</b>\n\n"
                f"💰 Сумма: <b>{payment.amount} {payment.currency}</b>\n"
                f"📅 Дата: <b>{payment.created_at.strftime('%d.%m.%Y %H:%M')}</b>\n"
                f"🆔 ID платежа: <code>{payment.external_id}</code>\n"
                f"❗ Причина: <b>{reason}</b>\n\n"
                "Попробуйте оплатить еще раз или обратитесь в поддержку."
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="retry_payment")],
                [InlineKeyboardButton(text="📞 Связаться с поддержкой", callback_data="support")]
            ])
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            
            self.logger.info(
                "Отправлено уведомление о неудачной оплате",
                user_id=user.telegram_id,
                payment_id=payment.id,
                reason=reason
            )
            
            return True
            
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            self.logger.error(
                "Ошибка отправки уведомления о неудачной оплате",
                user_id=user.telegram_id,
                error=str(e)
            )
            return False
    
    async def send_admin_notification(
        self,
        message: str,
        notification_type: NotificationType = NotificationType.ADMIN_ALERT,
        data: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Отправка уведомления администраторам.
        
        Args:
            message: Текст сообщения
            notification_type: Тип уведомления
            data: Дополнительные данные
            
        Returns:
            int: Количество отправленных уведомлений
        """
        if not self.bot:
            self.logger.error("Bot не инициализирован")
            return 0
        
        admin_ids = getattr(self.settings, 'ADMIN_IDS', [])
        if not admin_ids:
            self.logger.warning("Список администраторов пуст")
            return 0
        
        sent_count = 0
        
        # Формируем полный текст сообщения
        full_message = f"🔔 <b>Уведомление администратора</b>\n\n{message}"
        
        if data:
            full_message += "\n\n📊 <b>Дополнительная информация:</b>\n"
            for key, value in data.items():
                full_message += f"• {key}: <code>{value}</code>\n"
        
        full_message += f"\n⏰ Время: {datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S')} UTC"
        
        for admin_id in admin_ids:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=full_message,
                    parse_mode="HTML"
                )
                sent_count += 1
                
            except (TelegramBadRequest, TelegramForbiddenError) as e:
                self.logger.error(
                    "Ошибка отправки уведомления администратору",
                    admin_id=admin_id,
                    error=str(e)
                )
        
        self.logger.info(
            "Отправлены уведомления администраторам",
            sent_count=sent_count,
            total_admins=len(admin_ids),
            type=notification_type.value
        )
        
        return sent_count
    
    async def send_new_user_notification(self, user: User) -> bool:
        """
        Уведомление о новом пользователе.
        
        Args:
            user: Новый пользователь
            
        Returns:
            bool: True если уведомление отправлено
        """
        message = (
            f"👤 Новый пользователь зарегистрирован!\n\n"
            f"ID: {user.telegram_id}\n"
            f"Имя: {user.first_name or 'Не указано'}\n"
            f"Username: @{user.username or 'Не указан'}\n"
            f"Язык: {user.language_code or 'Не указан'}"
        )
        
        data = {
            "user_id": user.telegram_id,
            "username": user.username,
            "registration_date": user.created_at.isoformat() if user.created_at else None
        }
        
        sent_count = await self.send_admin_notification(
            message=message,
            notification_type=NotificationType.NEW_USER,
            data=data
        )
        
        return sent_count > 0
    
    async def send_bulk_notification(
        self,
        user_ids: List[int],
        message: str,
        parse_mode: str = "HTML",
        keyboard: Optional[InlineKeyboardMarkup] = None
    ) -> Dict[str, int]:
        """
        Массовая рассылка уведомлений.
        
        Args:
            user_ids: Список ID пользователей
            message: Текст сообщения
            parse_mode: Режим парсинга
            keyboard: Клавиатура
            
        Returns:
            Dict[str, int]: Статистика отправки
        """
        if not self.bot:
            self.logger.error("Bot не инициализирован")
            return {"sent": 0, "failed": 0, "total": 0}
        
        sent_count = 0
        failed_count = 0
        
        for user_id in user_ids:
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode=parse_mode,
                    reply_markup=keyboard
                )
                sent_count += 1
                
                # Небольшая задержка между отправками
                await asyncio.sleep(0.1)
                
            except (TelegramBadRequest, TelegramForbiddenError) as e:
                self.logger.error(
                    "Ошибка отправки массового уведомления",
                    user_id=user_id,
                    error=str(e)
                )
                failed_count += 1
        
        stats = {
            "sent": sent_count,
            "failed": failed_count,
            "total": len(user_ids)
        }
        
        self.logger.info(
            "Завершена массовая рассылка",
            **stats
        )
        
        return stats
    
    async def send_welcome_message(self, user: User) -> bool:
        """
        Отправка приветственного сообщения новому пользователю.
        
        Args:
            user: Новый пользователь
            
        Returns:
            bool: True если сообщение отправлено
        """
        if not self.bot:
            self.logger.error("Bot не инициализирован")
            return False
        
        try:
            text = (
                f"👋 <b>Добро пожаловать, {user.first_name or 'пользователь'}!</b>\n\n"
                "Вы успешно зарегистрировались в нашем боте.\n\n"
                "🔹 Используйте /help для получения справки\n"
                "🔹 Команда /subscription для управления подписками\n"
                "🔹 Команда /support для связи с поддержкой\n\n"
                "Начните с оформления подписки на наш закрытый канал!"
            )
            
            # Создаем клавиатуру
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оформить подписку", callback_data="new_subscription")],
                [InlineKeyboardButton(text="📖 Справка", callback_data="help")]
            ])
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            
            self.logger.info(
                "Отправлено приветственное сообщение",
                user_id=user.telegram_id
            )
            
            return True
            
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            self.logger.error(
                "Ошибка отправки приветственного сообщения",
                user_id=user.telegram_id,
                error=str(e)
            )
            return False

    async def broadcast_message(
        self,
        message: str,
        admin_id: int,
        parse_mode: str = "HTML",
        keyboard: Optional[InlineKeyboardMarkup] = None
    ) -> Dict[str, int]:
        """
        Массовая рассылка сообщения всем активным пользователям.
        
        Args:
            message: Текст сообщения для рассылки
            admin_id: ID администратора, инициировавшего рассылку
            parse_mode: Режим парсинга текста
            keyboard: Клавиатура (опционально)
            
        Returns:
            Dict[str, int]: Статистика рассылки
        """
        if not self.bot:
            self.logger.error("Bot не инициализирован")
            return {"sent": 0, "failed": 0, "blocked": 0}
        
        from app.services.user_service import UserService
        
        user_service = UserService()
        
        try:
            # Получаем всех активных пользователей
            users = await user_service.get_all_active_users()
            
            if not users:
                self.logger.warning("Нет активных пользователей для рассылки")
                return {"sent": 0, "failed": 0, "blocked": 0}
            
            self.logger.info(
                "Начинается массовая рассылка",
                admin_id=admin_id,
                total_users=len(users),
                message_length=len(message)
            )
            
            sent_count = 0
            failed_count = 0
            blocked_count = 0
            
            # Отправляем сообщения пакетами по 30 пользователей с задержкой
            batch_size = 30
            delay_between_batches = 1  # секунда между пакетами
            
            for i in range(0, len(users), batch_size):
                batch = users[i:i + batch_size]
                
                # Отправляем сообщения в пакете
                tasks = []
                for user in batch:
                    if user.telegram_id != admin_id:  # Не отправляем админу
                        task = self._send_broadcast_message_to_user(
                            user.telegram_id, message, parse_mode, keyboard
                        )
                        tasks.append((user.telegram_id, task))
                
                # Ожидаем выполнения всех задач в пакете
                results = await asyncio.gather(
                    *[task for _, task in tasks],
                    return_exceptions=True
                )
                
                # Обрабатываем результаты
                for (user_id, _), result in zip(tasks, results):
                    if isinstance(result, Exception):
                        if isinstance(result, TelegramForbiddenError):
                            blocked_count += 1
                            self.logger.debug(f"Пользователь {user_id} заблокировал бота")
                        else:
                            failed_count += 1
                            self.logger.warning(f"Ошибка отправки пользователю {user_id}: {result}")
                    elif result:
                        sent_count += 1
                    else:
                        failed_count += 1
                
                # Задержка между пакетами для соблюдения лимитов Telegram
                if i + batch_size < len(users):
                    await asyncio.sleep(delay_between_batches)
            
            stats = {
                "sent": sent_count,
                "failed": failed_count,
                "blocked": blocked_count
            }
            
            self.logger.info(
                "Массовая рассылка завершена",
                admin_id=admin_id,
                stats=stats
            )
            
            # Отправляем отчет администратору
            report_text = (
                "📊 <b>Отчет о рассылке</b>\n\n"
                f"✅ Отправлено: <b>{sent_count}</b>\n"
                f"❌ Не доставлено: <b>{failed_count}</b>\n"
                f"🚫 Заблокировали бота: <b>{blocked_count}</b>\n\n"
                f"📝 Общий охват: <b>{sent_count}/{len(users)} ({round(sent_count/len(users)*100, 1)}%)</b>"
            )
            
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=report_text,
                    parse_mode="HTML"
                )
            except Exception as e:
                self.logger.error(f"Не удалось отправить отчет админу: {e}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Ошибка массовой рассылки: {e}", exc_info=True)
            return {"sent": 0, "failed": 0, "blocked": 0}

    async def _send_broadcast_message_to_user(
        self,
        user_id: int,
        message: str,
        parse_mode: str = "HTML",
        keyboard: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """
        Отправка сообщения конкретному пользователю (вспомогательный метод).
        
        Args:
            user_id: ID пользователя
            message: Текст сообщения
            parse_mode: Режим парсинга
            keyboard: Клавиатура
            
        Returns:
            bool: True если сообщение отправлено
        """
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=parse_mode,
                reply_markup=keyboard
            )
            return True
            
        except TelegramForbiddenError:
            # Пользователь заблокировал бота
            raise
        except Exception as e:
            # Другие ошибки
            self.logger.debug(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
            return False 