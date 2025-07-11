"""
Inline клавиатуры для PaidSubscribeBot.
Содержит все inline клавиатуры, используемые ботом.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Optional
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.models.subscription import SubscriptionDuration
from app.database.models.payment import PaymentMethod


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню бота"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 Оплатить подписку", callback_data="pay_subscription"),
        ],
        [
            InlineKeyboardButton(text="📋 Моя подписка", callback_data="my_subscription"),
        ],
        [
            InlineKeyboardButton(text="🎯 Реферальная программа", callback_data="referral_menu"),
            InlineKeyboardButton(text="🎟️ Промокоды", callback_data="promo_menu"),
        ],
        [
            InlineKeyboardButton(text="📖 Справка", callback_data="help"),
            InlineKeyboardButton(text="🆘 Поддержка", callback_data="support"),
        ]
    ])
    return keyboard


def subscription_plans_keyboard(
    monthly_price: int,
    yearly_price: int,
    trial_available: bool = True,
    trial_days: int = 3
) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора тарифного плана.
    
    Args:
        monthly_price: Цена месячной подписки в рублях
        yearly_price: Цена годовой подписки в рублях
        trial_available: Доступна ли пробная подписка
        trial_days: Количество дней пробной подписки
    """
    keyboard = []
    
    # Месячная подписка
    keyboard.append([
        InlineKeyboardButton(
            text=f"📅 Месячная подписка - {monthly_price} ₽",
            callback_data=f"plan_{SubscriptionDuration.MONTHLY.value}"
        )
    ])
    
    # Годовая подписка
    discount = round((1 - (yearly_price / (monthly_price * 12))) * 100)
    keyboard.append([
        InlineKeyboardButton(
            text=f"📆 Годовая подписка - {yearly_price} ₽ (-{discount}%)",
            callback_data=f"plan_{SubscriptionDuration.YEARLY.value}"
        )
    ])
    
    # Пробная подписка (если доступна)
    if trial_available:
        keyboard.append([
            InlineKeyboardButton(
                text=f"🎁 Пробная подписка - {trial_days} дня (Бесплатно)",
                callback_data=f"plan_{SubscriptionDuration.TRIAL.value}"
            )
        ])
    
    # Кнопка назад
    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def payment_methods_keyboard(
    plan: str,
    amount: int,
    available_methods: Optional[List[PaymentMethod]] = None
) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора способа оплаты.
    
    Args:
        plan: Выбранный тарифный план
        amount: Сумма к оплате
        available_methods: Доступные способы оплаты
    """
    if available_methods is None:
        available_methods = [
            PaymentMethod.YOOMONEY,
            PaymentMethod.TELEGRAM_STARS,
            PaymentMethod.SBP,
            PaymentMethod.BANK_CARD,
        ]
    
    keyboard = []
    
    # Кнопки способов оплаты
    for method in available_methods:
        if method == PaymentMethod.YOOMONEY:
            text = "💰 YooMoney"
        elif method == PaymentMethod.TELEGRAM_STARS:
            text = "⭐ Telegram Stars"
        elif method == PaymentMethod.SBP:
            text = "🚀 СБП"
        elif method == PaymentMethod.BANK_CARD:
            text = "💳 Банковская карта"
        elif method == PaymentMethod.CRYPTO:
            text = "₿ Криптовалюта"
        else:
            continue
            
        keyboard.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"payment_{method.value}_{plan}_{amount}"
            )
        ])
    
    # Кнопки навигации
    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_plans"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def payment_confirmation_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения платежа.
    
    Args:
        payment_id: ID созданного платежа
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="💳 Перейти к оплате",
                url=f"https://payment.example.com/pay/{payment_id}"  # Заменить на реальный URL
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Проверить оплату",
                callback_data=f"check_payment_{payment_id}"
            )
        ],
        [
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_payment_{payment_id}"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")
        ]
    ])
    return keyboard


def subscription_info_keyboard(subscription_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """
    Клавиатура для информации о подписке.
    
    Args:
        subscription_id: ID подписки
        is_active: Активна ли подписка
    """
    keyboard = []
    
    if is_active:
        keyboard.append([
            InlineKeyboardButton(
                text="📢 Перейти в канал",
                url="https://t.me/your_channel"  # Заменить на реальную ссылку
            )
        ])
        keyboard.append([
            InlineKeyboardButton(
                text="🔄 Продлить подписку",
                callback_data="pay_subscription"
            )
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(
                text="💳 Оплатить подписку",
                callback_data="pay_subscription"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню администратора"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
        ],
        [
            InlineKeyboardButton(text="💳 Платежи", callback_data="admin_payments"),
            InlineKeyboardButton(text="📋 Подписки", callback_data="admin_subscriptions"),
        ],
        [
            InlineKeyboardButton(text="🎯 Рефералы", callback_data="admin_referrals"),
            InlineKeyboardButton(text="🎟️ Промокоды", callback_data="admin_promo"),
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="📤 Экспорт данных", callback_data="admin_export"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings"),
            InlineKeyboardButton(text="🔙 Выйти из админки", callback_data="exit_admin")
        ]
    ])
    return keyboard


def admin_users_keyboard(page: int = 1, total_pages: int = 1) -> InlineKeyboardMarkup:
    """
    Клавиатура управления пользователями.
    
    Args:
        page: Текущая страница
        total_pages: Общее количество страниц
    """
    keyboard = []
    
    # Кнопки управления пользователем
    keyboard.append([
        InlineKeyboardButton(text="🔍 Найти пользователя", callback_data="admin_find_user"),
        InlineKeyboardButton(text="📊 Экспорт данных", callback_data="admin_export_users"),
    ])
    
    # Пагинация
    if total_pages > 1:
        pagination_row = []
        if page > 1:
            pagination_row.append(
                InlineKeyboardButton(text="⬅️", callback_data=f"admin_users_page_{page-1}")
            )
        
        pagination_row.append(
            InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="current_page")
        )
        
        if page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(text="➡️", callback_data=f"admin_users_page_{page+1}")
            )
        
        keyboard.append(pagination_row)
    
    # Кнопка назад
    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="admin_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def user_management_keyboard(user_id: int, is_banned: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура управления конкретным пользователем.
    
    Args:
        user_id: ID пользователя
        is_banned: Заблокирован ли пользователь
    """
    keyboard = []
    
    # Информация о пользователе
    keyboard.append([
        InlineKeyboardButton(
            text="📋 Подписки пользователя",
            callback_data=f"admin_user_subscriptions_{user_id}"
        )
    ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="💳 Платежи пользователя",
            callback_data=f"admin_user_payments_{user_id}"
        )
    ])
    
    # Управление пользователем
    ban_text = "🔓 Разблокировать" if is_banned else "🚫 Заблокировать"
    keyboard.append([
        InlineKeyboardButton(
            text=ban_text,
            callback_data=f"admin_toggle_ban_{user_id}"
        ),
        InlineKeyboardButton(
            text="➕ Добавить подписку",
            callback_data=f"admin_add_subscription_{user_id}"
        )
    ])
    
    # Кнопки назад
    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад к пользователям", callback_data="admin_users"),
        InlineKeyboardButton(text="🏠 Админ меню", callback_data="admin_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def confirmation_keyboard(action: str, item_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения действия.
    
    Args:
        action: Действие для подтверждения
        item_id: ID элемента
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"confirm_{action}_{item_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data=f"cancel_{action}_{item_id}"
            )
        ]
    ])
    return keyboard


