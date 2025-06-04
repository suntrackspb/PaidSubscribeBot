"""
Обработчики промокодов для PaidSubscribeBot.
Включает создание, применение и управление промокодами.
"""

from typing import Optional
from decimal import Decimal
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.services.promo_service import PromoService
from app.services.user_service import UserService
from app.database.models.promo import PromoCodeType
from app.utils.logger import get_logger

# Создаем роутер для промокод-обработчиков
promo_router = Router()

# Инициализируем сервисы
promo_service = PromoService()
user_service = UserService()

logger = get_logger("handlers.promo")


class PromoStates(StatesGroup):
    """Состояния для работы с промокодами"""
    entering_code = State()
    creating_code = State()
    entering_amount_to_check = State()


def create_promo_menu_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры промокодов"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎟️ Ввести промокод", callback_data="promo_enter"),
            InlineKeyboardButton(text="📋 Мои промокоды", callback_data="promo_my_codes")
        ],
        [
            InlineKeyboardButton(text="💰 Проверить скидку", callback_data="promo_check_discount"),
            InlineKeyboardButton(text="ℹ️ О промокодах", callback_data="promo_info")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="main_menu")
        ]
    ])
    return keyboard


def create_admin_promo_keyboard() -> InlineKeyboardMarkup:
    """Создание админской клавиатуры промокодов"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_promo_create"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_promo_stats")
        ],
        [
            InlineKeyboardButton(text="📋 Все промокоды", callback_data="admin_promo_list"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_promo_settings")
        ],
        [
            InlineKeyboardButton(text="⬅️ Админ-панель", callback_data="admin_menu")
        ]
    ])
    return keyboard


@promo_router.message(Command("promo"))
async def cmd_promo_menu(message: Message):
    """Команда входа в меню промокодов"""
    user_id = message.from_user.id
    
    # Получаем доступные промокоды пользователя
    promo_codes = await promo_service.get_promo_codes(
        active_only=True,
        user_telegram_id=str(user_id),
        limit=5
    )
    
    text = f"""
🎟️ <b>Промокоды и скидки</b>

Здесь вы можете ввести промокод для получения скидки или посмотреть доступные предложения.

💡 <b>Доступно промокодов:</b> {len(promo_codes)}

💰 <b>Как использовать:</b>
1. Введите промокод
2. Выберите подписку для оплаты
3. Скидка применится автоматически

🎁 <b>Виды скидок:</b>
• Фиксированная сумма (₽)
• Процентная скидка (%)
"""
    
    await message.answer(
        text,
        reply_markup=create_promo_menu_keyboard(),
        parse_mode="HTML"
    )


@promo_router.callback_query(F.data == "promo_menu")
async def cb_promo_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат к меню промокодов"""
    await state.clear()
    user_id = callback.from_user.id
    
    # Получаем доступные промокоды пользователя
    promo_codes = await promo_service.get_promo_codes(
        active_only=True,
        user_telegram_id=str(user_id),
        limit=5
    )
    
    text = f"""
🎟️ <b>Промокоды и скидки</b>

Здесь вы можете ввести промокод для получения скидки или посмотреть доступные предложения.

💡 <b>Доступно промокодов:</b> {len(promo_codes)}

💰 <b>Как использовать:</b>
1. Введите промокод
2. Выберите подписку для оплаты
3. Скидка применится автоматически

🎁 <b>Виды скидок:</b>
• Фиксированная сумма (₽)
• Процентная скидка (%)
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=create_promo_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@promo_router.callback_query(F.data == "promo_enter")
async def cb_promo_enter(callback: CallbackQuery, state: FSMContext):
    """Начало ввода промокода"""
    text = """
🎟️ <b>Введите промокод</b>

Отправьте мне промокод, чтобы проверить его и узнать размер скидки.

💡 <b>Формат:</b> PROMO2024 или promo123

Промокод может содержать буквы и цифры.
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="promo_menu")]
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    await state.set_state(PromoStates.entering_code)
    await callback.answer()


