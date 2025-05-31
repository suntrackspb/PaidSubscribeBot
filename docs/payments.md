# Платежные системы PaidSubscribeBot

## Обзор

PaidSubscribeBot поддерживает несколько способов оплаты подписки:

- **YooMoney** (Яндекс.Деньги) - электронные кошельки и банковские карты
- **Telegram Stars** - внутренняя валюта Telegram
- **СБП** (Система Быстрых Платежей) - QR-коды для оплаты через банковские приложения

## Архитектура

### Базовые компоненты

1. **BasePaymentProvider** - абстрактный базовый класс для всех провайдеров
2. **PaymentManager** - менеджер для управления всеми провайдерами
3. **Конкретные провайдеры** - реализации для каждой платежной системы

### Структура файлов

```
app/payments/
├── __init__.py              # Экспорт основных классов
├── base.py                  # Базовые классы и интерфейсы
├── manager.py               # Менеджер платежных систем
├── yoomoney_provider.py     # Провайдер YooMoney
├── telegram_stars_provider.py  # Провайдер Telegram Stars
└── sbp_provider.py          # Провайдер СБП
```

## Настройка платежных систем

### YooMoney

1. Зарегистрируйтесь на [yoomoney.ru](https://yoomoney.ru)
2. Получите номер кошелька и секретный ключ для уведомлений
3. Добавьте в `.env`:

```env
YOOMONEY_RECEIVER=410011234567890
YOOMONEY_SECRET_KEY=your_secret_key_here
```

### Telegram Stars

1. Убедитесь, что ваш бот поддерживает платежи
2. Настройте курс конвертации в `.env`:

```env
TELEGRAM_STARS_RATE=100  # 1 звезда = 100 рублей
```

### СБП (Система Быстрых Платежей)

Есть два варианта настройки:

#### Вариант 1: Через мерчанта (рекомендуется)
```env
SBP_MERCHANT_ID=your_merchant_id
SBP_BANK_ID=your_bank_id
SBP_API_URL=https://api.bank.com/sbp
SBP_SECRET_KEY=your_secret_key
```

#### Вариант 2: Через номер телефона (упрощенный)
```env
SBP_PHONE_NUMBER=+71234567890
```

## Использование

### Создание платежа

```python
from app.payments.manager import payment_manager
from app.payments.base import PaymentRequest
from app.database.models.payment import PaymentMethod
from decimal import Decimal

# Создаем запрос на платеж
request = PaymentRequest(
    amount=Decimal("499.00"),
    currency="RUB",
    description="Подписка Premium",
    user_id=123456789
)

# Создаем платеж через YooMoney
response = await payment_manager.create_payment(
    PaymentMethod.YOOMONEY,
    request
)

print(f"Платеж создан: {response.payment_id}")
print(f"Ссылка для оплаты: {response.payment_url}")
```

### Проверка статуса платежа

```python
status = await payment_manager.check_payment_status(
    PaymentMethod.YOOMONEY,
    "payment_id_here"
)

print(f"Статус: {status.status}")
print(f"Сумма: {status.amount}")
```

### Обработка webhook'ов

```python
# Данные от платежной системы
webhook_data = {...}

# Обрабатываем через менеджер
payment_id, status = await payment_manager.process_webhook(
    PaymentMethod.YOOMONEY,
    webhook_data
)

if status.status == PaymentStatus.COMPLETED:
    print(f"Платеж {payment_id} успешно завершен!")
```

## Особенности провайдеров

### YooMoney

- **Поддерживаемые валюты**: RUB
- **Минимальная сумма**: 1₽
- **Максимальная сумма**: 500,000₽
- **Webhook**: Поддерживается с валидацией подписи
- **Отмена платежей**: Не поддерживается

### Telegram Stars

- **Поддерживаемые валюты**: XTR (Stars), RUB
- **Минимальная сумма**: 1 звезда (100₽ по умолчанию)
- **Максимальная сумма**: 10,000 звезд
- **Webhook**: Автоматически через Bot API
- **Отмена платежей**: Не поддерживается

### СБП

- **Поддерживаемые валюты**: RUB
- **Минимальная сумма**: 1₽
- **Максимальная сумма**: 1,000,000₽
- **QR-коды**: Статические и динамические
- **Webhook**: Зависит от банка-эквайера
- **Отмена платежей**: Не поддерживается

## Обработка ошибок

Все провайдеры используют единую систему исключений:

```python
from app.payments.base import (
    PaymentProviderError,
    PaymentValidationError,
    PaymentNetworkError,
    PaymentAuthError
)

try:
    response = await payment_manager.create_payment(method, request)
except PaymentValidationError as e:
    print(f"Ошибка валидации: {e}")
except PaymentNetworkError as e:
    print(f"Сетевая ошибка: {e}")
except PaymentAuthError as e:
    print(f"Ошибка аутентификации: {e}")
except PaymentProviderError as e:
    print(f"Общая ошибка провайдера: {e}")
```

## Логирование

Все операции с платежами логируются:

```python
# Логи создания платежей
logger.info("Платеж создан", payment_id="...", amount=499.0)

# Логи обработки webhook'ов
logger.info("Webhook обработан", payment_id="...", status="completed")

# Логи ошибок
logger.error("Ошибка создания платежа", error="...")
```

## Мониторинг

Для мониторинга платежей используйте:

1. **Логи** - все операции записываются в файлы логов
2. **Метрики** - количество успешных/неуспешных платежей
3. **Уведомления** - админы получают уведомления о критических ошибках

## Безопасность

1. **Валидация подписей** - все webhook'и проверяются на подлинность
2. **Шифрование данных** - чувствительные данные шифруются
3. **Логирование** - все операции записываются для аудита
4. **Ограничения** - проверка минимальных/максимальных сумм

## Тестирование

Для тестирования платежных систем:

1. Используйте тестовые окружения провайдеров
2. Проверьте все сценарии (успех, ошибка, отмена)
3. Убедитесь в корректной обработке webhook'ов
4. Протестируйте валидацию подписей

## Расширение

Для добавления нового провайдера:

1. Создайте класс, наследующий `BasePaymentProvider`
2. Реализуйте все абстрактные методы
3. Добавьте провайдер в `PaymentManager`
4. Обновите настройки и документацию

Пример:

```python
class NewPaymentProvider(BasePaymentProvider):
    @property
    def method(self) -> PaymentMethod:
        return PaymentMethod.NEW_METHOD
    
    async def create_payment(self, request: PaymentRequest) -> PaymentResponse:
        # Реализация создания платежа
        pass
    
    # ... другие методы
``` 