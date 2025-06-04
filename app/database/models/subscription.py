"""
Модель подписки для PaidSubscribeBot.
Содержит информацию о подписках пользователей на каналы.
"""

from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum as SQLEnum, Numeric
from sqlalchemy.orm import relationship

from app.config.database import Base


class SubscriptionStatus(str, Enum):
    """Статусы подписки"""
    ACTIVE = "active"          # Активная подписка
    EXPIRED = "expired"        # Истекшая подписка
    CANCELLED = "cancelled"    # Отмененная подписка
    TRIAL = "trial"           # Пробная подписка
    PENDING = "pending"        # Ожидающая активации


class SubscriptionDuration(str, Enum):
    """Длительность подписки"""
    MONTHLY = "monthly"        # Месячная подписка
    YEARLY = "yearly"         # Годовая подписка
    TRIAL = "trial"           # Пробная подписка


class Subscription(Base):
    """
    Модель подписки пользователя на канал.
    
    Attributes:
        id: Уникальный ID подписки
        user_id: ID пользователя (FK to users.telegram_id)
        channel_id: ID канала (FK)
        status: Статус подписки
        price: Стоимость подписки
        duration_days: Длительность подписки в днях
        starts_at: Дата начала подписки
        expires_at: Дата окончания подписки
        is_active: Активна ли подписка
        activated_at: Дата активации
        cancelled_at: Дата отмены
        payment_id: ID связанного платежа
        created_at: Дата создания
        updated_at: Дата последнего обновления
        notes: Заметки администратора
    """
    
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=False, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False, index=True)
    
    # Статус и параметры подписки
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.PENDING, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    duration_days = Column(Integer, nullable=False)
    
    # Временные рамки
    starts_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Статус активности
    is_active = Column(Boolean, default=False)
    
    # Метки времени
    activated_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связанный платеж
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    
    # Дополнительная информация
    notes = Column(String(500), nullable=True)
    
    # Связи с другими таблицами
    user = relationship("User", back_populates="subscriptions")
    channel = relationship("Channel", back_populates="subscriptions")
    payment = relationship("Payment", back_populates="subscription")
    
    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, user_id={self.user_id}, status={self.status})>"
    
    @property
    def is_expired(self) -> bool:
        """Проверка истечения подписки"""
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        return False
    
    @property
    def days_left(self) -> int:
        """Количество дней до окончания подписки"""
        if not self.expires_at:
            return 0
        
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)
    
    @property
    def hours_left(self) -> int:
        """Количество часов до окончания подписки"""
        if not self.expires_at:
            return 0
        
        delta = self.expires_at - datetime.utcnow()
        return max(0, int(delta.total_seconds() // 3600))
    
    def activate(self):
        """Активация подписки"""
        self.status = SubscriptionStatus.ACTIVE
        self.is_active = True
        self.activated_at = datetime.utcnow()
        self.starts_at = datetime.utcnow()
        
        if not self.expires_at and self.duration_days:
            self.expires_at = self.starts_at + timedelta(days=self.duration_days)
        
        self.updated_at = datetime.utcnow()
    
    def cancel(self, reason: str = None):
        """Отмена подписки"""
        self.status = SubscriptionStatus.CANCELLED
        self.is_active = False
        self.cancelled_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        if reason:
            self.notes = reason
    
    def expire(self):
        """Установка статуса истекшей подписки"""
        self.status = SubscriptionStatus.EXPIRED
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Преобразование объекта в словарь"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "status": self.status.value,
            "price": float(self.price) if self.price else None,
            "duration_days": self.duration_days,
            "starts_at": self.starts_at.isoformat() if self.starts_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "payment_id": self.payment_id,
            "days_left": self.days_left,
            "hours_left": self.hours_left,
            "is_expired": self.is_expired,
            "notes": self.notes,
        } 