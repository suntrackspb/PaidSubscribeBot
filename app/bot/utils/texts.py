"""
Тексты сообщений для PaidSubscribeBot.
Содержит все тексты, которые отправляет бот пользователям.
"""

from typing import Dict, Any
from datetime import datetime


class Messages:
    """Класс с текстами сообщений бота"""
    
    # Команда /start
    START_MESSAGE = """
🤖 <b>Добро пожаловать в PaidSubscribeBot!</b>

Я помогу вам оформить подписку на закрытый канал.

<b>Что я умею:</b>
• 💳 Принимать оплату разными способами
• 🔑 Автоматически добавлять в канал после оплаты
• 📊 Показывать информацию о подписке
• 🆘 Предоставлять поддержку

Выберите действие в меню ниже:
"""
    
    # Команда /help
    HELP_MESSAGE = """
📖 <b>Справка по боту</b>

<b>Доступные команды:</b>
/start - Главное меню
/help - Эта справка
/subscription - Информация о подписке
/pay - Оплата подписки
/support - Связь с поддержкой

<b>Способы оплаты:</b>
• 💳 Банковские карты (Visa, MasterCard, МИР)
• 🚀 СБП (Система быстрых платежей)
• ⭐ Telegram Stars
• 💰 YooMoney

<b>Нужна помощь?</b>
Используйте команду /support для связи с поддержкой.
"""
    
    # Информация о подписке
    SUBSCRIPTION_INFO = """
📋 <b>Информация о подписке</b>

<b>Статус:</b> {status}
<b>Тарифный план:</b> {duration}
<b>Дата окончания:</b> {end_date}
<b>Дней осталось:</b> {days_left}

{additional_info}
"""
    
    SUBSCRIPTION_ACTIVE = """
✅ <b>Подписка активна</b>

Вы можете пользоваться всеми возможностями канала.
Не забудьте продлить подписку до окончания срока!
"""
    
    SUBSCRIPTION_EXPIRED = """
❌ <b>Подписка истекла</b>

Для продолжения пользования каналом необходимо продлить подписку.
"""
    
    SUBSCRIPTION_NOT_FOUND = """
❓ <b>Подписка не найдена</b>

У вас пока нет подписки на канал.
Оформите подписку, чтобы получить доступ к эксклюзивному контенту!
"""
    
    # Выбор тарифного плана
    CHOOSE_PLAN = """
💰 <b>Выберите тарифный план</b>

<b>📅 Месячная подписка</b>
• Цена: <b>{monthly_price} ₽</b>
• Срок: 30 дней
• Полный доступ к каналу

<b>📆 Годовая подписка</b>
• Цена: <b>{yearly_price} ₽</b>
• Срок: 365 дней
• Скидка {discount}%
• Полный доступ к каналу

{trial_info}
"""
    
    TRIAL_INFO = """
<b>🎁 Пробная подписка</b>
• Цена: <b>Бесплатно</b>
• Срок: {trial_days} дня
• Ограниченный доступ
"""
    
    # Выбор способа оплаты
    CHOOSE_PAYMENT_METHOD = """
💳 <b>Выберите способ оплаты</b>

<b>Тарифный план:</b> {plan}
<b>Сумма к оплате:</b> <b>{amount} ₽</b>

Доступные способы оплаты:
"""
    
    # Платежи
    PAYMENT_CREATED = """
💳 <b>Счет создан</b>

<b>Сумма:</b> {amount} ₽
<b>Способ оплаты:</b> {method}
<b>Номер счета:</b> #{payment_id}

{payment_info}

⏱ <b>Время ожидания оплаты:</b> 15 минут
"""
    
    PAYMENT_SUCCESS = """
✅ <b>Оплата прошла успешно!</b>

<b>Сумма:</b> {amount} ₽
<b>Способ оплаты:</b> {method}
<b>Номер транзакции:</b> #{payment_id}

🎉 <b>Поздравляем!</b>
Вы успешно оформили подписку. Теперь у вас есть доступ к каналу.

📢 <b>Ссылка на канал:</b> {channel_link}
"""
    
    PAYMENT_FAILED = """
❌ <b>Оплата не прошла</b>

<b>Причина:</b> {reason}
<b>Номер счета:</b> #{payment_id}

Попробуйте еще раз или выберите другой способ оплаты.
"""
    
    PAYMENT_PENDING = """
⏳ <b>Ожидаем оплату</b>

<b>Номер счета:</b> #{payment_id}
<b>Сумма:</b> {amount} ₽

Пожалуйста, завершите оплату в платежной системе.
Уведомление придет автоматически после подтверждения платежа.
"""
    
    # Поддержка
    SUPPORT_MESSAGE = """
🆘 <b>Поддержка</b>

Если у вас возникли вопросы или проблемы, мы готовы помочь!

<b>Способы связи:</b>
• 📱 Telegram: @support_username
• 📧 Email: support@example.com
• 🕐 Время работы: Пн-Пт, 9:00-18:00 (МСК)

<b>Часто задаваемые вопросы:</b>
• Как оплатить подписку?
• Как получить доступ к каналу?
• Как продлить подписку?
• Возврат средств

Мы ответим в течение 2-4 часов в рабочее время.
"""
    
    # Администраторские сообщения
    ADMIN_MENU = """
👑 <b>Панель администратора</b>

Выберите действие:
"""
    
    EXPORT_MENU = """
📤 <b>Экспорт данных</b>

Выберите что хотите экспортировать:

<b>Доступные форматы:</b>
• 📄 CSV - для таблиц
• 📊 JSON - для программ  
• 📈 Excel - для анализа

<b>Типы данных:</b>
• 👥 Пользователи
• 📋 Подписки
• 💳 Платежи
• 📊 Аналитика
• 💾 Полный бэкап
"""
    
    ADMIN_STATS = """
📊 <b>Статистика бота</b>

<b>👥 Пользователи:</b>
• Всего: {total_users}
• Активных: {active_users}
• Новых за сегодня: {new_users_today}

<b>💳 Подписки:</b>
• Активных: {active_subscriptions}
• Истекших: {expired_subscriptions}
• Пробных: {trial_subscriptions}

<b>💰 Платежи:</b>
• За сегодня: {payments_today} ({revenue_today} ₽)
• За месяц: {payments_month} ({revenue_month} ₽)
• Неудачных: {failed_payments}

<b>📈 Конверсия:</b>
• Подписка → Оплата: {conversion_rate}%
"""
    
    # Ошибки
    ERROR_GENERAL = """
❌ <b>Произошла ошибка</b>

Попробуйте еще раз или обратитесь в поддержку.
"""
    
    ERROR_PAYMENT_SYSTEM = """
❌ <b>Ошибка платежной системы</b>

Временные неполадки в платежной системе.
Попробуйте позже или выберите другой способ оплаты.
"""
    
    ERROR_INVALID_AMOUNT = """
❌ <b>Неверная сумма</b>

Указана некорректная сумма платежа.
"""
    
    ERROR_USER_BANNED = """
🚫 <b>Доступ заблокирован</b>

Ваш аккаунт заблокирован администратором.
Для разблокировки обратитесь в поддержку.
"""
    
    # Техническое обслуживание
    MAINTENANCE_MODE = """
🔧 <b>Техническое обслуживание</b>

Бот временно недоступен из-за проведения технических работ.
Приносим извинения за неудобства.

⏱ <b>Ориентировочное время восстановления:</b> {estimated_time}
"""