@promo_router.message(PromoStates.entering_code)
async def process_promo_code_input(message: Message, state: FSMContext):
    """Обработка введенного промокода"""
    code = message.text.strip().upper()
    user_id = message.from_user.id
    
    if len(code) < 3 or len(code) > 50:
        await message.answer(
            "❌ Неверный формат промокода. Длина должна быть от 3 до 50 символов.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_menu")]
            ])
        )
        return
    
    # Проверяем промокод с минимальной суммой
    test_amount = Decimal('100')  # Тестовая сумма
    validation = await promo_service.validate_promo_code(code, user_id, test_amount)
    
    if validation["valid"]:
        promo_code = validation["promo_code"]
        discount = validation["discount"]
        
        # Информация о промокоде
        if promo_code.type == PromoCodeType.PERCENTAGE:
            discount_text = f"{float(promo_code.value)}%"
        else:
            discount_text = f"{float(promo_code.value)} ₽"
        
        valid_until_text = ""
        if promo_code.valid_until:
            valid_until_text = f"\n⏰ Действует до: {promo_code.valid_until.strftime('%d.%m.%Y %H:%M')}"
        
        min_amount_text = ""
        if promo_code.min_amount:
            min_amount_text = f"\n💵 Минимальная сумма: {float(promo_code.min_amount)} ₽"
        
        text = f"""
✅ <b>Промокод действителен!</b>

🎟️ <b>Код:</b> {code}
📝 <b>Название:</b> {promo_code.title}
💰 <b>Скидка:</b> {discount_text}
📊 <b>Использований:</b> {promo_code.current_uses}/{promo_code.max_uses or '∞'}
🔄 <b>Осталось для вас:</b> {promo_code.max_uses_per_user - await promo_service.get_user_promo_usage_count(promo_code.id, user_id)}{valid_until_text}{min_amount_text}

💡 <b>Описание:</b> {promo_code.description or 'Нет описания'}

Этот промокод будет автоматически применен при оформлении подписки!
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 Оплатить подписку", callback_data="pay_subscription"),
            ],
            [
                InlineKeyboardButton(text="🔄 Ввести другой код", callback_data="promo_enter"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_menu")
            ]
        ])
        
        # Сохраняем промокод в состояние пользователя
        await state.update_data(applied_promo_code=code)
        
    else:
        text = f"""
❌ <b>Промокод недействителен</b>

🎟️ <b>Код:</b> {code}
🚫 <b>Ошибка:</b> {validation['error']}

Попробуйте ввести другой промокод или обратитесь в поддержку.
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Ввести другой код", callback_data="promo_enter"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_menu")
            ]
        ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.clear()


