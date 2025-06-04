"""
Обработчики реферальной системы для PaidSubscribeBot.
Включает создание реферальных ссылок, просмотр статистики и управление рефералами.
"""

from typing import Optional
from decimal import Decimal

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.bot.utils.texts import Messages
from app.services.referral_service import ReferralService
from app.services.user_service import UserService
from app.utils.logger import get_logger
from app.config.settings import get_settings

# Создаем роутер для реферальных обработчиков
referral_router = Router()

# Инициализируем сервисы
referral_service = ReferralService()
user_service = UserService()

logger = get_logger("handlers.referral")
settings = get_settings()


def create_referral_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для реферальной системы"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Моя статистика", callback_data="referral_stats"),
            InlineKeyboardButton(text="👥 Мои рефералы", callback_data="referral_list")
        ],
        [
            InlineKeyboardButton(text="🔗 Получить ссылку", callback_data="referral_link"),
            InlineKeyboardButton(text="ℹ️ Как это работает", callback_data="referral_info")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="main_menu")
        ]
    ])
    return keyboard


def create_referral_link_keyboard(referral_link: str) -> InlineKeyboardMarkup:
    """Создание клавиатуры с реферальной ссылкой"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Скопировать ссылку", url=referral_link)
        ],
        [
            InlineKeyboardButton(text="📤 Поделиться", switch_inline_query=f"Присоединяйся к боту по моей ссылке: {referral_link}")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="referral_menu")
        ]
    ])
    return keyboard


@referral_router.message(Command("referral"))
async def cmd_referral_menu(message: Message):
    """Команда входа в реферальное меню"""
    user_id = message.from_user.id
    
    # Получаем статистику пользователя
    stats = await referral_service.get_referral_stats(user_id)
    
    text = f"""
🎯 <b>Реферальная программа</b>

💰 <b>Ваша статистика:</b>
👥 Всего рефералов: {stats['total_referrals']}
✅ Подтвержденных: {stats['confirmed_referrals']}
⏳ Ожидают: {stats['pending_referrals']}

💵 <b>Вознаграждения:</b>
💰 Всего заработано: {stats['total_rewards']} ₽
✅ Выплачено: {stats['paid_rewards']} ₽
⏳ К выплате: {stats['pending_rewards']} ₽

Приглашайте друзей и получайте вознаграждения за каждую их подписку!
"""
    
    await message.answer(
        text,
        reply_markup=create_referral_keyboard(),
        parse_mode="HTML"
    )


@referral_router.callback_query(F.data == "referral_menu")
async def cb_referral_menu(callback: CallbackQuery):
    """Возврат к реферальному меню"""
    user_id = callback.from_user.id
    
    # Получаем статистику пользователя
    stats = await referral_service.get_referral_stats(user_id)
    
    text = f"""
🎯 <b>Реферальная программа</b>

💰 <b>Ваша статистика:</b>
👥 Всего рефералов: {stats['total_referrals']}
✅ Подтвержденных: {stats['confirmed_referrals']}
⏳ Ожидают: {stats['pending_referrals']}

💵 <b>Вознаграждения:</b>
💰 Всего заработано: {stats['total_rewards']} ₽
✅ Выплачено: {stats['paid_rewards']} ₽
⏳ К выплате: {stats['pending_rewards']} ₽

Приглашайте друзей и получайте вознаграждения за каждую их подписку!
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=create_referral_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@referral_router.callback_query(F.data == "referral_link")
async def cb_referral_link(callback: CallbackQuery):
    """Получение реферальной ссылки"""
    user_id = callback.from_user.id
    
    try:
        # Генерируем уникальный реферальный код
        referral_code = referral_service.generate_referral_code()
        
        # Создаем реферальную ссылку
        bot_username = settings.BOT_USERNAME or "your_bot"
        referral_link = f"https://t.me/{bot_username}?start=ref_{referral_code}"
        
        text = f"""
🔗 <b>Ваша реферальная ссылка</b>

<code>{referral_link}</code>

📋 Скопируйте ссылку и отправьте друзьям!

💡 <b>Как это работает:</b>
1. Друг переходит по вашей ссылке
2. Регистрируется в боте
3. Оплачивает подписку
4. Вы получаете вознаграждение!

💰 <b>Размер вознаграждения:</b> 100 ₽ за каждого друга
"""
        
        await callback.message.edit_text(
            text,
            reply_markup=create_referral_link_keyboard(referral_link),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка создания реферальной ссылки: {e}")
        await callback.answer("❌ Ошибка создания ссылки", show_alert=True)
    
    await callback.answer()


@referral_router.callback_query(F.data == "referral_stats")
async def cb_referral_stats(callback: CallbackQuery):
    """Подробная статистика рефералов"""
    user_id = callback.from_user.id
    
    try:
        stats = await referral_service.get_referral_stats(user_id)
        
        text = f"""
📊 <b>Подробная статистика</b>

👥 <b>Рефералы:</b>
• Всего приглашено: {stats['total_referrals']}
• Подтвержденных: {stats['confirmed_referrals']}
• Ожидают подтверждения: {stats['pending_referrals']}

💰 <b>Вознаграждения:</b>
• Всего заработано: {stats['total_rewards']} ₽
• Выплачено: {stats['paid_rewards']} ₽
• К выплате: {stats['pending_rewards']} ₽

📈 <b>Конверсия:</b>
"""
        
        if stats['total_referrals'] > 0:
            conversion_rate = (stats['confirmed_referrals'] / stats['total_referrals']) * 100
            text += f"• {conversion_rate:.1f}% рефералов оплатили подписку"
        else:
            text += "• Пока нет данных для расчета"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="referral_stats")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="referral_menu")]
        ])
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await callback.answer("❌ Ошибка получения статистики", show_alert=True)
    
    await callback.answer()