class AdminMessages:
    """Сообщения для администраторов"""
    
    NEW_USER = """
👤 <b>Новый пользователь</b>

<b>ID:</b> {user_id}
<b>Имя:</b> {name}
<b>Username:</b> @{username}
<b>Дата регистрации:</b> {created_at}
"""
    
    NEW_PAYMENT = """
💳 <b>Новый платеж</b>

<b>Пользователь:</b> {user_name} (ID: {user_id})
<b>Сумма:</b> {amount} ₽
<b>Способ:</b> {method}
<b>Статус:</b> {status}
<b>ID платежа:</b> #{payment_id}
"""
    
    SUBSCRIPTION_EXPIRED = """
⏰ <b>Подписка истекла</b>

<b>Пользователь:</b> {user_name} (ID: {user_id})
<b>План:</b> {plan}
<b>Дата истечения:</b> {expired_date}
"""


def format_currency(amount: float, currency: str = "RUB") -> str:
    """
    Форматирование суммы с валютой.
    
    Args:
        amount: Сумма
        currency: Код валюты
        
    Returns:
        str: Отформатированная строка
    """
    if currency == "RUB":
        return f"{amount:,.0f} ₽"
    return f"{amount:,.2f} {currency}"


def format_date(date_obj) -> str:
    """
    Форматирование даты для отображения.
    
    Args:
        date_obj: Объект даты
        
    Returns:
        str: Отформатированная дата
    """
    if not date_obj:
        return "Не указано"
    
    return date_obj.strftime("%d.%m.%Y %H:%M")