@promo_router.callback_query(F.data == "promo_my_codes")
async def cb_promo_my_codes(callback: CallbackQuery):
    """Мои промокоды"""
    user_id = callback.from_user.id
    
    # Получаем промокоды пользователя
    personal_codes = await promo_service.get_promo_codes(
        active_only=True,
        user_telegram_id=str(user_id),
        limit=10
    )
    
    # Получаем общие промокоды (не персональные)
    general_codes = await promo_service.get_promo_codes(
        active_only=True,
        user_telegram_id=None,
        limit=5
    )
    # Фильтруем только общие (не персональные)
    general_codes = [code for code in general_codes if not code.user_telegram_id]
    
    text = "🎟️ <b>Доступные промокоды</b>\n\n"
    
    if personal_codes:
        text += "👤 <b>Персональные:</b>\n"
        for code in personal_codes:
            if code.type == PromoCodeType.PERCENTAGE:
                discount = f"{float(code.value)}%"
            else:
                discount = f"{float(code.value)} ₽"
            
            remaining = code.max_uses_per_user - await promo_service.get_user_promo_usage_count(code.id, user_id)
            text += f"• <code>{code.code}</code> - {discount} (осталось: {remaining})\n"
        text += "\n"
    
    if general_codes:
        text += "🌐 <b>Общие:</b>\n"
        for code in general_codes[:3]:  # Показываем только первые 3
            if code.type == PromoCodeType.PERCENTAGE:
                discount = f"{float(code.value)}%"
            else:
                discount = f"{float(code.value)} ₽"
            text += f"• <code>{code.code}</code> - {discount}\n"
    
    if not personal_codes and not general_codes:
        text += "😔 У вас пока нет доступных промокодов.\n\nСледите за новостями и акциями!"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎟️ Ввести промокод", callback_data="promo_enter")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_menu")
        ]
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@promo_router.callback_query(F.data == "promo_check_discount")
async def cb_promo_check_discount(callback: CallbackQuery, state: FSMContext):
    """Проверка размера скидки для суммы"""
    text = """
💰 <b>Проверка размера скидки</b>

Введите сумму в рублях, чтобы узнать какая скидка будет применена с вашими промокодами.

💡 <b>Формат:</b> 199 или 1990

Это поможет вам выбрать наиболее выгодный промокод.
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="promo_menu")]
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    await state.set_state(PromoStates.entering_amount_to_check)
    await callback.answer()


@promo_router.message(PromoStates.entering_amount_to_check)
async def process_amount_check(message: Message, state: FSMContext):
    """Обработка суммы для проверки скидки"""
    try:
        amount = Decimal(message.text.strip())
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")
    except (ValueError, TypeError):
        await message.answer(
            "❌ Неверный формат суммы. Введите число больше 0.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_menu")]
            ])
        )
        return
    
    user_id = message.from_user.id
    
    # Получаем доступные промокоды
    promo_codes = await promo_service.get_promo_codes(
        active_only=True,
        user_telegram_id=str(user_id),
        limit=10
    )
    
    text = f"💰 <b>Расчет скидки для суммы: {float(amount)} ₽</b>\n\n"
    
    best_discount = Decimal('0')
    best_code = None
    
    if promo_codes:
        text += "🎟️ <b>Доступные промокоды:</b>\n"
        
        for code in promo_codes:
            validation = await promo_service.validate_promo_code(code.code, user_id, amount)
            
            if validation["valid"]:
                discount = validation["discount"]
                final_amount = amount - discount
                
                if code.type == PromoCodeType.PERCENTAGE:
                    discount_text = f"{float(code.value)}%"
                else:
                    discount_text = f"{float(code.value)} ₽"
                
                text += f"• <code>{code.code}</code> ({discount_text})\n"
                text += f"  💸 Скидка: {float(discount)} ₽\n"
                text += f"  💳 К оплате: {float(final_amount)} ₽\n\n"
                
                if discount > best_discount:
                    best_discount = discount
                    best_code = code
            else:
                text += f"• <code>{code.code}</code> - ❌ {validation['error']}\n\n"
    
    if best_code:
        text += f"🏆 <b>Лучший промокод:</b> <code>{best_code.code}</code>\n"
        text += f"💰 <b>Максимальная экономия:</b> {float(best_discount)} ₽"
    else:
        text += "😔 Нет подходящих промокодов для данной суммы."
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎟️ Ввести промокод", callback_data="promo_enter")
        ],
        [
            InlineKeyboardButton(text="💳 Оплатить подписку", callback_data="pay_subscription")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_menu")
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.clear()


@promo_router.callback_query(F.data == "promo_info")
async def cb_promo_info(callback: CallbackQuery):
    """Информация о промокодах"""
    text = """
ℹ️ <b>О промокодах и скидках</b>

🎟️ <b>Что такое промокод?</b>
Промокод - это специальный код, который дает скидку при оплате подписки.

💰 <b>Типы скидок:</b>
• <b>Фиксированная</b> - конкретная сумма в рублях
• <b>Процентная</b> - процент от стоимости подписки

🔄 <b>Ограничения:</b>
• Промокод может иметь срок действия
• Ограниченное количество использований
• Минимальная сумма заказа
• Персональные промокоды

📋 <b>Как использовать:</b>
1. Введите промокод в разделе "Промокоды"
2. Проверьте размер скидки
3. Оформите подписку - скидка применится автоматически

🎁 <b>Где получить промокоды:</b>
• При регистрации (приветственная скидка)
• За приглашение друзей
• В рамках акций и розыгрышей
• От администрации бота

💡 <b>Совет:</b> Подпишитесь на уведомления, чтобы не пропустить новые промокоды!
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎟️ Ввести промокод", callback_data="promo_enter")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_menu")
        ]
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


# Админские хэндлеры
@promo_router.callback_query(F.data == "admin_promo")
async def cb_admin_promo_menu(callback: CallbackQuery):
    """Админское меню промокодов"""
    # Получаем статистику
    stats = await promo_service.get_promo_stats()
    
    text = f"""
👑 <b>Управление промокодами</b>

📊 <b>Статистика:</b>
• Всего промокодов: {stats['total_promo_codes']}
• Активных: {stats['active_promo_codes']}
• Использований: {stats['total_usages']}
• Общая скидка: {stats['total_discount_given']} ₽

⚙️ Здесь вы можете создавать, редактировать и управлять промокодами системы.
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=create_admin_promo_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


async def get_applied_promo_code(state: FSMContext) -> Optional[str]:
    """Получение примененного промокода из состояния пользователя"""
    data = await state.get_data()
    return data.get("applied_promo_code") 