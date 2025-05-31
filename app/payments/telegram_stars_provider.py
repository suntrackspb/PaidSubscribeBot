"""
Провайдер для интеграции с Telegram Stars.
Поддерживает создание платежей через встроенную систему Telegram.
"""

import json
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple

from aiogram import Bot
from aiogram.types import LabeledPrice

from app.payments.base import (
    BasePaymentProvider,
    PaymentRequest,
    PaymentResponse,
    PaymentStatusData,
    PaymentProviderError,
    PaymentValidationError,
)
from app.database.models.payment import PaymentMethod, PaymentStatus
from app.utils.logger import get_logger


class TelegramStarsProvider(BasePaymentProvider):
    """
    Провайдер для работы с Telegram Stars.
    
    Поддерживает:
    - Создание платежей через Telegram Bot API
    - Автоматическую обработку успешных платежей
    - Работу с внутренней валютой Telegram (Stars)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger("payments.telegram_stars")
        super().__init__(config)
        
        # Настройки Telegram Stars
        self.bot_token = config.get("bot_token")
        self.stars_rate = config.get("stars_rate", 100)  # 1 звезда = 100 рублей
        self.provider_token = ""  # Для Stars токен не нужен
        
        if self.bot_token:
            self.bot = Bot(token=self.bot_token)
        else:
            self.bot = None
    
    @property
    def method(self) -> PaymentMethod:
        return PaymentMethod.TELEGRAM_STARS
    
    @property
    def name(self) -> str:
        return "Telegram Stars"
    
    @property
    def is_enabled(self) -> bool:
        return bool(self.bot_token)
    
    def _validate_config(self) -> None:
        """Валидация конфигурации Telegram Stars"""
        if not self.bot_token:
            raise PaymentValidationError("Telegram bot_token не настроен")
        
        if self.stars_rate <= 0:
            raise PaymentValidationError("Некорректный курс конвертации stars_rate")
    
    def _rub_to_stars(self, rub_amount: Decimal) -> int:
        """
        Конвертация рублей в звезды.
        
        Args:
            rub_amount: Сумма в рублях
            
        Returns:
            int: Количество звезд
        """
        stars = int(rub_amount / self.stars_rate)
        return max(1, stars)  # Минимум 1 звезда
    
    def _stars_to_rub(self, stars: int) -> Decimal:
        """
        Конвертация звезд в рубли.
        
        Args:
            stars: Количество звезд
            
        Returns:
            Decimal: Сумма в рублях
        """
        return Decimal(str(stars * self.stars_rate))
    
    async def create_payment(self, request: PaymentRequest) -> PaymentResponse:
        """
        Создание платежа через Telegram Stars.
        
        Args:
            request: Запрос на создание платежа
            
        Returns:
            PaymentResponse: Ответ с данными о платеже
        """
        try:
            if not self.bot:
                raise PaymentProviderError("Telegram Bot не инициализирован")
            
            # Генерируем уникальный ID платежа
            payment_id = str(uuid.uuid4())
            
            # Конвертируем рубли в звезды
            stars_amount = self._rub_to_stars(request.amount)
            
            self.logger.info(
                "Telegram Stars платеж создается",
                payment_id=payment_id,
                rub_amount=float(request.amount),
                stars_amount=stars_amount,
                user_id=request.user_id
            )
            
            return PaymentResponse(
                payment_id=payment_id,
                status=PaymentStatus.PENDING,
                metadata={
                    "stars_amount": stars_amount,
                    "rub_amount": float(request.amount),
                    "description": request.description,
                    "user_id": request.user_id,
                    "subscription_id": request.subscription_id,
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Ошибка создания Telegram Stars платежа",
                error=str(e),
                user_id=request.user_id,
                amount=float(request.amount)
            )
            raise PaymentProviderError(f"Ошибка создания платежа: {str(e)}")
    
    async def send_invoice_to_user(self, chat_id: int, payment_data: Dict[str, Any]) -> bool:
        """
        Отправка инвойса пользователю в Telegram.
        
        Args:
            chat_id: ID чата пользователя
            payment_data: Данные платежа из metadata
            
        Returns:
            bool: True если инвойс отправлен успешно
        """
        try:
            if not self.bot:
                raise PaymentProviderError("Telegram Bot не инициализирован")
            
            stars_amount = payment_data.get("stars_amount", 1)
            description = payment_data.get("description", "Подписка на канал")
            
            # Создаем инвойс для Telegram Stars
            prices = [LabeledPrice(label="Подписка", amount=stars_amount)]
            
            await self.bot.send_invoice(
                chat_id=chat_id,
                title="Оплата подписки",
                description=description,
                payload=json.dumps({
                    "payment_id": payment_data.get("payment_id"),
                    "user_id": payment_data.get("user_id"),
                    "subscription_id": payment_data.get("subscription_id"),
                }),
                provider_token="",  # Для Stars не нужен
                currency="XTR",  # Код валюты для Telegram Stars
                prices=prices,
                need_email=False,
                need_phone_number=False,
                need_name=False,
                need_shipping_address=False,
                is_flexible=False
            )
            
            self.logger.info(
                "Telegram Stars инвойс отправлен",
                chat_id=chat_id,
                stars_amount=stars_amount
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Ошибка отправки Telegram Stars инвойса",
                chat_id=chat_id,
                error=str(e)
            )
            return False
    
    async def check_payment_status(self, payment_id: str) -> PaymentStatusData:
        """
        Проверка статуса платежа Telegram Stars.
        
        Note: Статус обновляется через pre_checkout_query и successful_payment
        """
        try:
            self.logger.info(
                "Проверка статуса Telegram Stars платежа",
                payment_id=payment_id
            )
            
            # Для Stars статус обновляется через события бота
            return PaymentStatusData(
                external_id=payment_id,
                status=PaymentStatus.PENDING,
            )
            
        except Exception as e:
            self.logger.error(
                "Ошибка проверки статуса Telegram Stars платежа",
                payment_id=payment_id,
                error=str(e)
            )
            raise PaymentProviderError(f"Ошибка проверки статуса: {str(e)}")
    
    async def cancel_payment(self, payment_id: str) -> bool:
        """
        Отмена платежа Telegram Stars.
        
        Note: Telegram Stars не поддерживает программную отмену отправленных инвойсов.
        """
        self.logger.info(
            "Попытка отмены Telegram Stars платежа",
            payment_id=payment_id
        )
        
        # Telegram Stars не поддерживает отмену инвойсов
        return False
    
    async def process_webhook(self, data: Dict[str, Any]) -> Tuple[str, PaymentStatusData]:
        """
        Обработка successful_payment от Telegram.
        
        Args:
            data: Данные о успешном платеже
            
        Returns:
            Tuple[str, PaymentStatusData]: ID платежа и его статус
        """
        try:
            # Получаем данные из successful_payment
            telegram_payment_charge_id = data.get("telegram_payment_charge_id")
            total_amount = data.get("total_amount")  # В минимальных единицах валюты
            currency = data.get("currency", "XTR")
            
            # Парсим payload для получения payment_id
            invoice_payload = data.get("invoice_payload", "{}")
            try:
                payload_data = json.loads(invoice_payload)
                payment_id = payload_data.get("payment_id")
            except (json.JSONDecodeError, AttributeError):
                payment_id = telegram_payment_charge_id
            
            if not payment_id:
                raise PaymentValidationError("Не удалось определить payment_id")
            
            # Конвертируем звезды обратно в рубли для записи
            if currency == "XTR" and total_amount:
                rub_amount = self._stars_to_rub(total_amount)
            else:
                rub_amount = None
            
            self.logger.info(
                "Telegram Stars платеж завершен",
                payment_id=payment_id,
                telegram_charge_id=telegram_payment_charge_id,
                stars_amount=total_amount,
                rub_amount=float(rub_amount) if rub_amount else None
            )
            
            return payment_id, PaymentStatusData(
                external_id=telegram_payment_charge_id,
                status=PaymentStatus.COMPLETED,
                amount=rub_amount,
                currency="RUB",
                metadata={
                    "telegram_payment_charge_id": telegram_payment_charge_id,
                    "stars_amount": total_amount,
                    "currency": currency,
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Ошибка обработки Telegram Stars webhook",
                data=data,
                error=str(e)
            )
            raise PaymentProviderError(f"Ошибка обработки платежа: {str(e)}")
    
    def validate_webhook_signature(self, data: bytes, signature: str) -> bool:
        """
        Валидация подписи для Telegram Stars.
        
        Note: Telegram автоматически обеспечивает безопасность через Bot API,
        дополнительная валидация подписи не требуется.
        """
        # Для Telegram Stars всегда возвращаем True,
        # так как данные приходят через безопасный Bot API
        return True
    
    def get_supported_currencies(self) -> list[str]:
        """Поддерживаемые валюты для Telegram Stars"""
        return ["XTR", "RUB"]  # XTR = Telegram Stars
    
    def get_min_amount(self, currency: str = "RUB") -> Decimal:
        """Минимальная сумма для Telegram Stars"""
        if currency == "XTR":
            return Decimal("1")  # 1 звезда
        return Decimal(str(self.stars_rate))  # Минимум на 1 звезду в рублях
    
    def get_max_amount(self, currency: str = "RUB") -> Decimal:
        """Максимальная сумма для Telegram Stars"""
        if currency == "XTR":
            return Decimal("10000")  # 10000 звезд
        return Decimal(str(10000 * self.stars_rate))  # В рублях 