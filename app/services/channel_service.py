"""
Сервис каналов для PaidSubscribeBot.
Управляет каналами, добавлением/удалением пользователей и настройками доступа.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.database.models.channel import Channel
from app.database.models.user import User
from app.database.models.subscription import Subscription
from app.config.database import get_db_session
from app.config.settings import get_settings
from app.utils.logger import get_logger


class ChannelService:
    """
    Сервис для работы с каналами.
    
    Обеспечивает:
    - Управление каналами
    - Добавление/удаление пользователей
    - Проверку доступа
    - Генерацию пригласительных ссылок
    """
    
    def __init__(self, bot: Optional[Bot] = None):
        self.logger = get_logger("services.channel")
        self.bot = bot
        self.settings = get_settings()
    
    async def get_channel_by_id(self, channel_id: int) -> Optional[Channel]:
        """
        Получение канала по ID.
        
        Args:
            channel_id: ID канала
            
        Returns:
            Optional[Channel]: Канал или None
        """
        async with get_db_session() as session:
            stmt = select(Channel).where(Channel.id == channel_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def get_channel_by_telegram_id(self, telegram_id: int) -> Optional[Channel]:
        """
        Получение канала по Telegram ID.
        
        Args:
            telegram_id: Telegram ID канала
            
        Returns:
            Optional[Channel]: Канал или None
        """
        async with get_db_session() as session:
            stmt = select(Channel).where(Channel.telegram_id == telegram_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def create_channel(
        self,
        telegram_id: int,
        title: str,
        username: Optional[str] = None,
        description: Optional[str] = None,
        monthly_price: Optional[float] = None,
        yearly_price: Optional[float] = None
    ) -> Channel:
        """
        Создание нового канала.
        
        Args:
            telegram_id: Telegram ID канала
            title: Название канала
            username: Username канала (без @)
            description: Описание канала
            monthly_price: Цена месячной подписки
            yearly_price: Цена годовой подписки
            
        Returns:
            Channel: Созданный канал
        """
        async with get_db_session() as session:
            # Проверяем, не существует ли уже канал с таким telegram_id
            existing_stmt = select(Channel).where(Channel.telegram_id == telegram_id)
            existing_result = await session.execute(existing_stmt)
            existing_channel = existing_result.scalar_one_or_none()
            
            if existing_channel:
                raise ValueError(f"Канал с Telegram ID {telegram_id} уже существует")
            
            # Создаем новый канал
            channel = Channel(
                telegram_id=telegram_id,
                title=title,
                username=username,
                description=description,
                monthly_price=monthly_price,
                yearly_price=yearly_price,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            session.add(channel)
            await session.commit()
            await session.refresh(channel)
            
            self.logger.info(
                "Создан новый канал",
                channel_id=channel.id,
                telegram_id=telegram_id,
                title=title
            )
            
            return channel
    
    async def update_channel(
        self,
        channel_id: int,
        title: Optional[str] = None,
        username: Optional[str] = None,
        description: Optional[str] = None,
        monthly_price: Optional[float] = None,
        yearly_price: Optional[float] = None
    ) -> bool:
        """
        Обновление данных канала.
        
        Args:
            channel_id: ID канала
            title: Новое название
            username: Новый username
            description: Новое описание
            monthly_price: Новая цена месячной подписки
            yearly_price: Новая цена годовой подписки
            
        Returns:
            bool: True если канал обновлен
        """
        async with get_db_session() as session:
            stmt = select(Channel).where(Channel.id == channel_id)
            result = await session.execute(stmt)
            channel = result.scalar_one_or_none()
            
            if not channel:
                self.logger.error("Канал не найден", channel_id=channel_id)
                return False
            
            # Обновляем поля
            updated = False
            
            if title is not None and channel.title != title:
                channel.title = title
                updated = True
            
            if username is not None and channel.username != username:
                channel.username = username
                updated = True
            
            if description is not None and channel.description != description:
                channel.description = description
                updated = True
            
            if monthly_price is not None and channel.monthly_price != monthly_price:
                channel.monthly_price = monthly_price
                updated = True
            
            if yearly_price is not None and channel.yearly_price != yearly_price:
                channel.yearly_price = yearly_price
                updated = True
            
            if updated:
                channel.updated_at = datetime.utcnow()
                await session.commit()
                
                self.logger.info(
                    "Канал обновлен",
                    channel_id=channel_id,
                    title=title
                )
            
            return updated
    
    async def add_user_to_channel(self, user_telegram_id: int, channel_telegram_id: int) -> bool:
        """
        Добавление пользователя в канал.
        
        Args:
            user_telegram_id: Telegram ID пользователя
            channel_telegram_id: Telegram ID канала
            
        Returns:
            bool: True если пользователь добавлен
        """
        if not self.bot:
            self.logger.error("Bot не инициализирован для добавления пользователей")
            return False
        
        try:
            # Получаем информацию о канале
            chat = await self.bot.get_chat(channel_telegram_id)
            
            # Создаем пригласительную ссылку для пользователя
            invite_link = await self.bot.create_chat_invite_link(
                chat_id=channel_telegram_id,
                member_limit=1,
                expire_date=None
            )
            
            # Отправляем ссылку пользователю
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=f"🎉 Добро пожаловать! Вот ваша ссылка для доступа к каналу:\n\n{invite_link.invite_link}\n\n"
                     f"Ссылка действительна только для вас."
            )
            
            self.logger.info(
                "Пользователь добавлен в канал",
                user_id=user_telegram_id,
                channel_id=channel_telegram_id
            )
            
            return True
            
        except TelegramBadRequest as e:
            self.logger.error(
                "Ошибка добавления пользователя в канал",
                user_id=user_telegram_id,
                channel_id=channel_telegram_id,
                error=str(e)
            )
            return False
        except TelegramForbiddenError as e:
            self.logger.error(
                "Нет прав для добавления пользователя",
                user_id=user_telegram_id,
                channel_id=channel_telegram_id,
                error=str(e)
            )
            return False
    
    async def remove_user_from_channel(self, user_telegram_id: int, channel_telegram_id: int) -> bool:
        """
        Удаление пользователя из канала.
        
        Args:
            user_telegram_id: Telegram ID пользователя
            channel_telegram_id: Telegram ID канала
            
        Returns:
            bool: True если пользователь удален
        """
        if not self.bot:
            self.logger.error("Bot не инициализирован для удаления пользователей")
            return False
        
        try:
            # Банним пользователя (удаляем из канала)
            await self.bot.ban_chat_member(
                chat_id=channel_telegram_id,
                user_id=user_telegram_id
            )
            
            # Сразу разбаниваем, чтобы пользователь мог вернуться при новой подписке
            await self.bot.unban_chat_member(
                chat_id=channel_telegram_id,
                user_id=user_telegram_id
            )
            
            self.logger.info(
                "Пользователь удален из канала",
                user_id=user_telegram_id,
                channel_id=channel_telegram_id
            )
            
            return True
            
        except TelegramBadRequest as e:
            self.logger.error(
                "Ошибка удаления пользователя из канала",
                user_id=user_telegram_id,
                channel_id=channel_telegram_id,
                error=str(e)
            )
            return False
        except TelegramForbiddenError as e:
            self.logger.error(
                "Нет прав для удаления пользователя",
                user_id=user_telegram_id,
                channel_id=channel_telegram_id,
                error=str(e)
            )
            return False
    
    async def get_channel_members_count(self, channel_telegram_id: int) -> Optional[int]:
        """
        Получение количества участников канала.
        
        Args:
            channel_telegram_id: Telegram ID канала
            
        Returns:
            Optional[int]: Количество участников или None
        """
        if not self.bot:
            self.logger.error("Bot не инициализирован")
            return None
        
        try:
            chat = await self.bot.get_chat(channel_telegram_id)
            return chat.member_count
            
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            self.logger.error(
                "Ошибка получения информации о канале",
                channel_id=channel_telegram_id,
                error=str(e)
            )
            return None
    
    async def create_invite_link(
        self,
        channel_telegram_id: int,
        expire_date: Optional[datetime] = None,
        member_limit: Optional[int] = None
    ) -> Optional[str]:
        """
        Создание пригласительной ссылки.
        
        Args:
            channel_telegram_id: Telegram ID канала
            expire_date: Дата истечения ссылки
            member_limit: Лимит участников
            
        Returns:
            Optional[str]: Пригласительная ссылка или None
        """
        if not self.bot:
            self.logger.error("Bot не инициализирован")
            return None
        
        try:
            invite_link = await self.bot.create_chat_invite_link(
                chat_id=channel_telegram_id,
                expire_date=expire_date,
                member_limit=member_limit
            )
            
            self.logger.info(
                "Создана пригласительная ссылка",
                channel_id=channel_telegram_id,
                link=invite_link.invite_link
            )
            
            return invite_link.invite_link
            
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            self.logger.error(
                "Ошибка создания пригласительной ссылки",
                channel_id=channel_telegram_id,
                error=str(e)
            )
            return None
    
    async def get_all_channels(self, active_only: bool = True) -> List[Channel]:
        """
        Получение всех каналов.
        
        Args:
            active_only: Только активные каналы
            
        Returns:
            List[Channel]: Список каналов
        """
        async with get_db_session() as session:
            stmt = select(Channel)
            
            if active_only:
                stmt = stmt.where(Channel.is_active == True)
            
            stmt = stmt.order_by(Channel.created_at.desc())
            
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def deactivate_channel(self, channel_id: int) -> bool:
        """
        Деактивация канала.
        
        Args:
            channel_id: ID канала
            
        Returns:
            bool: True если канал деактивирован
        """
        async with get_db_session() as session:
            stmt = (
                update(Channel)
                .where(Channel.id == channel_id)
                .values(
                    is_active=False,
                    updated_at=datetime.utcnow()
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount > 0:
                self.logger.info("Канал деактивирован", channel_id=channel_id)
                return True
            
            return False
    
    async def get_channel_stats(self, channel_id: int) -> Dict[str, Any]:
        """
        Получение статистики канала.
        
        Args:
            channel_id: ID канала
            
        Returns:
            Dict[str, Any]: Статистика канала
        """
        async with get_db_session() as session:
            # Получаем канал
            channel_stmt = select(Channel).where(Channel.id == channel_id)
            channel_result = await session.execute(channel_stmt)
            channel = channel_result.scalar_one_or_none()
            
            if not channel:
                return {}
            
            # Получаем количество активных подписок
            active_subs_stmt = (
                select(Subscription)
                .where(
                    Subscription.channel_id == channel_id,
                    Subscription.is_active == True,
                    Subscription.expires_at > datetime.utcnow()
                )
            )
            active_subs_result = await session.execute(active_subs_stmt)
            active_subscriptions = len(active_subs_result.scalars().all())
            
            # Получаем общее количество подписок
            total_subs_stmt = select(Subscription).where(Subscription.channel_id == channel_id)
            total_subs_result = await session.execute(total_subs_stmt)
            total_subscriptions = len(total_subs_result.scalars().all())
            
            # Получаем количество участников из Telegram (если бот доступен)
            telegram_members = None
            if self.bot:
                telegram_members = await self.get_channel_members_count(channel.telegram_id)
            
            return {
                "channel_id": channel_id,
                "title": channel.title,
                "username": channel.username,
                "active_subscriptions": active_subscriptions,
                "total_subscriptions": total_subscriptions,
                "telegram_members": telegram_members,
                "monthly_price": channel.monthly_price,
                "yearly_price": channel.yearly_price,
                "is_active": channel.is_active,
                "created_at": channel.created_at.isoformat() if channel.created_at else None
            } 