"""
Модели для системы уведомлений.
Поддерживает различные типы уведомлений и шаблоны сообщений.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.config.database import Base


class NotificationType(str, Enum):
    """Типы уведомлений"""
    SUBSCRIPTION_EXPIRING = "subscription_expiring"       # Истекает подписка
    SUBSCRIPTION_EXPIRED = "subscription_expired"         # Подписка истекла
    PAYMENT_SUCCESS = "payment_success"                   # Успешная оплата
    PAYMENT_FAILED = "payment_failed"                     # Неудачная оплата
    REFERRAL_REWARD = "referral_reward"                   # Реферальное вознаграждение
    PROMO_CODE_AVAILABLE = "promo_code_available"         # Доступен промокод
    WELCOME_MESSAGE = "welcome_message"                   # Приветственное сообщение
    BROADCAST = "broadcast"                               # Массовая рассылка
    ADMIN_ALERT = "admin_alert"                          # Уведомление администратора
    SYSTEM_MAINTENANCE = "system_maintenance"             # Техническое обслуживание


class NotificationStatus(str, Enum):
    """Статусы уведомлений"""
    PENDING = "pending"        # Ожидает отправки
    SENT = "sent"             # Отправлено
    DELIVERED = "delivered"    # Доставлено
    FAILED = "failed"         # Не удалось отправить
    CANCELLED = "cancelled"    # Отменено


class NotificationPriority(str, Enum):
    """Приоритеты уведомлений"""
    LOW = "low"               # Низкий приоритет
    NORMAL = "normal"         # Обычный приоритет
    HIGH = "high"            # Высокий приоритет
    URGENT = "urgent"        # Срочное уведомление


class NotificationTemplate(Base):
    """
    Модель шаблона уведомления.
    Хранит шаблоны сообщений для различных типов уведомлений.
    """
    __tablename__ = "notification_templates"

    id = Column(Integer, primary_key=True, index=True)
    
    # Основные поля
    name = Column(String(100), nullable=False, comment="Название шаблона")
    type = Column(SQLEnum(NotificationType), nullable=False, index=True, comment="Тип уведомления")
    
    # Содержимое
    title = Column(String(200), nullable=True, comment="Заголовок сообщения")
    message = Column(Text, nullable=False, comment="Текст сообщения (поддерживает переменные)")
    
    # Настройки
    is_active = Column(Boolean, default=True, nullable=False, comment="Активен ли шаблон")
    priority = Column(SQLEnum(NotificationPriority), default=NotificationPriority.NORMAL, nullable=False)
    
    # Параметры отправки
    delay_seconds = Column(Integer, default=0, nullable=False, comment="Задержка перед отправкой (сек)")
    retry_count = Column(Integer, default=3, nullable=False, comment="Количество попыток отправки")
    
    # Условия отправки
    conditions = Column(JSON, nullable=True, comment="Условия для отправки уведомления")
    
    # Системные поля
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(20), ForeignKey("users.telegram_id"), nullable=True)
    
    # Отношения
    notifications = relationship("Notification", back_populates="template", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<NotificationTemplate(name='{self.name}', type='{self.type.value}')>"

    def render_message(self, variables: Dict[str, Any]) -> str:
        """
        Рендеринг сообщения с подстановкой переменных.
        
        Args:
            variables: Словарь переменных для подстановки
            
        Returns:
            Готовое сообщение с подставленными значениями
        """
        try:
            return self.message.format(**variables)
        except KeyError as e:
            # Если переменная не найдена, возвращаем исходный текст
            return self.message
        except Exception:
            return self.message


class Notification(Base):
    """
    Модель уведомления.
    Представляет конкретное уведомление для пользователя.
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    
    # Связи
    user_telegram_id = Column(String(20), ForeignKey("users.telegram_id"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("notification_templates.id"), nullable=True)
    
    # Основные поля
    type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    priority = Column(SQLEnum(NotificationPriority), default=NotificationPriority.NORMAL, nullable=False)
    
    # Содержимое
    title = Column(String(200), nullable=True)
    message = Column(Text, nullable=False, comment="Готовое сообщение для отправки")
    
    # Статус и обработка
    status = Column(SQLEnum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False, index=True)
    
    # Планирование
    scheduled_at = Column(DateTime, nullable=True, comment="Запланированное время отправки")
    sent_at = Column(DateTime, nullable=True, comment="Время отправки")
    delivered_at = Column(DateTime, nullable=True, comment="Время доставки")
    
    # Обработка ошибок
    attempts = Column(Integer, default=0, nullable=False, comment="Количество попыток отправки")
    max_attempts = Column(Integer, default=3, nullable=False, comment="Максимум попыток")
    error_message = Column(Text, nullable=True, comment="Сообщение об ошибке")
    
    # Дополнительные данные
    extra_data = Column(JSON, nullable=True, comment="Дополнительные данные уведомления")
    
    # Системные поля
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Отношения
    user = relationship("User", back_populates="notifications")
    template = relationship("NotificationTemplate", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(id={self.id}, type='{self.type.value}', status='{self.status.value}')>"

    @property
    def is_pending(self) -> bool:
        """Проверяет, ожидает ли уведомление отправки"""
        return self.status == NotificationStatus.PENDING

    @property
    def can_retry(self) -> bool:
        """Проверяет, можно ли повторить отправку"""
        return self.attempts < self.max_attempts and self.status == NotificationStatus.FAILED

    @property
    def is_scheduled(self) -> bool:
        """Проверяет, запланировано ли уведомление на будущее"""
        if not self.scheduled_at:
            return False
        return self.scheduled_at > datetime.utcnow()

    def mark_sent(self, telegram_message_id: Optional[int] = None):
        """Отметить уведомление как отправленное"""
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        if telegram_message_id and self.extra_data:
            self.extra_data["telegram_message_id"] = telegram_message_id
        elif telegram_message_id:
            self.extra_data = {"telegram_message_id": telegram_message_id}

    def mark_delivered(self):
        """Отметить уведомление как доставленное"""
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_failed(self, error_message: str):
        """Отметить уведомление как неудачное"""
        self.status = NotificationStatus.FAILED
        self.error_message = error_message
        self.attempts += 1
        self.updated_at = datetime.utcnow()

    def cancel(self):
        """Отменить уведомление"""
        self.status = NotificationStatus.CANCELLED
        self.updated_at = datetime.utcnow()


class NotificationSettings(Base):
    """
    Настройки уведомлений пользователя.
    Определяет, какие уведомления пользователь хочет получать.
    """
    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_telegram_id = Column(String(20), ForeignKey("users.telegram_id"), nullable=False, unique=True, index=True)
    
    # Настройки типов уведомлений
    subscription_notifications = Column(Boolean, default=True, nullable=False, comment="Уведомления о подписке")
    payment_notifications = Column(Boolean, default=True, nullable=False, comment="Уведомления о платежах")
    referral_notifications = Column(Boolean, default=True, nullable=False, comment="Реферальные уведомления")
    promo_notifications = Column(Boolean, default=True, nullable=False, comment="Уведомления о промокодах")
    broadcast_notifications = Column(Boolean, default=True, nullable=False, comment="Общие рассылки")
    
    # Настройки времени
    quiet_hours_start = Column(Integer, nullable=True, comment="Начало тихих часов (час 0-23)")
    quiet_hours_end = Column(Integer, nullable=True, comment="Конец тихих часов (час 0-23)")
    timezone = Column(String(50), default="UTC", nullable=False, comment="Часовой пояс пользователя")
    
    # Системные поля
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Отношения
    user = relationship("User", back_populates="notification_settings")

    def __repr__(self):
        return f"<NotificationSettings(user_id={self.user_telegram_id})>"

    def is_type_enabled(self, notification_type: NotificationType) -> bool:
        """Проверяет, включен ли определенный тип уведомлений"""
        type_mapping = {
            NotificationType.SUBSCRIPTION_EXPIRING: self.subscription_notifications,
            NotificationType.SUBSCRIPTION_EXPIRED: self.subscription_notifications,
            NotificationType.PAYMENT_SUCCESS: self.payment_notifications,
            NotificationType.PAYMENT_FAILED: self.payment_notifications,
            NotificationType.REFERRAL_REWARD: self.referral_notifications,
            NotificationType.PROMO_CODE_AVAILABLE: self.promo_notifications,
            NotificationType.BROADCAST: self.broadcast_notifications,
            NotificationType.WELCOME_MESSAGE: True,  # Всегда включено
            NotificationType.ADMIN_ALERT: True,     # Всегда включено
            NotificationType.SYSTEM_MAINTENANCE: True,  # Всегда включено
        }
        
        return type_mapping.get(notification_type, True)

    def is_quiet_time(self, current_hour: int) -> bool:
        """Проверяет, находится ли текущее время в тихих часах"""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        start = self.quiet_hours_start
        end = self.quiet_hours_end
        
        if start <= end:
            # Обычный случай: 22:00 - 08:00
            return start <= current_hour <= end
        else:
            # Переход через полночь: 22:00 - 08:00
            return current_hour >= start or current_hour <= end


class BroadcastCampaign(Base):
    """
    Модель кампании массовой рассылки.
    Управляет отправкой сообщений множеству пользователей.
    """
    __tablename__ = "broadcast_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    
    # Основные поля
    name = Column(String(200), nullable=False, comment="Название кампании")
    message = Column(Text, nullable=False, comment="Текст сообщения")
    
    # Целевая аудитория
    target_all_users = Column(Boolean, default=False, nullable=False, comment="Отправить всем пользователям")
    target_active_subscribers = Column(Boolean, default=False, nullable=False, comment="Только активные подписчики")
    target_inactive_users = Column(Boolean, default=False, nullable=False, comment="Только неактивные пользователи")
    target_user_ids = Column(JSON, nullable=True, comment="Конкретные ID пользователей")
    
    # Планирование
    scheduled_at = Column(DateTime, nullable=True, comment="Запланированное время отправки")
    started_at = Column(DateTime, nullable=True, comment="Время начала отправки")
    completed_at = Column(DateTime, nullable=True, comment="Время завершения отправки")
    
    # Статистика
    total_recipients = Column(Integer, default=0, nullable=False, comment="Общее количество получателей")
    sent_count = Column(Integer, default=0, nullable=False, comment="Количество отправленных")
    delivered_count = Column(Integer, default=0, nullable=False, comment="Количество доставленных")
    failed_count = Column(Integer, default=0, nullable=False, comment="Количество неудачных")
    
    # Статус
    is_active = Column(Boolean, default=True, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    
    # Системные поля
    created_at = Column(DateTime, default=func.now(), nullable=False)
    created_by = Column(String(20), ForeignKey("users.telegram_id"), nullable=False)
    
    # Отношения
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<BroadcastCampaign(name='{self.name}', recipients={self.total_recipients})>" 