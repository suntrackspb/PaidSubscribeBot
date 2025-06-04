"""
Модели для промокодов и скидок.
Поддерживает различные типы скидок: фиксированная сумма и процент от стоимости.
"""

from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.config.database import Base


class PromoCodeType(enum.Enum):
    """Типы промокодов"""
    FIXED_AMOUNT = "fixed_amount"  # Фиксированная скидка в рублях
    PERCENTAGE = "percentage"      # Процентная скидка


class PromoCode(Base):
    """
    Модель промокода.
    
    Поддерживает создание скидочных кодов с различными настройками:
    - Типы скидок (фиксированная сумма или процент)
    - Ограничения по времени действия
    - Ограничения по количеству использований
    - Привязка к конкретным пользователям или каналам
    """
    __tablename__ = "promo_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False, comment="Уникальный код промокода")
    
    # Параметры скидки
    type = Column(Enum(PromoCodeType), nullable=False, comment="Тип скидки")
    value = Column(Numeric(10, 2), nullable=False, comment="Размер скидки (рубли или проценты)")
    
    # Описание и метаданные
    title = Column(String(100), nullable=False, comment="Название промокода")
    description = Column(Text, nullable=True, comment="Описание промокода")
    
    # Временные ограничения
    valid_from = Column(DateTime, nullable=True, comment="Дата начала действия")
    valid_until = Column(DateTime, nullable=True, comment="Дата окончания действия")
    
    # Ограничения по использованию
    max_uses = Column(Integer, nullable=True, comment="Максимальное количество использований")
    current_uses = Column(Integer, default=0, nullable=False, comment="Текущее количество использований")
    max_uses_per_user = Column(Integer, default=1, nullable=False, comment="Максимум использований на пользователя")
    
    # Ограничения по пользователям
    user_telegram_id = Column(String(20), ForeignKey("users.telegram_id"), nullable=True, 
                              comment="ID пользователя (если код персональный)")
    
    # Минимальная сумма для применения скидки
    min_amount = Column(Numeric(10, 2), nullable=True, comment="Минимальная сумма заказа для применения")
    
    # Статус и системные поля
    is_active = Column(Boolean, default=True, nullable=False, comment="Активен ли промокод")
    created_at = Column(DateTime, default=func.now(), nullable=False)
    created_by = Column(String(20), ForeignKey("users.telegram_id"), nullable=True,
                        comment="ID администратора, создавшего промокод")
    
    # Отношения
    user = relationship("User", foreign_keys=[user_telegram_id], back_populates="personal_promo_codes")
    creator = relationship("User", foreign_keys=[created_by])
    usages = relationship("PromoCodeUsage", back_populates="promo_code", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PromoCode(code='{self.code}', type='{self.type.value}', value={self.value})>"

    @property
    def is_valid(self) -> bool:
        """Проверяет, действителен ли промокод по времени и использованиям"""
        now = datetime.utcnow()
        
        # Проверяем активность
        if not self.is_active:
            return False
        
        # Проверяем временные ограничения
        if self.valid_from and now < self.valid_from:
            return False
        
        if self.valid_until and now > self.valid_until:
            return False
        
        # Проверяем ограничения по использованию
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        
        return True

    @property
    def uses_remaining(self) -> Optional[int]:
        """Возвращает количество оставшихся использований"""
        if self.max_uses is None:
            return None
        return max(0, self.max_uses - self.current_uses)

    def calculate_discount(self, amount: Decimal) -> Decimal:
        """
        Рассчитывает размер скидки для указанной суммы.
        
        Args:
            amount: Сумма заказа
            
        Returns:
            Размер скидки в рублях
        """
        if not self.is_valid:
            return Decimal('0')
        
        # Проверяем минимальную сумму
        if self.min_amount and amount < self.min_amount:
            return Decimal('0')
        
        if self.type == PromoCodeType.FIXED_AMOUNT:
            # Фиксированная скидка не может быть больше суммы заказа
            return min(self.value, amount)
        
        elif self.type == PromoCodeType.PERCENTAGE:
            # Процентная скидка
            discount = amount * (self.value / 100)
            return discount.quantize(Decimal('0.01'))
        
        return Decimal('0')


class PromoCodeUsage(Base):
    """
    Модель использования промокода.
    Ведет учет всех случаев применения промокодов.
    """
    __tablename__ = "promo_code_usages"

    id = Column(Integer, primary_key=True, index=True)
    
    # Связи
    promo_code_id = Column(Integer, ForeignKey("promo_codes.id"), nullable=False)
    user_telegram_id = Column(String(20), ForeignKey("users.telegram_id"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True,
                        comment="ID платежа, к которому применен промокод")
    
    # Данные об использовании
    original_amount = Column(Numeric(10, 2), nullable=False, comment="Первоначальная сумма")
    discount_amount = Column(Numeric(10, 2), nullable=False, comment="Размер скидки")
    final_amount = Column(Numeric(10, 2), nullable=False, comment="Итоговая сумма к оплате")
    
    # Системные поля
    used_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Отношения
    promo_code = relationship("PromoCode", back_populates="usages")
    user = relationship("User", back_populates="promo_code_usages")
    payment = relationship("Payment", back_populates="promo_code_usage")

    def __repr__(self):
        return f"<PromoCodeUsage(code='{self.promo_code.code}', user={self.user_telegram_id}, discount={self.discount_amount})>"


class PromoCodeSettings(Base):
    """
    Настройки системы промокодов.
    Глобальные параметры для работы с промокодами.
    """
    __tablename__ = "promo_code_settings"

    id = Column(Integer, primary_key=True, index=True)
    
    # Общие настройки
    is_enabled = Column(Boolean, default=True, nullable=False, comment="Включена ли система промокодов")
    auto_generate_enabled = Column(Boolean, default=False, nullable=False, 
                                   comment="Автоматическая генерация промокодов для новых пользователей")
    
    # Настройки автогенерации
    auto_discount_type = Column(Enum(PromoCodeType), default=PromoCodeType.PERCENTAGE, nullable=False)
    auto_discount_value = Column(Numeric(10, 2), default=Decimal('10'), nullable=False)
    auto_valid_days = Column(Integer, default=7, nullable=False, comment="Дни действия автогенерированных кодов")
    
    # Системные поля
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(String(20), ForeignKey("users.telegram_id"), nullable=True)

    def __repr__(self):
        return f"<PromoCodeSettings(enabled={self.is_enabled})>" 