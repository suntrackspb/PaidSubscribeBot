"""
Модель платежа для PaidSubscribeBot.
Содержит информацию о всех платежных операциях.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Numeric, Text
from sqlalchemy.orm import relationship

from app.config.database import Base


class PaymentStatus(str, Enum):
    """Статусы платежа"""
    PENDING = "pending"        # Ожидает оплаты
    PROCESSING = "processing"  # В процессе обработки
    COMPLETED = "completed"    # Завершен успешно
    FAILED = "failed"         # Не удался
    CANCELED = "canceled"     # Отменен
    REFUNDED = "refunded"     # Возвращен


class PaymentMethod(str, Enum):
    """Методы оплаты"""
    YOOMONEY = "yoomoney"           # YooMoney
    TELEGRAM_STARS = "telegram_stars"  # Telegram Stars
    SBP = "sbp"                     # Система быстрых платежей
    BANK_CARD = "bank_card"         # Банковская карта
    CRYPTO = "crypto"               # Криптовалюта
    MANUAL = "manual"               # Ручное начисление администратором


class Payment(Base):
    """
    Модель платежа пользователя.
    
    Attributes:
        id: Уникальный ID платежа
        user_id: ID пользователя (FK to users.telegram_id)
        subscription_id: ID подписки (FK, опционально)
        external_id: ID платежа в внешней системе
        method: Метод оплаты
        status: Статус платежа
        amount: Сумма платежа
        currency: Валюта платежа
        description: Описание платежа
        created_at: Дата создания
        updated_at: Дата последнего обновления
        completed_at: Дата завершения
        failed_at: Дата неудачи
        payment_metadata: Дополнительные данные платежа
        failure_reason: Причина неудачи
        webhook_data: Данные от webhook
    """
    
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True, index=True)
    
    # Данные платежа
    external_id = Column(String(255), nullable=True, index=True)  # ID в платежной системе
    method = Column(SQLEnum(PaymentMethod), nullable=False)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    
    # Финансовые данные
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="RUB", nullable=False)
    
    # Описание
    description = Column(String(255), nullable=True)
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    
    # Дополнительные данные
    payment_metadata = Column(Text, nullable=True)  # JSON данные
    failure_reason = Column(String(500), nullable=True)
    webhook_data = Column(Text, nullable=True)  # Данные от webhook'а
    
    # Связи с другими таблицами
    user = relationship("User", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payment")
    promo_code_usage = relationship("PromoCodeUsage", back_populates="payment", uselist=False)
    
    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, user_id={self.user_id}, amount={self.amount}, status={self.status})>"
    
    @property
    def is_successful(self) -> bool:
        """Проверка успешности платежа"""
        return self.status == PaymentStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Проверка неудачности платежа"""
        return self.status in [PaymentStatus.FAILED, PaymentStatus.CANCELED]
    
    @property
    def is_pending(self) -> bool:
        """Проверка ожидания платежа"""
        return self.status in [PaymentStatus.PENDING, PaymentStatus.PROCESSING]
    
    @property
    def amount_rub(self) -> float:
        """Сумма платежа в рублях"""
        if self.currency == "RUB":
            return float(self.amount)
        # Здесь можно добавить конвертацию валют
        return float(self.amount)
    
    def complete(self, external_id: str = None, webhook_data: str = None):
        """
        Завершение платежа успешно.
        
        Args:
            external_id: ID платежа в внешней системе
            webhook_data: Данные от webhook'а
        """
        self.status = PaymentStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        if external_id:
            self.external_id = external_id
        if webhook_data:
            self.webhook_data = webhook_data
    
    def fail(self, reason: str = None, webhook_data: str = None):
        """
        Отметка платежа как неудачного.
        
        Args:
            reason: Причина неудачи
            webhook_data: Данные от webhook'а
        """
        self.status = PaymentStatus.FAILED
        self.failed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        if reason:
            self.failure_reason = reason
        if webhook_data:
            self.webhook_data = webhook_data
    
    def cancel(self, reason: str = None):
        """
        Отмена платежа.
        
        Args:
            reason: Причина отмены
        """
        self.status = PaymentStatus.CANCELED
        self.updated_at = datetime.utcnow()
        
        if reason:
            self.failure_reason = reason
    
    def set_processing(self):
        """Установка статуса обработки"""
        self.status = PaymentStatus.PROCESSING
        self.updated_at = datetime.utcnow()
    
    def refund(self, reason: str = None):
        """
        Возврат платежа.
        
        Args:
            reason: Причина возврата
        """
        self.status = PaymentStatus.REFUNDED
        self.updated_at = datetime.utcnow()
        
        if reason:
            self.failure_reason = reason
    
    def to_dict(self) -> dict:
        """Преобразование объекта в словарь"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "subscription_id": self.subscription_id,
            "external_id": self.external_id,
            "method": self.method.value,
            "status": self.status.value,
            "amount": float(self.amount),
            "currency": self.currency,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "failed_at": self.failed_at.isoformat() if self.failed_at else None,
            "failure_reason": self.failure_reason,
            "is_successful": self.is_successful,
            "is_failed": self.is_failed,
            "is_pending": self.is_pending,
            "amount_rub": self.amount_rub,
        } 