"""
Сервис пользователей для PaidSubscribeBot.
Управляет регистрацией, обновлением и получением данных пользователей.
"""

from typing import Optional, List
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

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
        Установка статуса администратора.
        
        Args:
            telegram_id: ID пользователя в Telegram
            is_admin: Статус администратора
            
        Returns:
            bool: True если статус изменен
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(
                    is_admin=is_admin,
                    updated_at=datetime.utcnow()
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount > 0:
                self.logger.info(
                    "Изменен статус администратора",
                    user_id=telegram_id,
                    is_admin=is_admin
                )
                return True
            
            return False 