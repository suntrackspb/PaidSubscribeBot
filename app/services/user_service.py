"""
Сервис пользователей для PaidSubscribeBot.
Управляет регистрацией, обновлением и получением данных пользователей.
"""

from typing import Optional, List
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from sqlalchemy.sql import func
from sqlalchemy.types import String

from app.database.models.user import User
from app.database.models.subscription import Subscription
from app.config.database import AsyncSessionLocal
from app.utils.logger import get_logger
from app.utils.crypto import encrypt_data, decrypt_data


class UserService:
    """
    Сервис для работы с пользователями.
    
    Обеспечивает:
    - Регистрацию новых пользователей
    - Обновление данных пользователей
    - Получение информации о пользователях
    - Управление правами доступа
    """
    
    def __init__(self):
        self.logger = get_logger("services.user")
    
    async def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None
    ) -> User:
        """
        Получение существующего или создание нового пользователя.
        
        Args:
            telegram_id: ID пользователя в Telegram
            username: Имя пользователя в Telegram (без @)
            first_name: Имя пользователя
            last_name: Фамилия пользователя
            language_code: Код языка пользователя
            
        Returns:
            User: Объект пользователя
        """
        async with AsyncSessionLocal() as session:
            # Пытаемся найти существующего пользователя
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                # Обновляем данные, если они изменились
                updated = False
                
                if username and user.username != username:
                    user.username = username
                    updated = True
                
                if first_name and user.first_name != first_name:
                    user.first_name = first_name
                    updated = True
                
                if last_name and user.last_name != last_name:
                    user.last_name = last_name
                    updated = True
                
                if language_code and user.language_code != language_code:
                    user.language_code = language_code
                    updated = True
                
                if updated:
                    user.updated_at = datetime.utcnow()
                    await session.commit()
                    self.logger.info(
                        "Обновлены данные пользователя",
                        user_id=telegram_id,
                        username=username
                    )
                
                return user
            
            # Создаем нового пользователя
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code or 'ru',
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            self.logger.info(
                "Создан новый пользователь",
                user_id=telegram_id,
                username=username
            )
            
            return user
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Получение пользователя по Telegram ID.
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            Optional[User]: Пользователь или None
        """
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def get_user_with_active_subscription(self, telegram_id: int) -> Optional[User]:
        """
        Получение пользователя с активной подпиской.
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            Optional[User]: Пользователь с активной подпиской или None
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                select(User)
                .join(Subscription)
                .where(
                    and_(
                        User.telegram_id == telegram_id,
                        Subscription.is_active == True,
                        Subscription.expires_at > datetime.utcnow()
                    )
                )
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def update_user_activity(self, telegram_id: int) -> None:
        """
        Обновление времени последней активности пользователя.
        
        Args:
            telegram_id: ID пользователя в Telegram
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(
                    last_activity_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            await session.execute(stmt)
            await session.commit()
    
    async def deactivate_user(self, telegram_id: int) -> bool:
        """
        Деактивация пользователя.
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            bool: True если пользователь деактивирован
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(
                    is_active=False,
                    updated_at=datetime.utcnow()
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount > 0:
                self.logger.info("Пользователь деактивирован", user_id=telegram_id)
                return True
            
            return False
    
    async def activate_user(self, telegram_id: int) -> bool:
        """
        Активация пользователя.
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            bool: True если пользователь активирован
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(
                    is_active=True,
                    updated_at=datetime.utcnow()
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount > 0:
                self.logger.info("Пользователь активирован", user_id=telegram_id)
                return True
            
            return False
    
    async def get_users_list(
        self,
        limit: int = 100,
        offset: int = 0,
        active_only: bool = True,
        with_subscription: bool = False
    ) -> List[User]:
        """
        Получение списка пользователей.
        
        Args:
            limit: Количество пользователей
            offset: Смещение
            active_only: Только активные пользователи
            with_subscription: Только с активной подпиской
            
        Returns:
            List[User]: Список пользователей
        """
        async with AsyncSessionLocal() as session:
            stmt = select(User)
            
            if active_only:
                stmt = stmt.where(User.is_active == True)
            
            if with_subscription:
                stmt = (
                    stmt.join(Subscription)
                    .where(
                        and_(
                            Subscription.is_active == True,
                            Subscription.expires_at > datetime.utcnow()
                        )
                    )
                )
            
            stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
            
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def get_users_count(
        self,
        active_only: bool = True,
        with_subscription: bool = False
    ) -> int:
        """
        Получение количества пользователей.
        
        Args:
            active_only: Только активные пользователи
            with_subscription: Только с активной подпиской
            
        Returns:
            int: Количество пользователей
        """
        async with AsyncSessionLocal() as session:
            stmt = select(User.id)
            
            if active_only:
                stmt = stmt.where(User.is_active == True)
            
            if with_subscription:
                stmt = (
                    stmt.join(Subscription)
                    .where(
                        and_(
                            Subscription.is_active == True,
                            Subscription.expires_at > datetime.utcnow()
                        )
                    )
                )
            
            result = await session.execute(stmt)
            return len(result.scalars().all())
    
    async def get_inactive_users(self, days: int = 30) -> List[User]:
        """
        Получение неактивных пользователей.
        
        Args:
            days: Количество дней неактивности
            
        Returns:
            List[User]: Список неактивных пользователей
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        async with AsyncSessionLocal() as session:
            stmt = (
                select(User)
                .where(
                    and_(
                        User.is_active == True,
                        User.last_activity_at < cutoff_date
                    )
                )
                .order_by(User.last_activity_at.asc())
            )
            
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def is_admin(self, telegram_id: int) -> bool:
        """
        Проверка, является ли пользователь администратором.
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            bool: True если пользователь администратор
        """
        user = await self.get_user_by_telegram_id(telegram_id)
        return user is not None and user.is_admin
    
    async def set_admin_status(self, telegram_id: int, is_admin: bool) -> bool:
        """
        Изменение статуса администратора.
        
        Args:
            telegram_id: ID пользователя в Telegram
            is_admin: Статус администратора
            
        Returns:
            bool: True если статус изменен
        """
        # Примечание: Админы управляются через настройки,
        # но можно добавить поле в базу данных для расширенного функционала
        
        self.logger.info(
            "Изменение статуса администратора",
            user_id=telegram_id,
            is_admin=is_admin
        )
        
        # TODO: Реализовать сохранение в базе данных при необходимости
        return True

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Получение пользователя по username.
        
        Args:
            username: Имя пользователя (без @)
            
        Returns:
            Optional[User]: Пользователь или None
        """
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.username == username)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_recent_users(self, limit: int = 10) -> List[User]:
        """
        Получение списка последних зарегистрированных пользователей.
        
        Args:
            limit: Максимальное количество пользователей
            
        Returns:
            List[User]: Список пользователей
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                select(User)
                .order_by(User.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_active_users_count(self, days: int = 7) -> int:
        """
        Получение количества активных пользователей за период.
        
        Args:
            days: Количество дней для расчета активности
            
        Returns:
            int: Количество активных пользователей
        """
        async with AsyncSessionLocal() as session:
            since_date = datetime.utcnow() - timedelta(days=days)
            stmt = (
                select(User)
                .where(
                    and_(
                        User.last_activity_at >= since_date,
                        User.is_active == True
                    )
                )
            )
            result = await session.execute(stmt)
            users = result.scalars().all()
            return len(list(users))

    async def get_new_users_count(self, days: int = 1) -> int:
        """
        Получение количества новых пользователей за период.
        
        Args:
            days: Количество дней
            
        Returns:
            int: Количество новых пользователей
        """
        async with AsyncSessionLocal() as session:
            since_date = datetime.utcnow() - timedelta(days=days)
            stmt = (
                select(User)
                .where(User.created_at >= since_date)
            )
            result = await session.execute(stmt)
            users = result.scalars().all()
            return len(list(users))

    async def get_all_active_users(self) -> List[User]:
        """
        Получение всех активных пользователей.
        
        Returns:
            List[User]: Список всех активных пользователей
        """
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.is_active == True)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update_user_ban_status(self, telegram_id: int, is_banned: bool) -> bool:
        """
        Изменение статуса блокировки пользователя.
        
        Args:
            telegram_id: ID пользователя в Telegram
            is_banned: Статус блокировки
            
        Returns:
            bool: True если статус изменен
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(
                    is_banned=is_banned,
                    updated_at=datetime.utcnow()
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount > 0:
                action = "заблокирован" if is_banned else "разблокирован"
                self.logger.info(f"Пользователь {action}", user_id=telegram_id)
                return True
            
            return False

    async def get_users_paginated(self, limit: int = 20, offset: int = 0) -> List[User]:
        """
        Получение пользователей с пагинацией.
        
        Args:
            limit: Количество записей
            offset: Смещение
            
        Returns:
            List[User]: Список пользователей
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                select(User)
                .order_by(User.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def search_users(self, search_query: str, limit: int = 20, offset: int = 0) -> List[User]:
        """
        Поиск пользователей по имени или username.
        
        Args:
            search_query: Поисковый запрос
            limit: Количество записей
            offset: Смещение
            
        Returns:
            List[User]: Список найденных пользователей
        """
        async with AsyncSessionLocal() as session:
            search_pattern = f"%{search_query}%"
            stmt = (
                select(User)
                .where(
                    or_(
                        User.username.ilike(search_pattern),
                        User.first_name.ilike(search_pattern),
                        User.last_name.ilike(search_pattern),
                        User.telegram_id.cast(String).like(search_pattern)
                    )
                )
                .order_by(User.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def count_search_results(self, search_query: str) -> int:
        """
        Подсчет результатов поиска пользователей.
        
        Args:
            search_query: Поисковый запрос
            
        Returns:
            int: Количество найденных пользователей
        """
        async with AsyncSessionLocal() as session:
            search_pattern = f"%{search_query}%"
            stmt = (
                select(func.count(User.id))
                .where(
                    or_(
                        User.username.ilike(search_pattern),
                        User.first_name.ilike(search_pattern),
                        User.last_name.ilike(search_pattern),
                        User.telegram_id.cast(String).like(search_pattern)
                    )
                )
            )
            result = await session.execute(stmt)
            return result.scalar() or 0 