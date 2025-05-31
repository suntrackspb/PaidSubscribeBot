"""
Модель канала для PaidSubscribeBot.
Содержит информацию о каналах, к которым продаются подписки.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship

from app.config.database import Base


class Channel(Base):
    """
    Модель канала Telegram.
    
    Attributes:
        id: Уникальный ID канала в базе данных
        telegram_id: ID канала в Telegram
        username: Имя канала (без @)
        title: Название канала
        description: Описание канала
        invite_link: Ссылка-приглашение
        is_active: Активен ли канал
        monthly_price: Цена месячной подписки
        yearly_price: Цена годовой подписки
        trial_enabled: Включена ли пробная подписка
        trial_days: Количество дней пробной подписки
        created_at: Дата создания записи
        updated_at: Дата последнего обновления
    """
    
    __tablename__ = "channels"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String(50), unique=True, nullable=False, index=True)  # ID канала в Telegram
    username = Column(String(50), nullable=True, index=True)  # Имя канала без @
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    invite_link = Column(String(255), nullable=True)
    
    # Настройки канала
    is_active = Column(Boolean, default=True)
    
    # Ценообразование
    monthly_price = Column(Integer, nullable=False, default=499)  # В копейках
    yearly_price = Column(Integer, nullable=False, default=4990)  # В копейках
    
    # Пробная подписка
    trial_enabled = Column(Boolean, default=True)
    trial_days = Column(Integer, default=3)
    
    # Метки времени
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи с другими таблицами
    subscriptions = relationship(
        "Subscription", 
        back_populates="channel",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Channel(id={self.id}, telegram_id={self.telegram_id}, title={self.title})>"
    
    @property
    def monthly_price_rub(self) -> float:
        """Цена месячной подписки в рублях"""
        return self.monthly_price / 100
    
    @property
    def yearly_price_rub(self) -> float:
        """Цена годовой подписки в рублях"""
        return self.yearly_price / 100
    
    @property
    def channel_link(self) -> str:
        """Ссылка на канал"""
        if self.username:
            return f"https://t.me/{self.username}"
        return self.invite_link or ""
    
    @property
    def display_name(self) -> str:
        """Отображаемое имя канала"""
        return f"@{self.username}" if self.username else self.title
    
    def get_price(self, duration: str) -> int:
        """
        Получение цены подписки по длительности.
        
        Args:
            duration: Длительность подписки (monthly, yearly)
            
        Returns:
            int: Цена в копейках
        """
        if duration == "monthly":
            return self.monthly_price
        elif duration == "yearly":
            return self.yearly_price
        else:
            return self.monthly_price
    
    def get_price_rub(self, duration: str) -> float:
        """
        Получение цены подписки в рублях по длительности.
        
        Args:
            duration: Длительность подписки (monthly, yearly)
            
        Returns:
            float: Цена в рублях
        """
        return self.get_price(duration) / 100
    
    def activate(self):
        """Активация канала"""
        self.is_active = True
        self.updated_at = datetime.utcnow()
    
    def deactivate(self):
        """Деактивация канала"""
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def update_prices(self, monthly_price: int = None, yearly_price: int = None):
        """
        Обновление цен на подписки.
        
        Args:
            monthly_price: Новая цена месячной подписки в копейках
            yearly_price: Новая цена годовой подписки в копейках
        """
        if monthly_price is not None:
            self.monthly_price = monthly_price
        if yearly_price is not None:
            self.yearly_price = yearly_price
        
        self.updated_at = datetime.utcnow()
    
    def enable_trial(self, days: int = 3):
        """
        Включение пробной подписки.
        
        Args:
            days: Количество дней пробной подписки
        """
        self.trial_enabled = True
        self.trial_days = days
        self.updated_at = datetime.utcnow()
    
    def disable_trial(self):
        """Отключение пробной подписки"""
        self.trial_enabled = False
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Преобразование объекта в словарь"""
        return {
            "id": self.id,
            "telegram_id": self.telegram_id,
            "username": self.username,
            "title": self.title,
            "description": self.description,
            "invite_link": self.invite_link,
            "is_active": self.is_active,
            "monthly_price": self.monthly_price,
            "yearly_price": self.yearly_price,
            "monthly_price_rub": self.monthly_price_rub,
            "yearly_price_rub": self.yearly_price_rub,
            "trial_enabled": self.trial_enabled,
            "trial_days": self.trial_days,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "channel_link": self.channel_link,
            "display_name": self.display_name,
        } 