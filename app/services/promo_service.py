"""
Сервис для работы с промокодами.
Управляет созданием, валидацией и применением промокодов.
"""

import random
import string
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload

from app.database.connection import get_async_session
from app.database.models.promo import PromoCode, PromoCodeUsage, PromoCodeSettings, PromoCodeType
from app.database.models.user import User
from app.database.models.payment import Payment
from app.utils.logger import get_logger

logger = get_logger("services.promo")


class PromoService:
    """Сервис для работы с промокодами"""

    def __init__(self):
        self.logger = logger

    async def _get_session(self) -> AsyncSession:
        """Получение сессии базы данных"""
        async for session in get_async_session():
            return session

    # Управление настройками
    async def get_settings(self) -> Optional[PromoCodeSettings]:
        """Получение настроек промокодов"""
        async with await self._get_session() as session:
            query = select(PromoCodeSettings)
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def update_settings(
        self,
        is_enabled: bool = True,
        auto_generate_enabled: bool = False,
        auto_discount_type: PromoCodeType = PromoCodeType.PERCENTAGE,
        auto_discount_value: Decimal = Decimal('10'),
        auto_valid_days: int = 7,
        updated_by: int = None
    ) -> PromoCodeSettings:
        """Обновление настроек промокодов"""
        async with await self._get_session() as session:
            # Получаем существующие настройки или создаем новые
            settings = await self.get_settings()
            
            if not settings:
                settings = PromoCodeSettings()
                session.add(settings)
            
            settings.is_enabled = is_enabled
            settings.auto_generate_enabled = auto_generate_enabled
            settings.auto_discount_type = auto_discount_type
            settings.auto_discount_value = auto_discount_value
            settings.auto_valid_days = auto_valid_days
            settings.updated_by = str(updated_by) if updated_by else None
            settings.updated_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(settings)
            
            self.logger.info(
                "Настройки промокодов обновлены",
                enabled=is_enabled,
                auto_generate=auto_generate_enabled,
                updated_by=updated_by
            )
            
            return settings

    # Создание промокодов
    def generate_promo_code(self, length: int = 8) -> str:
        """Генерация уникального промокода"""
        characters = string.ascii_uppercase + string.digits
        return ''.join(random.choices(characters, k=length))

    async def create_promo_code(
        self,
        code: str,
        type: PromoCodeType,
        value: Decimal,
        title: str,
        description: Optional[str] = None,
        valid_from: Optional[datetime] = None,
        valid_until: Optional[datetime] = None,
        max_uses: Optional[int] = None,
        max_uses_per_user: int = 1,
        min_amount: Optional[Decimal] = None,
        user_telegram_id: Optional[str] = None,
        created_by: Optional[int] = None
    ) -> PromoCode:
        """Создание нового промокода"""
        async with await self._get_session() as session:
            # Проверяем уникальность кода
            existing_query = select(PromoCode).where(PromoCode.code == code)
            existing = await session.execute(existing_query)
            if existing.scalar_one_or_none():
                raise ValueError(f"Промокод {code} уже существует")
            
            promo_code = PromoCode(
                code=code,
                type=type,
                value=value,
                title=title,
                description=description,
                valid_from=valid_from,
                valid_until=valid_until,
                max_uses=max_uses,
                max_uses_per_user=max_uses_per_user,
                min_amount=min_amount,
                user_telegram_id=user_telegram_id,
                created_by=str(created_by) if created_by else None
            )
            
            session.add(promo_code)
            await session.commit()
            await session.refresh(promo_code)
            
            self.logger.info(
                "Создан промокод",
                code=code,
                type=type.value,
                value=float(value),
                created_by=created_by
            )
            
            return promo_code

    async def auto_generate_promo_code(self, user_telegram_id: int) -> Optional[PromoCode]:
        """Автоматическая генерация промокода для нового пользователя"""
        settings = await self.get_settings()
        
        if not settings or not settings.is_enabled or not settings.auto_generate_enabled:
            return None
        
        # Генерируем уникальный код
        code = None
        for _ in range(10):  # Максимум 10 попыток
            candidate = f"WELCOME{self.generate_promo_code(6)}"
            
            async with await self._get_session() as session:
                existing_query = select(PromoCode).where(PromoCode.code == candidate)
                existing = await session.execute(existing_query)
                if not existing.scalar_one_or_none():
                    code = candidate
                    break
        
        if not code:
            self.logger.warning("Не удалось сгенерировать уникальный промокод")
            return None
        
        # Создаем промокод
        valid_until = datetime.utcnow() + timedelta(days=settings.auto_valid_days)
        
        return await self.create_promo_code(
            code=code,
            type=settings.auto_discount_type,
            value=settings.auto_discount_value,
            title="Приветственная скидка",
            description="Скидка для нового пользователя",
            valid_until=valid_until,
            max_uses=1,
            max_uses_per_user=1,
            user_telegram_id=str(user_telegram_id)
        )

    # Получение промокодов
    async def get_promo_code(self, code: str) -> Optional[PromoCode]:
        """Получение промокода по коду"""
        async with await self._get_session() as session:
            query = select(PromoCode).where(PromoCode.code == code.upper())
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_promo_codes(
        self,
        active_only: bool = False,
        user_telegram_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[PromoCode]:
        """Получение списка промокодов"""
        async with await self._get_session() as session:
            query = select(PromoCode).options(
                selectinload(PromoCode.usages)
            ).order_by(desc(PromoCode.created_at))
            
            if active_only:
                query = query.where(PromoCode.is_active == True)
            
            if user_telegram_id:
                query = query.where(
                    or_(
                        PromoCode.user_telegram_id == user_telegram_id,
                        PromoCode.user_telegram_id.is_(None)
                    )
                )
            
            query = query.limit(limit).offset(offset)
            result = await session.execute(query)
            return result.scalars().all()

    # Валидация и применение
    async def validate_promo_code(
        self,
        code: str,
        user_telegram_id: int,
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        Валидация промокода для использования.
        
        Returns:
            Dict с результатом валидации и размером скидки
        """
        promo_code = await self.get_promo_code(code)
        
        if not promo_code:
            return {
                "valid": False,
                "error": "Промокод не найден",
                "discount": Decimal('0')
            }
        
        if not promo_code.is_valid:
            error = "Промокод недействителен"
            if not promo_code.is_active:
                error = "Промокод отключен"
            elif promo_code.max_uses and promo_code.current_uses >= promo_code.max_uses:
                error = "Промокод исчерпан"
            elif promo_code.valid_until and datetime.utcnow() > promo_code.valid_until:
                error = "Промокод истек"
            elif promo_code.valid_from and datetime.utcnow() < promo_code.valid_from:
                error = "Промокод еще не активен"
            
            return {
                "valid": False,
                "error": error,
                "discount": Decimal('0')
            }
        
        # Проверяем персональные ограничения
        if promo_code.user_telegram_id and promo_code.user_telegram_id != str(user_telegram_id):
            return {
                "valid": False,
                "error": "Промокод предназначен для другого пользователя",
                "discount": Decimal('0')
            }
        
        # Проверяем количество использований пользователем
        user_usages = await self.get_user_promo_usage_count(promo_code.id, user_telegram_id)
        if user_usages >= promo_code.max_uses_per_user:
            return {
                "valid": False,
                "error": "Вы уже использовали этот промокод максимальное количество раз",
                "discount": Decimal('0')
            }
        
        # Рассчитываем скидку
        discount = promo_code.calculate_discount(amount)
        
        if discount == 0:
            error = "Промокод не применим к данной сумме"
            if promo_code.min_amount and amount < promo_code.min_amount:
                error = f"Минимальная сумма для применения промокода: {promo_code.min_amount} ₽"
            
            return {
                "valid": False,
                "error": error,
                "discount": Decimal('0')
            }
        
        return {
            "valid": True,
            "error": None,
            "discount": discount,
            "promo_code": promo_code
        }

    async def apply_promo_code(
        self,
        code: str,
        user_telegram_id: int,
        amount: Decimal,
        payment_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Применение промокода к платежу"""
        validation = await self.validate_promo_code(code, user_telegram_id, amount)
        
        if not validation["valid"]:
            return validation
        
        promo_code = validation["promo_code"]
        discount = validation["discount"]
        final_amount = amount - discount
        
        async with await self._get_session() as session:
            # Создаем запись об использовании
            usage = PromoCodeUsage(
                promo_code_id=promo_code.id,
                user_telegram_id=str(user_telegram_id),
                payment_id=payment_id,
                original_amount=amount,
                discount_amount=discount,
                final_amount=final_amount
            )
            
            session.add(usage)
            
            # Увеличиваем счетчик использований
            promo_code.current_uses += 1
            
            await session.commit()
            await session.refresh(usage)
            
            self.logger.info(
                "Применен промокод",
                code=code,
                user_id=user_telegram_id,
                original_amount=float(amount),
                discount=float(discount),
                final_amount=float(final_amount)
            )
            
            return {
                "valid": True,
                "error": None,
                "discount": discount,
                "final_amount": final_amount,
                "usage": usage
            }

    async def get_user_promo_usage_count(self, promo_code_id: int, user_telegram_id: int) -> int:
        """Количество использований промокода пользователем"""
        async with await self._get_session() as session:
            query = select(func.count(PromoCodeUsage.id)).where(
                and_(
                    PromoCodeUsage.promo_code_id == promo_code_id,
                    PromoCodeUsage.user_telegram_id == str(user_telegram_id)
                )
            )
            result = await session.execute(query)
            return result.scalar() or 0

    # Управление промокодами
    async def deactivate_promo_code(self, code: str) -> bool:
        """Деактивация промокода"""
        async with await self._get_session() as session:
            query = select(PromoCode).where(PromoCode.code == code)
            result = await session.execute(query)
            promo_code = result.scalar_one_or_none()
            
            if not promo_code:
                return False
            
            promo_code.is_active = False
            await session.commit()
            
            self.logger.info("Промокод деактивирован", code=code)
            return True

    async def delete_promo_code(self, code: str) -> bool:
        """Удаление промокода"""
        async with await self._get_session() as session:
            query = select(PromoCode).where(PromoCode.code == code)
            result = await session.execute(query)
            promo_code = result.scalar_one_or_none()
            
            if not promo_code:
                return False
            
            await session.delete(promo_code)
            await session.commit()
            
            self.logger.info("Промокод удален", code=code)
            return True

    # Статистика
    async def get_promo_stats(self, code: Optional[str] = None) -> Dict[str, Any]:
        """Получение статистики промокодов"""
        async with await self._get_session() as session:
            stats = {}
            
            if code:
                # Статистика конкретного промокода
                promo_code = await self.get_promo_code(code)
                if not promo_code:
                    return {"error": "Промокод не найден"}
                
                usage_query = select(PromoCodeUsage).where(
                    PromoCodeUsage.promo_code_id == promo_code.id
                )
                usages = await session.execute(usage_query)
                usages_list = usages.scalars().all()
                
                total_discount = sum(usage.discount_amount for usage in usages_list)
                total_original = sum(usage.original_amount for usage in usages_list)
                
                stats = {
                    "code": code,
                    "title": promo_code.title,
                    "type": promo_code.type.value,
                    "value": float(promo_code.value),
                    "total_uses": len(usages_list),
                    "max_uses": promo_code.max_uses,
                    "uses_remaining": promo_code.uses_remaining,
                    "total_discount_given": float(total_discount),
                    "total_original_amount": float(total_original),
                    "is_active": promo_code.is_active,
                    "is_valid": promo_code.is_valid
                }
            else:
                # Общая статистика
                total_codes_query = select(func.count(PromoCode.id))
                active_codes_query = select(func.count(PromoCode.id)).where(
                    PromoCode.is_active == True
                )
                total_usages_query = select(func.count(PromoCodeUsage.id))
                total_discount_query = select(func.sum(PromoCodeUsage.discount_amount))
                
                total_codes = await session.execute(total_codes_query)
                active_codes = await session.execute(active_codes_query)
                total_usages = await session.execute(total_usages_query)
                total_discount = await session.execute(total_discount_query)
                
                stats = {
                    "total_promo_codes": total_codes.scalar() or 0,
                    "active_promo_codes": active_codes.scalar() or 0,
                    "total_usages": total_usages.scalar() or 0,
                    "total_discount_given": float(total_discount.scalar() or 0)
                }
            
            return stats 