def format_subscription_status(status: str) -> str:
    """
    Форматирование статуса подписки.
    
    Args:
        status: Статус подписки
        
    Returns:
        str: Отформатированный статус
    """
    status_map = {
        "active": "✅ Активна",
        "expired": "❌ Истекла",
        "canceled": "🚫 Отменена",
        "trial": "🎁 Пробная",
        "pending": "⏳ Ожидает активации"
    }
    return status_map.get(status, status)


def format_payment_method(method: str) -> str:
    """
    Форматирование способа оплаты.
    
    Args:
        method: Способ оплаты
        
    Returns:
        str: Отформатированный способ оплаты
    """
    method_map = {
        "yoomoney": "💰 YooMoney",
        "telegram_stars": "⭐ Telegram Stars",
        "sbp": "🚀 СБП",
        "bank_card": "💳 Банковская карта",
        "crypto": "₿ Криптовалюта",
        "manual": "👨‍💼 Ручное начисление"
    }
    return method_map.get(method, method)


# Тексты для платежей
SUBSCRIPTION_PLANS_TEXT = """
💎 **Выберите тарифный план:**

🔹 **Базовый** - 199₽/месяц
• Доступ к основному контенту
• Поддержка в чате

💎 **Премиум** - 499₽/месяц  
• Все возможности Базового
• Эксклюзивные материалы
• Приоритетная поддержка

👑 **VIP** - 999₽/месяц
• Все возможности Премиум
• Персональные консультации
• Ранний доступ к новинкам
"""

PAYMENT_METHODS_TEXT = """
💳 **Выберите способ оплаты**

Тариф: **{plan}**
Сумма: **{price}₽**

Доступные способы оплаты:
"""

PAYMENT_CREATED_TEXT = """
✅ **Платеж создан!**

Способ оплаты: {method}
Сумма: {amount}₽
ID платежа: {payment_id}

Следуйте инструкциям для завершения оплаты.
"""

PAYMENT_ERROR_TEXT = """
❌ **Ошибка создания платежа**

{error}

Попробуйте выбрать другой способ оплаты или обратитесь в поддержку.
"""

PAYMENT_SUCCESS_TEXT = """
🎉 **Платеж успешно завершен!**

Сумма: {amount} {currency}

Ваша подписка активирована! Добро пожаловать в закрытый канал.
"""

