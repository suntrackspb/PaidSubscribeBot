"""
Провайдер для интеграции с СБП (Система Быстрых Платежей).
Поддерживает создание QR-кодов для оплаты и проверку статуса платежей.
"""

import base64
import hashlib
import json
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
from urllib.parse import quote

import httpx
import qrcode
from io import BytesIO

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


class SBPProvider(BasePaymentProvider):
    """
    Провайдер для работы с СБП (Система Быстрых Платежей).
    
    Поддерживает:
    - Создание QR-кодов для оплаты через СБП
    - Статические и динамические QR-коды
    - Проверку статуса платежей (при наличии API банка)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger("payments.sbp")
        super().__init__(config)
        
        # Настройки СБП
        self.merchant_id = config.get("merchant_id")  # ID мерчанта в банке
        self.bank_id = config.get("bank_id")  # ID банка-эквайера
        self.api_url = config.get("api_url")  # URL API банка для проверки статуса
        self.secret_key = config.get("secret_key")  # Секретный ключ для подписи
        self.phone_number = config.get("phone_number")  # Номер телефона для статического QR
        
        # Настройки QR-кода
        self.qr_size = config.get("qr_size", 300)
        self.qr_border = config.get("qr_border", 4)
        
        # HTTP клиент для API банка
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    @property
    def method(self) -> PaymentMethod:
        return PaymentMethod.SBP
    
    @property
    def name(self) -> str:
        return "СБП"
    
    @property
    def is_enabled(self) -> bool:
        # Для базовой работы нужен либо merchant_id, либо phone_number
        return bool(self.merchant_id or self.phone_number)
    
    def _validate_config(self) -> None:
        """Валидация конфигурации СБП"""
        if not self.merchant_id and not self.phone_number:
            raise PaymentValidationError(
                "Необходимо настроить либо merchant_id, либо phone_number для СБП"
            )
    
    def _generate_qr_payload(self, payment_id: str, amount: Decimal, description: str) -> str:
        """
        Генерация payload для QR-кода СБП.
        
        Args:
            payment_id: ID платежа
            amount: Сумма платежа
            description: Описание платежа
            
        Returns:
            str: Payload для QR-кода
        """
        if self.merchant_id:
            # Динамический QR-код для мерчанта
            payload = f"https://qr.nspk.ru/{self.bank_id}/{self.merchant_id}?amount={amount}&currency=RUB&order={payment_id}&desc={quote(description)}"
        elif self.phone_number:
            # Статический QR-код по номеру телефона
            payload = f"https://qr.nspk.ru/AD10006M/{self.phone_number}?amount={amount}&currency=RUB&desc={quote(description)}"
        else:
            raise PaymentValidationError("Не настроены параметры для генерации QR-кода СБП")
        
        return payload
    
    def _generate_qr_code(self, payload: str) -> str:
        """
        Генерация QR-кода в формате base64.
        
        Args:
            payload: Строка для кодирования в QR
            
        Returns:
            str: QR-код в формате base64
        """
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=self.qr_border,
            )
            qr.add_data(payload)
            qr.make(fit=True)
            
            # Создаем изображение
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Изменяем размер
            img = img.resize((self.qr_size, self.qr_size))
            
            # Конвертируем в base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_base64}"
            
        except Exception as e:
            self.logger.error("Ошибка генерации QR-кода СБП", error=str(e))
            raise PaymentProviderError(f"Ошибка генерации QR-кода: {str(e)}")
    
    async def create_payment(self, request: PaymentRequest) -> PaymentResponse:
        """
        Создание платежа через СБП.
        
        Args:
            request: Запрос на создание платежа
            
        Returns:
            PaymentResponse: Ответ с данными о платеже
        """
        try:
            # Генерируем уникальный ID платежа
            payment_id = str(uuid.uuid4())
            
            # Создаем описание платежа
            description = request.description or "Подписка на канал"
            
            # Генерируем payload для QR-кода
            qr_payload = self._generate_qr_payload(payment_id, request.amount, description)
            
            # Генерируем QR-код
            qr_code_base64 = self._generate_qr_code(qr_payload)
            
            self.logger.info(
                "СБП платеж создан",
                payment_id=payment_id,
                amount=float(request.amount),
                user_id=request.user_id,
                has_qr=bool(qr_code_base64)
            )
            
            return PaymentResponse(
                payment_id=payment_id,
                status=PaymentStatus.PENDING,
                payment_url=qr_payload,  # URL для открытия в банковском приложении
                qr_code_url=qr_code_base64,  # QR-код в base64
                metadata={
                    "qr_payload": qr_payload,
                    "amount": float(request.amount),
                    "description": description,
                    "merchant_id": self.merchant_id,
                    "phone_number": self.phone_number,
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Ошибка создания СБП платежа",
                error=str(e),
                user_id=request.user_id,
                amount=float(request.amount)
            )
            raise PaymentProviderError(f"Ошибка создания платежа: {str(e)}")
    
    async def check_payment_status(self, payment_id: str) -> PaymentStatusData:
        """
        Проверка статуса платежа через API банка.
        
        Args:
            payment_id: ID платежа
            
        Returns:
            PaymentStatusData: Статус платежа
        """
        try:
            if not self.api_url or not self.merchant_id:
                # Если нет API банка, возвращаем статус "в ожидании"
                self.logger.info(
                    "API банка не настроено, статус СБП платежа остается pending",
                    payment_id=payment_id
                )
                return PaymentStatusData(
                    external_id=payment_id,
                    status=PaymentStatus.PENDING,
                )
            
            # Запрос к API банка для проверки статуса
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.secret_key}" if self.secret_key else None
            }
            headers = {k: v for k, v in headers.items() if v is not None}
            
            response = await self.http_client.get(
                f"{self.api_url}/payments/{payment_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Парсим ответ банка (формат зависит от конкретного банка)
                bank_status = data.get("status", "pending")
                amount = data.get("amount")
                paid_at = data.get("paid_at")
                
                # Маппинг статусов банка на наши статусы
                status_mapping = {
                    "completed": PaymentStatus.COMPLETED,
                    "success": PaymentStatus.COMPLETED,
                    "paid": PaymentStatus.COMPLETED,
                    "failed": PaymentStatus.FAILED,
                    "error": PaymentStatus.FAILED,
                    "cancelled": PaymentStatus.CANCELLED,
                    "pending": PaymentStatus.PENDING,
                }
                
                status = status_mapping.get(bank_status.lower(), PaymentStatus.PENDING)
                
                self.logger.info(
                    "Статус СБП платежа получен от банка",
                    payment_id=payment_id,
                    bank_status=bank_status,
                    mapped_status=status.value
                )
                
                return PaymentStatusData(
                    external_id=payment_id,
                    status=status,
                    amount=Decimal(str(amount)) if amount else None,
                    currency="RUB",
                    paid_at=paid_at,
                    metadata=data
                )
            
            elif response.status_code == 404:
                self.logger.warning(
                    "СБП платеж не найден в банке",
                    payment_id=payment_id
                )
                return PaymentStatusData(
                    external_id=payment_id,
                    status=PaymentStatus.PENDING,
                )
            
            else:
                raise PaymentNetworkError(
                    f"Ошибка API банка: {response.status_code}"
                )
            
        except httpx.RequestError as e:
            self.logger.error(
                "Сетевая ошибка при проверке статуса СБП платежа",
                payment_id=payment_id,
                error=str(e)
            )
            # В случае сетевой ошибки возвращаем pending
            return PaymentStatusData(
                external_id=payment_id,
                status=PaymentStatus.PENDING,
            )
        
        except Exception as e:
            self.logger.error(
                "Ошибка проверки статуса СБП платежа",
                payment_id=payment_id,
                error=str(e)
            )
            raise PaymentProviderError(f"Ошибка проверки статуса: {str(e)}")
    
    async def cancel_payment(self, payment_id: str) -> bool:
        """
        Отмена платежа СБП.
        
        Note: СБП не поддерживает программную отмену созданных QR-кодов.
        """
        self.logger.info(
            "Попытка отмены СБП платежа",
            payment_id=payment_id
        )
        
        # СБП не поддерживает отмену QR-кодов
        return False
    
    async def process_webhook(self, data: Dict[str, Any]) -> Tuple[str, PaymentStatusData]:
        """
        Обработка уведомления от банка о платеже СБП.
        
        Args:
            data: Данные уведомления от банка
            
        Returns:
            Tuple[str, PaymentStatusData]: ID платежа и его статус
        """
        try:
            # Получаем данные из уведомления банка
            payment_id = data.get("order_id") or data.get("payment_id")
            amount = data.get("amount")
            status = data.get("status", "completed")
            transaction_id = data.get("transaction_id")
            paid_at = data.get("timestamp") or data.get("paid_at")
            
            if not payment_id:
                raise PaymentValidationError("Отсутствует payment_id в уведомлении СБП")
            
            # Маппинг статусов
            if status.lower() in ["completed", "success", "paid"]:
                payment_status = PaymentStatus.COMPLETED
            elif status.lower() in ["failed", "error"]:
                payment_status = PaymentStatus.FAILED
            else:
                payment_status = PaymentStatus.PENDING
            
            self.logger.info(
                "СБП уведомление обработано",
                payment_id=payment_id,
                amount=amount,
                status=status,
                transaction_id=transaction_id
            )
            
            return payment_id, PaymentStatusData(
                external_id=transaction_id or payment_id,
                status=payment_status,
                amount=Decimal(str(amount)) if amount else None,
                currency="RUB",
                paid_at=paid_at,
                metadata={
                    "transaction_id": transaction_id,
                    "bank_status": status,
                    "timestamp": paid_at,
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Ошибка обработки СБП webhook",
                data=data,
                error=str(e)
            )
            raise PaymentProviderError(f"Ошибка обработки уведомления: {str(e)}")
    
    def validate_webhook_signature(self, data: bytes, signature: str) -> bool:
        """
        Валидация подписи уведомления СБП.
        
        Args:
            data: Сырые данные уведомления
            signature: Подпись от банка
            
        Returns:
            bool: True если подпись валидна
        """
        try:
            if not self.secret_key:
                self.logger.warning("Секретный ключ СБП не настроен, пропускаем валидацию")
                return True
            
            # Вычисляем подпись (алгоритм зависит от банка)
            # Обычно используется HMAC-SHA256
            import hmac
            
            calculated_signature = hmac.new(
                self.secret_key.encode(),
                data,
                hashlib.sha256
            ).hexdigest()
            
            is_valid = hmac.compare_digest(calculated_signature, signature)
            
            self.logger.info(
                "Проверка подписи СБП",
                is_valid=is_valid,
                signature_length=len(signature)
            )
            
            return is_valid
            
        except Exception as e:
            self.logger.error(
                "Ошибка валидации подписи СБП",
                error=str(e),
                signature=signature
            )
            return False
    
    def get_min_amount(self, currency: str = "RUB") -> Decimal:
        """Минимальная сумма для СБП"""
        return Decimal("1.00")
    
    def get_max_amount(self, currency: str = "RUB") -> Decimal:
        """Максимальная сумма для СБП"""
        return Decimal("1000000.00")  # Лимит СБП на одну операцию
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose() 