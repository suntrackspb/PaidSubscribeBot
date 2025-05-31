"""
Провайдер для интеграции с YooMoney (Яндекс.Деньги).
Поддерживает создание платежей, проверку статуса и обработку webhook'ов.
"""

import hashlib
import hmac
import json
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode

import httpx
from yoomoney import Quickpay

from app.payments.base import (
    BasePaymentProvider,
    PaymentRequest,
    PaymentResponse,
    PaymentStatusData,
    PaymentProviderError,
    PaymentValidationError,
    PaymentNetworkError,
    PaymentAuthError,
)
from app.database.models.payment import PaymentMethod, PaymentStatus
from app.utils.logger import get_logger


class YooMoneyProvider(BasePaymentProvider):
    """
    Провайдер для работы с YooMoney.
    
    Поддерживает:
    - Создание платежных форм через Quickpay
    - Проверку статуса платежей через API
    - Обработку уведомлений (notifications)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger("payments.yoomoney")
        super().__init__(config)
        
        # Настройки YooMoney
        self.receiver = config.get("receiver")  # Номер кошелька получателя
        self.secret_key = config.get("secret_key")  # Секретный ключ для уведомлений
        self.base_url = "https://yoomoney.ru"
        
    @property
    def method(self) -> PaymentMethod:
        return PaymentMethod.YOOMONEY
    
    @property
    def name(self) -> str:
        return "YooMoney"
    
    @property
    def is_enabled(self) -> bool:
        return bool(self.receiver and self.secret_key)
    
    def _validate_config(self) -> None:
        """Валидация конфигурации YooMoney"""
        if not self.receiver:
            raise PaymentValidationError("YooMoney receiver не настроен")
        
        if not self.secret_key:
            raise PaymentValidationError("YooMoney secret_key не настроен")
    
    async def create_payment(self, request: PaymentRequest) -> PaymentResponse:
        """
        Создание платежа через YooMoney Quickpay.
        
        Args:
            request: Запрос на создание платежа
            
        Returns:
            PaymentResponse: Ответ с данными о платеже
        """
        try:
            # Генерируем уникальный ID платежа
            payment_id = str(uuid.uuid4())
            
            # Создаем платежную форму
            quickpay = Quickpay(
                receiver=self.receiver,
                quickpay_form="shop",
                targets=request.description or f"Подписка на канал",
                paymentType="SB",  # Со счета в ЮMoney, банковской картой, наличными
                sum=float(request.amount),
                label=payment_id,  # Метка для идентификации платежа
                successURL=request.return_url,
            )
            
            # Получаем URL для оплаты
            payment_url = quickpay.redirected_url
            
            self.logger.info(
                "YooMoney платеж создан",
                payment_id=payment_id,
                amount=float(request.amount),
                user_id=request.user_id
            )
            
            return PaymentResponse(
                payment_id=payment_id,
                status=PaymentStatus.PENDING,
                payment_url=payment_url,
                metadata={
                    "receiver": self.receiver,
                    "label": payment_id,
                    "amount": float(request.amount),
                    "description": request.description,
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Ошибка создания YooMoney платежа",
                error=str(e),
                user_id=request.user_id,
                amount=float(request.amount)
            )
            raise PaymentProviderError(f"Ошибка создания платежа: {str(e)}")
    
    async def check_payment_status(self, payment_id: str) -> PaymentStatusData:
        """
        Проверка статуса платежа через YooMoney API.
        
        Note: Для полноценной проверки статуса требуется OAuth токен
        или использование уведомлений (notifications).
        В данной реализации используется базовая проверка.
        """
        try:
            # В реальной реализации здесь был бы запрос к YooMoney API
            # Но для базовой версии используем проверку через уведомления
            
            self.logger.info(
                "Проверка статуса YooMoney платежа",
                payment_id=payment_id
            )
            
            # Возвращаем статус "в ожидании" - реальный статус придет через webhook
            return PaymentStatusData(
                external_id=payment_id,
                status=PaymentStatus.PENDING,
            )
            
        except Exception as e:
            self.logger.error(
                "Ошибка проверки статуса YooMoney платежа",
                payment_id=payment_id,
                error=str(e)
            )
            raise PaymentProviderError(f"Ошибка проверки статуса: {str(e)}")
    
    async def cancel_payment(self, payment_id: str) -> bool:
        """
        Отмена платежа YooMoney.
        
        Note: YooMoney не поддерживает программную отмену созданных платежей.
        """
        self.logger.info(
            "Попытка отмены YooMoney платежа",
            payment_id=payment_id
        )
        
        # YooMoney не поддерживает отмену платежей через API
        return False
    
    async def process_webhook(self, data: Dict[str, Any]) -> Tuple[str, PaymentStatusData]:
        """
        Обработка уведомления от YooMoney.
        
        Args:
            data: Данные уведомления
            
        Returns:
            Tuple[str, PaymentStatusData]: ID платежа и его статус
        """
        try:
            # Получаем данные из уведомления
            operation_id = data.get("operation_id")
            label = data.get("label")  # Наш payment_id
            amount = data.get("amount")
            currency = data.get("currency", "643")  # 643 = RUB
            datetime_str = data.get("datetime")
            sender = data.get("sender")
            
            if not label:
                raise PaymentValidationError("Отсутствует label в уведомлении")
            
            # Определяем статус платежа
            status = PaymentStatus.COMPLETED
            
            self.logger.info(
                "YooMoney уведомление обработано",
                payment_id=label,
                operation_id=operation_id,
                amount=amount,
                sender=sender
            )
            
            return label, PaymentStatusData(
                external_id=operation_id or label,
                status=status,
                amount=Decimal(str(amount)) if amount else None,
                currency="RUB" if currency == "643" else currency,
                paid_at=datetime_str,
                metadata={
                    "operation_id": operation_id,
                    "sender": sender,
                    "datetime": datetime_str,
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Ошибка обработки YooMoney webhook",
                data=data,
                error=str(e)
            )
            raise PaymentProviderError(f"Ошибка обработки уведомления: {str(e)}")
    
    def validate_webhook_signature(self, data: bytes, signature: str) -> bool:
        """
        Валидация подписи уведомления YooMoney.
        
        Args:
            data: Сырые данные уведомления
            signature: Подпись (sha1_hash из параметров)
            
        Returns:
            bool: True если подпись валидна
        """
        try:
            # Парсим параметры из данных
            params = {}
            if isinstance(data, bytes):
                data_str = data.decode('utf-8')
            else:
                data_str = str(data)
            
            # Если данные в формате form data
            if '&' in data_str:
                for param in data_str.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        params[key] = value
            else:
                # Если данные в JSON формате
                params = json.loads(data_str)
            
            # Создаем строку для подписи согласно документации YooMoney
            params_for_hash = [
                params.get('notification_type', ''),
                params.get('operation_id', ''),
                params.get('amount', ''),
                params.get('currency', ''),
                params.get('datetime', ''),
                params.get('sender', ''),
                params.get('codepro', ''),
                self.secret_key,
                params.get('label', ''),
            ]
            
            hash_string = '&'.join(str(p) for p in params_for_hash)
            
            # Вычисляем SHA1 хеш
            calculated_hash = hashlib.sha1(hash_string.encode('utf-8')).hexdigest()
            
            # Сравниваем с переданной подписью
            is_valid = calculated_hash.lower() == signature.lower()
            
            self.logger.info(
                "Проверка подписи YooMoney",
                is_valid=is_valid,
                calculated_hash=calculated_hash,
                received_signature=signature
            )
            
            return is_valid
            
        except Exception as e:
            self.logger.error(
                "Ошибка валидации подписи YooMoney",
                error=str(e),
                signature=signature
            )
            return False
    
    def get_min_amount(self, currency: str = "RUB") -> Decimal:
        """Минимальная сумма для YooMoney"""
        return Decimal("1.00")
    
    def get_max_amount(self, currency: str = "RUB") -> Decimal:
        """Максимальная сумма для YooMoney"""
        return Decimal("500000.00")  # Лимит YooMoney 