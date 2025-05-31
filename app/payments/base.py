"""
Базовый класс для платежных провайдеров PaidSubscribeBot.
Определяет общий интерфейс для всех способов оплаты.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass

from app.database.models.payment import PaymentMethod, PaymentStatus


@dataclass
class PaymentRequest:
    """Запрос на создание платежа"""
    amount: Decimal
    currency: str = "RUB"
    description: str = ""
    user_id: int = 0
    subscription_id: Optional[int] = None
    return_url: Optional[str] = None
    webhook_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PaymentResponse:
    """Ответ с данными о платеже"""
    payment_id: str
    status: PaymentStatus
    payment_url: Optional[str] = None
    qr_code_url: Optional[str] = None
    expires_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


@dataclass
class PaymentStatusData:
    """Данные о статусе платежа от провайдера"""
    external_id: str
    status: PaymentStatus
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    paid_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BasePaymentProvider(ABC):
    """
    Базовый класс для всех платежных провайдеров.
    
    Определяет общий интерфейс для создания платежей,
    проверки статуса и обработки webhook'ов.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация провайдера.
        
        Args:
            config: Конфигурация провайдера
        """
        self.config = config
        self._validate_config()
    
    @property
    @abstractmethod
    def method(self) -> PaymentMethod:
        """Метод оплаты провайдера"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Название провайдера"""
        pass
    
    @property
    @abstractmethod
    def is_enabled(self) -> bool:
        """Включен ли провайдер"""
        pass
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Валидация конфигурации провайдера"""
        pass
    
    @abstractmethod
    async def create_payment(self, request: PaymentRequest) -> PaymentResponse:
        """
        Создание платежа.
        
        Args:
            request: Запрос на создание платежа
            
        Returns:
            PaymentResponse: Ответ с данными о платеже
            
        Raises:
            PaymentProviderError: Ошибка создания платежа
        """
        pass
    
    @abstractmethod
    async def check_payment_status(self, payment_id: str) -> PaymentStatusData:
        """
        Проверка статуса платежа.
        
        Args:
            payment_id: ID платежа в системе провайдера
            
        Returns:
            PaymentStatusData: Статус платежа
            
        Raises:
            PaymentProviderError: Ошибка получения статуса
        """
        pass
    
    @abstractmethod
    async def cancel_payment(self, payment_id: str) -> bool:
        """
        Отмена платежа.
        
        Args:
            payment_id: ID платежа в системе провайдера
            
        Returns:
            bool: True если отмена успешна
            
        Raises:
            PaymentProviderError: Ошибка отмены платежа
        """
        pass
    
    @abstractmethod
    async def process_webhook(self, data: Dict[str, Any]) -> Tuple[str, PaymentStatusData]:
        """
        Обработка webhook от провайдера.
        
        Args:
            data: Данные webhook'а
            
        Returns:
            Tuple[str, PaymentStatusData]: ID платежа и его статус
            
        Raises:
            PaymentProviderError: Ошибка обработки webhook'а
        """
        pass
    
    @abstractmethod
    def validate_webhook_signature(self, data: bytes, signature: str) -> bool:
        """
        Валидация подписи webhook'а.
        
        Args:
            data: Сырые данные webhook'а
            signature: Подпись
            
        Returns:
            bool: True если подпись валидна
        """
        pass
    
    def get_supported_currencies(self) -> list[str]:
        """
        Получение списка поддерживаемых валют.
        
        Returns:
            list[str]: Список кодов валют
        """
        return ["RUB"]
    
    def get_min_amount(self, currency: str = "RUB") -> Decimal:
        """
        Минимальная сумма платежа.
        
        Args:
            currency: Валюта
            
        Returns:
            Decimal: Минимальная сумма
        """
        return Decimal("1.00")
    
    def get_max_amount(self, currency: str = "RUB") -> Decimal:
        """
        Максимальная сумма платежа.
        
        Args:
            currency: Валюта
            
        Returns:
            Decimal: Максимальная сумма
        """
        return Decimal("1000000.00")
    
    def format_amount(self, amount: Decimal, currency: str = "RUB") -> str:
        """
        Форматирование суммы для отображения.
        
        Args:
            amount: Сумма
            currency: Валюта
            
        Returns:
            str: Отформатированная сумма
        """
        if currency == "RUB":
            return f"{amount:,.0f} ₽"
        return f"{amount:,.2f} {currency}"


class PaymentProviderError(Exception):
    """Базовое исключение для ошибок платежных провайдеров"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class PaymentNotFoundError(PaymentProviderError):
    """Платеж не найден"""
    pass


class PaymentValidationError(PaymentProviderError):
    """Ошибка валидации данных платежа"""
    pass


class PaymentNetworkError(PaymentProviderError):
    """Сетевая ошибка при работе с API провайдера"""
    pass


class PaymentAuthError(PaymentProviderError):
    """Ошибка аутентификации с API провайдера"""
    pass 