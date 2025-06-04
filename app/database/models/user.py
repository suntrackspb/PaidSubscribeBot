"""
Модель пользователя для PaidSubscribeBot.
Содержит информацию о пользователях Telegram бота.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship

from app.config.database import Base


class User(Base):
    """
    Модель пользователя Telegram бота.
    
    Attributes:
        telegram_id: Telegram ID пользователя (первичный ключ)
        username: Имя пользователя в Telegram (без @)
        first_name: Имя пользователя
        last_name: Фамилия пользователя
        language_code: Код языка пользователя
        is_active: Активен ли пользователь
        is_admin: Является ли пользователь администратором
        is_banned: Заблокирован ли пользователь
        created_at: Дата регистрации
        updated_at: Дата последнего обновления
        last_activity_at: Дата последней активности
        referrer_id: ID пользователя, который пригласил этого пользователя
        notes: Заметки администратора о пользователе
    """
    
    __tablename__ = "users"
    
    telegram_id = Column(Integer, primary_key=True, index=True)  # Telegram ID как первичный ключ
    username = Column(String(50), nullable=True, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    language_code = Column(String(10), default="ru")
    
    # Статусы пользователя
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    
    # Реферальная система
    referrer_id = Column(Integer, nullable=True, index=True)
    
    # Дополнительная информация
    notes = Column(Text, nullable=True)
    
    # Связи с другими таблицами
    subscriptions = relationship(
        "Subscription", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    payments = relationship(
        "Payment", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    
    # Реферальные связи
    referrals_made = relationship(
        "Referral",
        foreign_keys="Referral.referrer_id",
        back_populates="referrer",
        cascade="all, delete-orphan"
    )
    referral_info = relationship(
        "Referral",
        foreign_keys="Referral.referred_id",
        back_populates="referred",
        uselist=False  # Один пользователь может быть приглашен только один раз
    )
    
    # Промокоды
    personal_promo_codes = relationship(
        "PromoCode",
        foreign_keys="PromoCode.user_telegram_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    promo_code_usages = relationship("PromoCodeUsage", back_populates="user", cascade="all, delete-orphan")
    
    # Уведомления
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    notification_settings = relationship(
        "NotificationSettings", 
        back_populates="user", 
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    @property
    def id(self) -> int:
        """Псевдоним для telegram_id для обратной совместимости"""
        return self.telegram_id
    
    @property
    def last_activity(self) -> datetime:
        """Псевдоним для last_activity_at для обратной совместимости"""
        return self.last_activity_at
    
    def __repr__(self) -> str:
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"
    
    @property
    def full_name(self) -> str:
        """Получение полного имени пользователя"""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) if parts else self.username or f"User {self.telegram_id}"
    
    @property
    def display_name(self) -> str:
        """Получение отображаемого имени для пользователя"""
        if self.username:
            return f"@{self.username}"
        return self.full_name
    
    def update_activity(self):
        """Обновление времени последней активности"""
        self.last_activity_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Преобразование объекта в словарь"""
        return {
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "language_code": self.language_code,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "is_banned": self.is_banned,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "referrer_id": self.referrer_id,
            "full_name": self.full_name,
            "display_name": self.display_name,
        } 