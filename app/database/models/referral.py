"""
Модель реферальной системы для PaidSubscribeBot.
Отслеживает рефералов и их вознаграждения.
"""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship, Mapped

from app.config.database import Base


class Referral(Base):
    """Модель реферала"""
    __tablename__ = "referrals"
    
    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    
    # Кто пригласил (реферер)
    referrer_id: Mapped[int] = Column(Integer, ForeignKey("users.telegram_id"), nullable=False)
    
    # Кого пригласили (реферал)
    referred_id: Mapped[int] = Column(Integer, ForeignKey("users.telegram_id"), nullable=False)
    
    # Реферальный код
    referral_code: Mapped[str] = Column(String(50), nullable=True, index=True)
    
    # Статус реферала
    status: Mapped[str] = Column(String(20), default="pending")  # pending, confirmed, rewarded
    
    # Сумма вознаграждения
    reward_amount: Mapped[Optional[Decimal]] = Column(Numeric(10, 2), nullable=True)
    
    # Валюта вознаграждения
    reward_currency: Mapped[str] = Column(String(10), default="RUB")
    
    # Выплачено ли вознаграждение
    is_rewarded: Mapped[bool] = Column(Boolean, default=False)
    
    # Дата создания реферала
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow)
    
    # Дата подтверждения (когда реферал совершил целевое действие)
    confirmed_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    
    # Дата выплаты вознаграждения
    rewarded_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    
    # Дополнительная информация
    notes: Mapped[Optional[str]] = Column(Text, nullable=True)
    
    # Связи с пользователями
    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="referrals_made")
    referred = relationship("User", foreign_keys=[referred_id], back_populates="referral_info")
    
    def __repr__(self):
        return f"<Referral(id={self.id}, referrer_id={self.referrer_id}, referred_id={self.referred_id}, status={self.status})>"
    
    @property
    def is_confirmed(self) -> bool:
        """Проверяет, подтвержден ли реферал"""
        return self.status == "confirmed"
    
    @property
    def is_pending(self) -> bool:
        """Проверяет, ожидает ли реферал подтверждения"""
        return self.status == "pending"
    
    def confirm(self, reward_amount: Optional[Decimal] = None):
        """Подтверждает реферала и устанавливает вознаграждение"""
        self.status = "confirmed"
        self.confirmed_at = datetime.utcnow()
        if reward_amount:
            self.reward_amount = reward_amount
    
    def mark_rewarded(self):
        """Отмечает, что вознаграждение выплачено"""
        self.is_rewarded = True
        self.rewarded_at = datetime.utcnow()
        self.status = "rewarded"


class ReferralSettings(Base):
    """Настройки реферальной системы"""
    __tablename__ = "referral_settings"
    
    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    
    # Включена ли реферальная система
    is_enabled: Mapped[bool] = Column(Boolean, default=True)
    
    # Тип вознаграждения: fixed (фиксированная сумма) или percentage (процент от платежа)
    reward_type: Mapped[str] = Column(String(20), default="fixed")
    
    # Размер вознаграждения
    reward_amount: Mapped[Decimal] = Column(Numeric(10, 2), default=Decimal("100.00"))
    
    # Процент от платежа (если reward_type = percentage)
    reward_percentage: Mapped[Optional[Decimal]] = Column(Numeric(5, 2), nullable=True)
    
    # Минимальная сумма платежа для получения вознаграждения
    min_payment_amount: Mapped[Decimal] = Column(Numeric(10, 2), default=Decimal("0.00"))
    
    # Максимальное количество рефералов от одного пользователя
    max_referrals_per_user: Mapped[int] = Column(Integer, default=100)
    
    # Срок действия реферального кода (в днях)
    referral_code_expiry_days: Mapped[int] = Column(Integer, default=30)
    
    # Условие для получения вознаграждения
    reward_condition: Mapped[str] = Column(String(50), default="first_payment")  # first_payment, subscription_active
    
    # Дата создания настроек
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow)
    
    # Дата последнего обновления
    updated_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ReferralSettings(id={self.id}, reward_type={self.reward_type}, reward_amount={self.reward_amount})>" 