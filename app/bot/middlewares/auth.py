"""
Middleware для авторизации и автоматической регистрации пользователей.
"""

from typing import Callable, Dict, Any, Awaitable, Union
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from app.config.settings import get_settings
from app.utils.logger import get_logger, log_user_action


class AuthMiddleware(BaseMiddleware):
    """
    Middleware для авторизации пользователей.
    Автоматически регистрирует новых пользователей и проверяет права доступа.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger("middleware.auth")
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработка события.
        
        Args:
            handler: Следующий обработчик в цепочке
            event: Событие (Message или CallbackQuery)
            data: Данные события
            
        Returns:
            Any: Результат обработки
        """
        user = event.from_user
        
        if not user:
            # Если пользователь не определен, пропускаем
            return await handler(event, data)
        
        # Проверяем режим технического обслуживания
        if self.settings.maintenance_mode and user.id not in self.settings.admin_ids:
            if isinstance(event, Message):
                await event.answer(self.settings.maintenance_message)
            elif isinstance(event, CallbackQuery):
                await event.answer(self.settings.maintenance_message, show_alert=True)
            return
        
        # Получаем или создаем пользователя в базе данных
        try:
            user_data = await self._get_or_create_user(user)
            data["user_data"] = user_data
            
            # Проверяем, не заблокирован ли пользователь
            if user_data and user_data.get("is_banned", False):
                if isinstance(event, Message):
                    await event.answer("🚫 <b>Доступ заблокирован</b>\n\nВаш аккаунт заблокирован администратором.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("Доступ заблокирован", show_alert=True)
                return
            
            # Обновляем время последней активности
            await self._update_user_activity(user.id)
            
        except Exception as e:
            self.logger.error(
                "Ошибка в AuthMiddleware",
                user_id=user.id,
                error=str(e),
                exc_info=True
            )
            # В случае ошибки продолжаем обработку
        
        # Добавляем информацию о правах пользователя
        data["is_admin"] = user.id in self.settings.admin_ids
        
        return await handler(event, data)
    
    async def _get_or_create_user(self, user) -> Dict[str, Any]:
        """
        Получение или создание пользователя в базе данных.
        
        Args:
            user: Объект пользователя Telegram
            
        Returns:
            Dict[str, Any]: Данные пользователя
        """
        # TODO: Реализовать работу с базой данных
        # Пока возвращаем базовые данные
        
        log_user_action(
            user_id=user.id,
            action="middleware_auth",
            username=user.username,
            first_name=user.first_name
        )
        
        return {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "language_code": user.language_code,
            "is_banned": False,
            "is_admin": user.id in self.settings.admin_ids,
        }
    
    async def _update_user_activity(self, user_id: int) -> None:
        """
        Обновление времени последней активности пользователя.
        
        Args:
            user_id: ID пользователя
        """
        # TODO: Реализовать обновление в базе данных
        pass


class AdminMiddleware(BaseMiddleware):
    """
    Middleware для проверки прав администратора.
    Используется только для админских команд.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger("middleware.admin")
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        """
        Проверка прав администратора.
        
        Args:
            handler: Следующий обработчик в цепочке
            event: Событие
            data: Данные события
            
        Returns:
            Any: Результат обработки
        """
        user = event.from_user
        
        if not user or user.id not in self.settings.admin_ids:
            # Если пользователь не администратор
            if isinstance(event, Message):
                await event.answer("❌ <b>Доступ запрещен</b>\n\nЭта команда доступна только администраторам.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Доступ запрещен", show_alert=True)
            return
        
        # Логируем действие администратора
        if isinstance(event, Message):
            command = event.text
        elif isinstance(event, CallbackQuery):
            command = event.data
        else:
            command = "unknown"
        
        log_user_action(
            user_id=user.id,
            action="admin_action",
            command=command,
            username=user.username
        )
        
        return await handler(event, data) 