"""
Сервис для управления реферальной системой PaidSubscribeBot.
Обрабатывает создание, подтверждение и выплату реферальных вознаграждений.
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.database.models.user import User
from app.database.models.referral import Referral, ReferralSettings
from app.database.models.subscription import Subscription
from app.database.models.payment import Payment
from app.config.database import AsyncSessionLocal
from app.utils.logger import get_logger

logger = get_logger("services.referral")


class ReferralService:
    """Сервис для управления реферальной системой"""
    
    def __init__(self):
        self.session_factory = AsyncSessionLocal
    
    async def get_referral_settings(self) -> Optional[ReferralSettings]:
        """Получение настроек реферальной системы"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(ReferralSettings).order_by(ReferralSettings.id.desc()).limit(1)
            )
            return result.scalar_one_or_none()
    
    async def create_or_update_settings(
        self,
        is_enabled: bool = True,
        reward_type: str = "fixed",
        reward_amount: Decimal = Decimal("100.00"),
        reward_percentage: Optional[Decimal] = None,
        min_payment_amount: Decimal = Decimal("0.00"),
        max_referrals_per_user: int = 100,
        referral_code_expiry_days: int = 30,
        reward_condition: str = "first_payment"
    ) -> ReferralSettings:
        """Создание или обновление настроек реферальной системы"""
        async with self.session_factory() as session:
            # Получаем существующие настройки
            existing_settings = await self.get_referral_settings()
            
            if existing_settings:
                # Обновляем существующие настройки
                existing_settings.is_enabled = is_enabled
                existing_settings.reward_type = reward_type
                existing_settings.reward_amount = reward_amount
                existing_settings.reward_percentage = reward_percentage
                existing_settings.min_payment_amount = min_payment_amount
                existing_settings.max_referrals_per_user = max_referrals_per_user
                existing_settings.referral_code_expiry_days = referral_code_expiry_days
                existing_settings.reward_condition = reward_condition
                existing_settings.updated_at = datetime.utcnow()
                
                settings = existing_settings
            else:
                # Создаем новые настройки
                settings = ReferralSettings(
                    is_enabled=is_enabled,
                    reward_type=reward_type,
                    reward_amount=reward_amount,
                    reward_percentage=reward_percentage,
                    min_payment_amount=min_payment_amount,
                    max_referrals_per_user=max_referrals_per_user,
                    referral_code_expiry_days=referral_code_expiry_days,
                    reward_condition=reward_condition
                )
                session.add(settings)
            
            await session.commit()
            await session.refresh(settings)
            
            logger.info(f"Настройки реферальной системы обновлены: {settings}")
            return settings
    
    def generate_referral_code(self, length: int = 8) -> str:
        """Генерация уникального реферального кода"""
        alphabet = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    async def create_referral(
        self,
        referrer_id: int,
        referred_id: int,
        referral_code: Optional[str] = None
    ) -> Optional[Referral]:
        """Создание новой записи о реферале"""
        async with self.session_factory() as session:
            # Проверяем, что пользователи существуют
            referrer_result = await session.execute(
                select(User).where(User.telegram_id == referrer_id)
            )
            referrer = referrer_result.scalar_one_or_none()
            
            referred_result = await session.execute(
                select(User).where(User.telegram_id == referred_id)
            )
            referred = referred_result.scalar_one_or_none()
            
            if not referrer or not referred:
                logger.warning(f"Пользователи не найдены: referrer_id={referrer_id}, referred_id={referred_id}")
                return None
            
            # Проверяем, что реферал еще не существует
            existing_result = await session.execute(
                select(Referral).where(Referral.referred_id == referred_id)
            )
            existing_referral = existing_result.scalar_one_or_none()
            
            if existing_referral:
                logger.warning(f"Реферал уже существует для пользователя {referred_id}")
                return existing_referral
            
            # Проверяем настройки системы
            settings = await self.get_referral_settings()
            if not settings or not settings.is_enabled:
                logger.warning("Реферальная система отключена")
                return None
            
            # Проверяем лимит рефералов для реферера
            referrals_count = await self.get_referrals_count(referrer_id)
            if referrals_count >= settings.max_referrals_per_user:
                logger.warning(f"Превышен лимит рефералов для пользователя {referrer_id}")
                return None
            
            # Создаем реферал
            referral = Referral(
                referrer_id=referrer_id,
                referred_id=referred_id,
                referral_code=referral_code,
                status="pending"
            )
            
            session.add(referral)
            await session.commit()
            await session.refresh(referral)
            
            logger.info(f"Создан новый реферал: {referral}")
            return referral
    
    async def get_referral_by_code(self, referral_code: str) -> Optional[Referral]:
        """Получение реферала по коду"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Referral).where(Referral.referral_code == referral_code)
            )
            return result.scalar_one_or_none()
    
    async def get_referral_by_referred_id(self, referred_id: int) -> Optional[Referral]:
        """Получение реферала по ID приглашенного пользователя"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Referral).where(Referral.referred_id == referred_id)
            )
            return result.scalar_one_or_none()
    
    async def get_referrals_by_referrer(
        self,
        referrer_id: int,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Referral]:
        """Получение рефералов по ID реферера"""
        async with self.session_factory() as session:
            query = select(Referral).where(Referral.referrer_id == referrer_id)
            
            if status:
                query = query.where(Referral.status == status)
            
            query = query.limit(limit).options(
                selectinload(Referral.referred)
            )
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def get_referrals_count(self, referrer_id: int) -> int:
        """Получение количества рефералов пользователя"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(func.count(Referral.id)).where(Referral.referrer_id == referrer_id)
            )
            return result.scalar() or 0
    
    async def confirm_referral(
        self,
        referred_id: int,
        payment_amount: Optional[Decimal] = None
    ) -> Optional[Referral]:
        """Подтверждение реферала при выполнении условий"""
        async with self.session_factory() as session:
            # Получаем реферал
            result = await session.execute(
                select(Referral).where(Referral.referred_id == referred_id)
            )
            referral = result.scalar_one_or_none()
            
            if not referral or referral.status != "pending":
                return None
            
            # Получаем настройки
            settings = await self.get_referral_settings()
            if not settings or not settings.is_enabled:
                return None
            
            # Проверяем условия для подтверждения
            if payment_amount and payment_amount < settings.min_payment_amount:
                logger.info(f"Сумма платежа {payment_amount} меньше минимальной {settings.min_payment_amount}")
                return None
            
            # Вычисляем размер вознаграждения
            reward_amount = self._calculate_reward(settings, payment_amount)
            
            # Подтверждаем реферал
            referral.confirm(reward_amount)
            
            await session.commit()
            await session.refresh(referral)
            
            logger.info(f"Реферал подтвержден: {referral}, вознаграждение: {reward_amount}")
            return referral
    
    def _calculate_reward(
        self,
        settings: ReferralSettings,
        payment_amount: Optional[Decimal] = None
    ) -> Decimal:
        """Вычисление размера вознаграждения"""
        if settings.reward_type == "fixed":
            return settings.reward_amount
        elif settings.reward_type == "percentage" and payment_amount and settings.reward_percentage:
            return payment_amount * (settings.reward_percentage / 100)
        else:
            return settings.reward_amount
    
    async def mark_referral_rewarded(self, referral_id: int) -> Optional[Referral]:
        """Отметка о выплате вознаграждения"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Referral).where(Referral.id == referral_id)
            )
            referral = result.scalar_one_or_none()
            
            if not referral:
                return None
            
            referral.mark_rewarded()
            
            await session.commit()
            await session.refresh(referral)
            
            logger.info(f"Вознаграждение выплачено для реферала: {referral}")
            return referral
    
    async def get_referral_stats(self, referrer_id: int) -> Dict[str, Any]:
        """Получение статистики по рефералам пользователя"""
        async with self.session_factory() as session:
            # Общее количество рефералов
            total_result = await session.execute(
                select(func.count(Referral.id)).where(Referral.referrer_id == referrer_id)
            )
            total_referrals = total_result.scalar() or 0
            
            # Подтвержденные рефералы
            confirmed_result = await session.execute(
                select(func.count(Referral.id)).where(
                    and_(
                        Referral.referrer_id == referrer_id,
                        Referral.status == "confirmed"
                    )
                )
            )
            confirmed_referrals = confirmed_result.scalar() or 0
            
            # Общая сумма вознаграждений
            reward_result = await session.execute(
                select(func.sum(Referral.reward_amount)).where(
                    and_(
                        Referral.referrer_id == referrer_id,
                        Referral.status.in_(["confirmed", "rewarded"])
                    )
                )
            )
            total_rewards = reward_result.scalar() or Decimal("0.00")
            
            # Выплаченные вознаграждения
            paid_result = await session.execute(
                select(func.sum(Referral.reward_amount)).where(
                    and_(
                        Referral.referrer_id == referrer_id,
                        Referral.is_rewarded == True
                    )
                )
            )
            paid_rewards = paid_result.scalar() or Decimal("0.00")
            
            return {
                "total_referrals": total_referrals,
                "confirmed_referrals": confirmed_referrals,
                "pending_referrals": total_referrals - confirmed_referrals,
                "total_rewards": total_rewards,
                "paid_rewards": paid_rewards,
                "pending_rewards": total_rewards - paid_rewards
            }
    
    async def get_system_referral_stats(self) -> Dict[str, Any]:
        """Получение общей статистики реферальной системы"""
        async with self.session_factory() as session:
            # Общее количество рефералов
            total_result = await session.execute(
                select(func.count(Referral.id))
            )
            total_referrals = total_result.scalar() or 0
            
            # Подтвержденные рефералы
            confirmed_result = await session.execute(
                select(func.count(Referral.id)).where(Referral.status == "confirmed")
            )
            confirmed_referrals = confirmed_result.scalar() or 0
            
            # Общая сумма вознаграждений
            total_rewards_result = await session.execute(
                select(func.sum(Referral.reward_amount)).where(
                    Referral.status.in_(["confirmed", "rewarded"])
                )
            )
            total_rewards = total_rewards_result.scalar() or Decimal("0.00")
            
            # Выплаченные вознаграждения
            paid_rewards_result = await session.execute(
                select(func.sum(Referral.reward_amount)).where(Referral.is_rewarded == True)
            )
            paid_rewards = paid_rewards_result.scalar() or Decimal("0.00")
            
            # Топ рефереров
            top_referrers_result = await session.execute(
                select(
                    Referral.referrer_id,
                    func.count(Referral.id).label("referrals_count")
                )
                .group_by(Referral.referrer_id)
                .order_by(func.count(Referral.id).desc())
                .limit(10)
            )
            top_referrers = [
                {"referrer_id": row.referrer_id, "referrals_count": row.referrals_count}
                for row in top_referrers_result.all()
            ]
            
            return {
                "total_referrals": total_referrals,
                "confirmed_referrals": confirmed_referrals,
                "pending_referrals": total_referrals - confirmed_referrals,
                "total_rewards": total_rewards,
                "paid_rewards": paid_rewards,
                "pending_rewards": total_rewards - paid_rewards,
                "top_referrers": top_referrers
            } 