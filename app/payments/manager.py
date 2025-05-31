"""
Менеджер платежных систем для PaidSubscribeBot.
Управляет всеми платежными провайдерами и обеспечивает единый интерфейс.
"""

from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal

from app.payments.base import (
    BasePaymentProvider,
    PaymentRequest,
    PaymentResponse,
    PaymentStatusData,
    PaymentProviderError,
)
from app.payments.yoomoney_provider import YooMoneyProvider
from app.payments.telegram_stars_provider import TelegramStarsProvider
from app.payments.sbp_provider import SBPProvider
from app.database.models.payment import PaymentMethod, PaymentStatus
from app.config.settings import settings
from app.utils.logger import get_logger


class PaymentManager:
    """
    Менеджер платежных систем.
    
    Обеспечивает:
    - Инициализацию всех провайдеров
    - Единый интерфейс для работы с платежами
    - Автоматический выбор доступных провайдеров
    - Обработку webhook'ов от разных систем
    """
    
    def __init__(self):
        self.logger = get_logger("payments.manager")
        self._providers: Dict[PaymentMethod, BasePaymentProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self) -> None:
        """Инициализация всех платежных провайдеров"""
        try:
            # YooMoney
            if hasattr(settings, 'YOOMONEY_RECEIVER') and settings.YOOMONEY_RECEIVER:
                try:
                    yoomoney_config = {
                        "receiver": settings.YOOMONEY_RECEIVER,
                        "secret_key": getattr(settings, 'YOOMONEY_SECRET_KEY', ''),
                    }
                    provider = YooMoneyProvider(yoomoney_config)
                    if provider.is_enabled:
                        self._providers[PaymentMethod.YOOMONEY] = provider
                        self.logger.info("YooMoney провайдер инициализирован")
                except Exception as e:
                    self.logger.error("Ошибка инициализации YooMoney", error=str(e))
            
            # Telegram Stars
            if hasattr(settings, 'BOT_TOKEN') and settings.BOT_TOKEN:
                try:
                    stars_config = {
                        "bot_token": settings.BOT_TOKEN,
                        "stars_rate": getattr(settings, 'TELEGRAM_STARS_RATE', 100),
                    }
                    provider = TelegramStarsProvider(stars_config)
                    if provider.is_enabled:
                        self._providers[PaymentMethod.TELEGRAM_STARS] = provider
                        self.logger.info("Telegram Stars провайдер инициализирован")
                except Exception as e:
                    self.logger.error("Ошибка инициализации Telegram Stars", error=str(e))
            
            # СБП
            sbp_merchant_id = getattr(settings, 'SBP_MERCHANT_ID', '')
            sbp_phone = getattr(settings, 'SBP_PHONE_NUMBER', '')
            
            if sbp_merchant_id or sbp_phone:
                try:
                    sbp_config = {
                        "merchant_id": sbp_merchant_id,
                        "bank_id": getattr(settings, 'SBP_BANK_ID', ''),
                        "api_url": getattr(settings, 'SBP_API_URL', ''),
                        "secret_key": getattr(settings, 'SBP_SECRET_KEY', ''),
                        "phone_number": sbp_phone,
                        "qr_size": getattr(settings, 'SBP_QR_SIZE', 300),
                        "qr_border": getattr(settings, 'SBP_QR_BORDER', 4),
                    }
                    provider = SBPProvider(sbp_config)
                    if provider.is_enabled:
                        self._providers[PaymentMethod.SBP] = provider
                        self.logger.info("СБП провайдер инициализирован")
                except Exception as e:
                    self.logger.error("Ошибка инициализации СБП", error=str(e))
            
            self.logger.info(
                "Менеджер платежей инициализирован",
                enabled_providers=[method.value for method in self._providers.keys()]
            )
            
        except Exception as e:
            self.logger.error("Критическая ошибка инициализации платежных провайдеров", error=str(e))
    
    def get_available_methods(self) -> List[PaymentMethod]:
        """
        Получение списка доступных методов оплаты.
        
        Returns:
            List[PaymentMethod]: Список доступных методов
        """
        return list(self._providers.keys())
    
    def get_provider(self, method: PaymentMethod) -> Optional[BasePaymentProvider]:
        """
        Получение провайдера по методу оплаты.
        
        Args:
            method: Метод оплаты
            
        Returns:
            Optional[BasePaymentProvider]: Провайдер или None
        """
        return self._providers.get(method)
    
    def is_method_available(self, method: PaymentMethod) -> bool:
        """
        Проверка доступности метода оплаты.
        
        Args:
            method: Метод оплаты
            
        Returns:
            bool: True если метод доступен
        """
        provider = self._providers.get(method)
        return provider is not None and provider.is_enabled
    
    async def create_payment(self, method: PaymentMethod, request: PaymentRequest) -> PaymentResponse:
        """
        Создание платежа через указанный метод.
        
        Args:
            method: Метод оплаты
            request: Запрос на создание платежа
            
        Returns:
            PaymentResponse: Ответ с данными о платеже
            
        Raises:
            PaymentProviderError: Ошибка создания платежа
        """
        provider = self._providers.get(method)
        if not provider:
            raise PaymentProviderError(f"Метод оплаты {method.value} недоступен")
        
        if not provider.is_enabled:
            raise PaymentProviderError(f"Провайдер {provider.name} отключен")
        
        # Валидируем сумму платежа
        min_amount = provider.get_min_amount(request.currency)
        max_amount = provider.get_max_amount(request.currency)
        
        if request.amount < min_amount:
            raise PaymentProviderError(
                f"Минимальная сумма для {provider.name}: {provider.format_amount(min_amount)}"
            )
        
        if request.amount > max_amount:
            raise PaymentProviderError(
                f"Максимальная сумма для {provider.name}: {provider.format_amount(max_amount)}"
            )
        
        # Проверяем поддержку валюты
        if request.currency not in provider.get_supported_currencies():
            raise PaymentProviderError(
                f"Валюта {request.currency} не поддерживается провайдером {provider.name}"
            )
        
        self.logger.info(
            "Создание платежа",
            method=method.value,
            amount=float(request.amount),
            currency=request.currency,
            user_id=request.user_id
        )
        
        return await provider.create_payment(request)
    
    async def check_payment_status(self, method: PaymentMethod, payment_id: str) -> PaymentStatusData:
        """
        Проверка статуса платежа.
        
        Args:
            method: Метод оплаты
            payment_id: ID платежа
            
        Returns:
            PaymentStatusData: Статус платежа
            
        Raises:
            PaymentProviderError: Ошибка проверки статуса
        """
        provider = self._providers.get(method)
        if not provider:
            raise PaymentProviderError(f"Метод оплаты {method.value} недоступен")
        
        return await provider.check_payment_status(payment_id)
    
    async def cancel_payment(self, method: PaymentMethod, payment_id: str) -> bool:
        """
        Отмена платежа.
        
        Args:
            method: Метод оплаты
            payment_id: ID платежа
            
        Returns:
            bool: True если отмена успешна
            
        Raises:
            PaymentProviderError: Ошибка отмены платежа
        """
        provider = self._providers.get(method)
        if not provider:
            raise PaymentProviderError(f"Метод оплаты {method.value} недоступен")
        
        return await provider.cancel_payment(payment_id)
    
    async def process_webhook(self, method: PaymentMethod, data: Dict[str, Any]) -> Tuple[str, PaymentStatusData]:
        """
        Обработка webhook от платежной системы.
        
        Args:
            method: Метод оплаты
            data: Данные webhook'а
            
        Returns:
            Tuple[str, PaymentStatusData]: ID платежа и его статус
            
        Raises:
            PaymentProviderError: Ошибка обработки webhook'а
        """
        provider = self._providers.get(method)
        if not provider:
            raise PaymentProviderError(f"Метод оплаты {method.value} недоступен")
        
        return await provider.process_webhook(data)
    
    def validate_webhook_signature(self, method: PaymentMethod, data: bytes, signature: str) -> bool:
        """
        Валидация подписи webhook'а.
        
        Args:
            method: Метод оплаты
            data: Сырые данные webhook'а
            signature: Подпись
            
        Returns:
            bool: True если подпись валидна
        """
        provider = self._providers.get(method)
        if not provider:
            return False
        
        return provider.validate_webhook_signature(data, signature)
    
    def get_method_info(self, method: PaymentMethod) -> Optional[Dict[str, Any]]:
        """
        Получение информации о методе оплаты.
        
        Args:
            method: Метод оплаты
            
        Returns:
            Optional[Dict[str, Any]]: Информация о методе
        """
        provider = self._providers.get(method)
        if not provider:
            return None
        
        return {
            "name": provider.name,
            "method": method.value,
            "is_enabled": provider.is_enabled,
            "supported_currencies": provider.get_supported_currencies(),
            "min_amount": {
                currency: float(provider.get_min_amount(currency))
                for currency in provider.get_supported_currencies()
            },
            "max_amount": {
                currency: float(provider.get_max_amount(currency))
                for currency in provider.get_supported_currencies()
            },
        }
    
    def get_all_methods_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Получение информации о всех доступных методах оплаты.
        
        Returns:
            Dict[str, Dict[str, Any]]: Информация о всех методах
        """
        return {
            method.value: self.get_method_info(method)
            for method in self._providers.keys()
        }
    
    def format_amount_for_method(self, method: PaymentMethod, amount: Decimal, currency: str = "RUB") -> str:
        """
        Форматирование суммы для отображения в указанном методе.
        
        Args:
            method: Метод оплаты
            amount: Сумма
            currency: Валюта
            
        Returns:
            str: Отформатированная сумма
        """
        provider = self._providers.get(method)
        if not provider:
            return f"{amount:,.2f} {currency}"
        
        return provider.format_amount(amount, currency)
    
    async def cleanup(self) -> None:
        """Очистка ресурсов всех провайдеров"""
        for provider in self._providers.values():
            if hasattr(provider, '__aexit__'):
                try:
                    await provider.__aexit__(None, None, None)
                except Exception as e:
                    self.logger.error(
                        "Ошибка очистки провайдера",
                        provider=provider.name,
                        error=str(e)
                    )
        
        self.logger.info("Менеджер платежей очищен")


# Глобальный экземпляр менеджера платежей
payment_manager = PaymentManager() 