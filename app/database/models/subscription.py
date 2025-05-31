"""
Модель подписки для PaidSubscribeBot.
Содержит информацию о подписках пользователей на каналы.
"""

from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.config.database import Base


class SubscriptionStatus(str, Enum):
    """Статусы подписки"""
    ACTIVE = "active"          # Активная подписка
    EXPIRED = "expired"        # Истекшая подписка
    CANCELED = "canceled"      # Отмененная подписка
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
        user_id: ID пользователя (FK)
        channel_id: ID канала (FK)
        status: Статус подписки
        duration: Длительность подписки
        start_date: Дата начала подписки
        end_date: Дата окончания подписки
        auto_renewal: Автоматическое продление
        created_at: Дата создания
        updated_at: Дата последнего обновления
        canceled_at: Дата отмены
        notes: Заметки администратора
    """
    
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False, index=True)
    
    # Статус и параметры подписки
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.PENDING, nullable=False)
    duration = Column(SQLEnum(SubscriptionDuration), nullable=False)
    
    # Временные рамки
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    
    # Настройки
    auto_renewal = Column(Boolean, default=False)
    
    # Метки времени
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    canceled_at = Column(DateTime, nullable=True)
    
    # Дополнительная информация
    notes = Column(String(500), nullable=True)
    
    # Связи с другими таблицами
    user = relationship("User", back_populates="subscriptions")
    channel = relationship("Channel", back_populates="subscriptions")
    payments = relationship(
        "Payment", 
        back_populates="subscription",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, user_id={self.user_id}, status={self.status})>"
    
    @property
    def is_active(self) -> bool:
        """Проверка активности подписки"""
        if self.status not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]:
            return False
        
        if self.end_date and datetime.utcnow() > self.end_date:
            return False
            
        return True
    
    @property
    def is_expired(self) -> bool:
        """Проверка истечения подписки"""
        if self.end_date and datetime.utcnow() > self.end_date:
            return True
        return False
    
    @property
    def days_left(self) -> int:
        """Количество дней до окончания подписки"""
        if not self.end_date:
            return 0
        
        delta = self.end_date - datetime.utcnow()
        return max(0, delta.days)
    
    @property
    def hours_left(self) -> int:
        """Количество часов до окончания подписки"""
        if not self.end_date:
            return 0
        
        delta = self.end_date - datetime.utcnow()
        return max(0, int(delta.total_seconds() // 3600))
    
    def activate(self, duration_days: int = None):
        """
        Активация подписки.
        
        Args:
            duration_days: Количество дней подписки (если не указано, берется из типа)
        """
        self.status = SubscriptionStatus.ACTIVE
        self.start_date = datetime.utcnow()
        
        if duration_days is None:
            # Определяем длительность по типу подписки
            duration_map = {
                SubscriptionDuration.TRIAL: 3,
                SubscriptionDuration.MONTHLY: 30,
                SubscriptionDuration.YEARLY: 365,
            }
            duration_days = duration_map.get(self.duration, 30)
        
        self.end_date = self.start_date + timedelta(days=duration_days)
        self.updated_at = datetime.utcnow()
    
    def extend(self, days: int):
        """
        Продление подписки на указанное количество дней.
        
        Args:
            days: Количество дней для продления
        """
        if not self.end_date:
            self.end_date = datetime.utcnow()
        
        self.end_date += timedelta(days=days)
        self.updated_at = datetime.utcnow()
        
        # Если подписка была истекшей, активируем её
        if self.status == SubscriptionStatus.EXPIRED:
            self.status = SubscriptionStatus.ACTIVE
    
    def cancel(self, reason: str = None):
        """
        Отмена подписки.
        
        Args:
            reason: Причина отмены
        """
        self.status = SubscriptionStatus.CANCELED
        self.canceled_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        if reason:
            self.notes = reason
    
    def expire(self):
        """Установка статуса истекшей подписки"""
        self.status = SubscriptionStatus.EXPIRED
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Преобразование объекта в словарь"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "status": self.status.value,
            "duration": self.duration.value,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "auto_renewal": self.auto_renewal,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "canceled_at": self.canceled_at.isoformat() if self.canceled_at else None,
            "notes": self.notes,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
            "days_left": self.days_left,
            "hours_left": self.hours_left,
        } 