# Глобальный объект с сообщениями
MESSAGES = {
    # Основные сообщения
    "start": Messages.START_MESSAGE,
    "help": Messages.HELP_MESSAGE,
    "support": Messages.SUPPORT_MESSAGE,
    
    # Подписки
    "no_subscription": """
📋 <b>У вас нет активной подписки</b>

Оформите подписку для получения доступа к эксклюзивному контенту канала!
    """,
    
    "subscription_expiring": """
⚠️ <b>Подписка скоро истечет</b>

Ваша подписка истекает через {days} дней.
Продлите подписку, чтобы не потерять доступ к каналу.
    """,
    
    "subscription_expired": """
❌ <b>Подписка истекла</b>

Ваша подписка истекла {date}.
Оформите новую подписку для продолжения пользования каналом.
    """,
    
    "welcome_to_channel": """
🎉 <b>Добро пожаловать в канал!</b>

Ваша подписка успешно активирована.
Теперь у вас есть полный доступ к контенту.

📅 Подписка действует до: {expires_at}
    """,
    
    # Платежи
    "payment_instructions": {
        "yoomoney": "Для оплаты через YooMoney перейдите по ссылке ниже:",
        "telegram_stars": "Для оплаты звездами Telegram нажмите кнопку ниже:",
        "sbp": "Отсканируйте QR-код приложением банка или перейдите по ссылке:",
        "bank_card": "Введите данные карты на странице оплаты:"
    },
    
    # Ошибки
    "error_channel_not_found": "❌ Канал не найден",
    "error_user_not_found": "❌ Пользователь не найден",
    "error_subscription_not_found": "❌ Подписка не найдена",
    "error_payment_failed": "❌ Ошибка при создании платежа",
    "error_invalid_plan": "❌ Неверный план подписки",
    "error_access_denied": "🚫 Доступ запрещен",
    
    # Админ сообщения
    "admin_only": "👑 Эта команда доступна только администраторам",
    "admin_stats_header": "📊 <b>Статистика системы</b>",
    "admin_users_header": "👥 <b>Управление пользователями</b>",
    "admin_channels_header": "📺 <b>Управление каналами</b>",
}

# Дополнительные функции форматирования
def format_subscription_info(subscription) -> str:
    """Форматирование информации о подписке"""
    if not subscription:
        return MESSAGES["no_subscription"]
    
    days_left = (subscription.expires_at - datetime.utcnow()).days
    status = "🟢 Активна" if subscription.is_active and days_left > 0 else "🔴 Неактивна"
    
    return f"""
📋 <b>Информация о подписке</b>

<b>Статус:</b> {status}
<b>Действует до:</b> {subscription.expires_at.strftime('%d.%m.%Y')}
<b>Дней осталось:</b> {max(0, days_left)}
<b>Стоимость:</b> {subscription.price} ₽
    """

def format_channel_info(channel) -> str:
    """Форматирование информации о канале"""
    text = f"📺 <b>{channel.title}</b>\n\n"
    
    if channel.description:
        text += f"📝 {channel.description}\n\n"
    
    if channel.monthly_price:
        text += f"💰 Месячная подписка: {channel.monthly_price} ₽\n"
    
    if channel.yearly_price:
        text += f"💰 Годовая подписка: {channel.yearly_price} ₽\n"
    
    return text

def format_payment_info(payment) -> str:
    """Форматирование информации о платеже"""
    status_icons = {
        "pending": "⏳",
        "completed": "✅", 
        "failed": "❌",
        "cancelled": "🚫"
    }
    
    icon = status_icons.get(payment.status, "❓")
    
    return f"""
💳 <b>Платеж #{payment.external_id}</b>

<b>Статус:</b> {icon} {payment.status}
<b>Сумма:</b> {payment.amount} {payment.currency}
<b>Дата:</b> {payment.created_at.strftime('%d.%m.%Y %H:%M')}
    """

def format_user_stats(stats: dict) -> str:
    """Форматирование статистики пользователей"""
    return f"""
👥 <b>Статистика пользователей</b>

<b>Всего пользователей:</b> {stats.get('total', 0)}
<b>Активных:</b> {stats.get('active', 0)}
<b>С подпиской:</b> {stats.get('with_subscription', 0)}
<b>Новых за сегодня:</b> {stats.get('new_today', 0)}
    """

def format_subscription_stats(stats: dict) -> str:
    """Форматирование статистики подписок"""
    return f"""
📊 <b>Статистика подписок</b>

<b>Всего подписок:</b> {stats.get('total', 0)}
<b>Активных:</b> {stats.get('active', 0)}
<b>Истекших:</b> {stats.get('expired', 0)}
<b>Отмененных:</b> {stats.get('cancelled', 0)}
    """ 