def back_button(callback_data: str = "back_to_main") -> InlineKeyboardMarkup:
    """
    Простая клавиатура с кнопкой "Назад".
    
    Args:
        callback_data: Callback data для кнопки назад
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=callback_data)]
    ])
    return keyboard


def url_button(text: str, url: str) -> InlineKeyboardMarkup:
    """
    Клавиатура с URL кнопкой.
    
    Args:
        text: Текст кнопки
        url: URL для перехода
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, url=url)]
    ])
    return keyboard


def get_subscription_plans_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифных планов"""
    keyboard = InlineKeyboardBuilder()
    
    keyboard.row(
        InlineKeyboardButton(text="🔹 Базовый - 199₽", callback_data="subscription_basic")
    )
    keyboard.row(
        InlineKeyboardButton(text="💎 Премиум - 499₽", callback_data="subscription_premium")
    )
    keyboard.row(
        InlineKeyboardButton(text="👑 VIP - 999₽", callback_data="subscription_vip")
    )
    keyboard.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    )
    
    return keyboard.as_markup()


def get_payment_methods_keyboard(available_methods: list, subscription_type: str, price: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора способов оплаты"""
    from app.database.models.payment import PaymentMethod
    
    keyboard = InlineKeyboardBuilder()
    
    # Маппинг методов на кнопки
    method_buttons = {
        PaymentMethod.YOOMONEY: ("💳 YooMoney", "yoomoney"),
        PaymentMethod.TELEGRAM_STARS: ("⭐ Telegram Stars", "stars"),
        PaymentMethod.SBP: ("📱 СБП", "sbp"),
        PaymentMethod.BANK_CARD: ("💳 Банковская карта", "card")
    }
    
    # Добавляем доступные методы
    for method in available_methods:
        if method in method_buttons:
            text, callback_key = method_buttons[method]
            callback_data = f"pay_{callback_key}_{subscription_type}_{price}"
            keyboard.row(
                InlineKeyboardButton(text=text, callback_data=callback_data)
            )
    
    # Кнопка "Назад"
    keyboard.row(
        InlineKeyboardButton(text="🔙 Назад к тарифам", callback_data="main_menu")
    )
    
    return keyboard.as_markup()


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура главного меню"""
    keyboard = InlineKeyboardBuilder()
    
    keyboard.row(
        InlineKeyboardButton(text="💳 Оплатить подписку", callback_data="subscription_plans")
    )
    keyboard.row(
        InlineKeyboardButton(text="ℹ️ Информация", callback_data="info"),
        InlineKeyboardButton(text="🆘 Поддержка", callback_data="support")
    )
    
    return keyboard.as_markup()


def get_subscription_menu_keyboard(has_subscription: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура меню подписок.
    
    Args:
        has_subscription: Есть ли у пользователя активная подписка
    """
    keyboard = []
    
    if has_subscription:
        keyboard.append([
            InlineKeyboardButton(text="📋 Мои подписки", callback_data="my_subscriptions")
        ])
        keyboard.append([
            InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="new_subscription")
        ])
        keyboard.append([
            InlineKeyboardButton(text="📱 Перейти в канал", url="https://t.me/your_channel")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(text="💳 Оформить подписку", callback_data="new_subscription")
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_subscription_plans_keyboard(channel) -> InlineKeyboardMarkup:
    """
    Клавиатура планов подписки для канала.
    
    Args:
        channel: Объект канала с ценами
    """
    keyboard = []
    
    # Месячная подписка
    if channel.monthly_price:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📅 Месячная подписка - {channel.monthly_price} ₽",
                callback_data="plan_monthly"
            )
        ])
    
    # Годовая подписка
    if channel.yearly_price:
        discount = 0
        if channel.monthly_price:
            discount = round((1 - (channel.yearly_price / (channel.monthly_price * 12))) * 100)
        
        text = f"📆 Годовая подписка - {channel.yearly_price} ₽"
        if discount > 0:
            text += f" (-{discount}%)"
        
        keyboard.append([
            InlineKeyboardButton(text=text, callback_data="plan_yearly")
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="subscription_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_payment_methods_keyboard(available_methods: List[PaymentMethod]) -> InlineKeyboardMarkup:
    """
    Клавиатура методов оплаты.
    
    Args:
        available_methods: Список доступных методов оплаты
    """
    keyboard = []
    
    method_names = {
        PaymentMethod.YOOMONEY: "💰 YooMoney",
        PaymentMethod.TELEGRAM_STARS: "⭐ Telegram Stars", 
        PaymentMethod.SBP: "🚀 СБП",
        PaymentMethod.BANK_CARD: "💳 Банковская карта",
        PaymentMethod.CRYPTO: "₿ Криптовалюта"
    }
    
    for method in available_methods:
        if method in method_names:
            keyboard.append([
                InlineKeyboardButton(
                    text=method_names[method],
                    callback_data=f"pay_{method.value}"
                )
            ])
    
    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="subscription_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_channels_list_keyboard(channels: list) -> InlineKeyboardMarkup:
    """
    Клавиатура списка каналов для выбора.
    
    Args:
        channels: Список каналов
    """
    keyboard = []
    
    for channel in channels:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📺 {channel.title}",
                callback_data=f"select_channel_{channel.id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_subscription_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура администрирования подписок"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="📺 Каналы", callback_data="admin_channels"),
            InlineKeyboardButton(text="💳 Платежи", callback_data="admin_payments")
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
        ]
    ])
    return keyboard


def get_notification_actions_keyboard(subscription_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура действий для уведомлений о подписке.
    
    Args:
        subscription_id: ID подписки
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="💳 Продлить подписку",
                callback_data=f"renew_{subscription_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="ℹ️ Информация о подписке",
                callback_data=f"sub_info_{subscription_id}"
            )
        ],
        [
            InlineKeyboardButton(text="📞 Поддержка", callback_data="support")
        ]
    ])
    return keyboard 