@referral_router.callback_query(F.data == "referral_list")
async def cb_referral_list(callback: CallbackQuery):
    """Список рефералов пользователя"""
    user_id = callback.from_user.id
    
    try:
        referrals = await referral_service.get_referrals_by_referrer(user_id, limit=10)
        
        text = "👥 <b>Ваши рефералы</b>\n\n"
        
        if referrals:
            for i, referral in enumerate(referrals, 1):
                status_emoji = {
                    "pending": "⏳",
                    "confirmed": "✅",
                    "rewarded": "💰"
                }.get(referral.status, "❓")
                
                referred_user = referral.referred
                user_name = referred_user.full_name if referred_user else f"ID: {referral.referred_id}"
                
                text += f"{i}. {status_emoji} {user_name}\n"
                text += f"   Статус: {referral.status}\n"
                
                if referral.reward_amount:
                    text += f"   Вознаграждение: {referral.reward_amount} ₽\n"
                
                text += f"   Дата: {referral.created_at.strftime('%d.%m.%Y')}\n\n"
        else:
            text += "У вас пока нет рефералов.\n\n"
            text += "💡 Получите реферальную ссылку и начните приглашать друзей!"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="referral_list")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="referral_menu")]
        ])
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения списка рефералов: {e}")
        await callback.answer("❌ Ошибка получения списка", show_alert=True)
    
    await callback.answer()


@referral_router.callback_query(F.data == "referral_info")
async def cb_referral_info(callback: CallbackQuery):
    """Информация о реферальной программе"""
    text = """
ℹ️ <b>Как работает реферальная программа</b>

🎯 <b>Что нужно делать:</b>
1. Получите свою уникальную реферальную ссылку
2. Поделитесь ей с друзьями
3. Когда друг оплатит подписку - получите вознаграждение!

💰 <b>Размер вознаграждений:</b>
• 100 ₽ за каждого друга, оплатившего подписку
• Вознаграждение начисляется автоматически
• Выплаты производятся еженедельно

📋 <b>Условия:</b>
• Друг должен быть новым пользователем
• Он должен оплатить подписку в течение 30 дней
• Максимум 100 рефералов от одного пользователя

🚀 <b>Советы для успеха:</b>
• Рассказывайте о преимуществах канала
• Делитесь ссылкой в соцсетях
• Помогайте друзьям с регистрацией

💡 Чем больше активных друзей вы приведете, тем больше заработаете!
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Получить ссылку", callback_data="referral_link")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="referral_menu")]
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


async def process_referral_start(user_id: int, referral_code: str) -> bool:
    """Обработка реферального кода при старте бота"""
    try:
        # Извлекаем код из параметра start
        if referral_code.startswith("ref_"):
            code = referral_code[4:]  # Убираем префикс "ref_"
            
            # Ищем реферера по коду (в данном случае код генерируется динамически)
            # Для простоты будем искать по последним рефералам
            # В реальной системе нужно сохранять соответствие код -> реферер
            
            # Пока что просто логируем
            logger.info(f"Получен реферальный код: {code} для пользователя {user_id}")
            
            # TODO: Реализовать поиск реферера по коду и создание связи
            return True
            
    except Exception as e:
        logger.error(f"Ошибка обработки реферального кода: {e}")
        return False
    
    return False


async def confirm_referral_on_payment(user_id: int, payment_amount: Decimal) -> bool:
    """Подтверждение реферала при оплате"""
    try:
        referral = await referral_service.confirm_referral(user_id, payment_amount)
        if referral:
            logger.info(f"Реферал подтвержден для пользователя {user_id}, вознаграждение: {referral.reward_amount}")
            
            # Уведомляем реферера о получении вознаграждения
            # TODO: Отправить уведомление реферу
            
            return True
    except Exception as e:
        logger.error(f"Ошибка подтверждения реферала: {e}")
    
    return False 