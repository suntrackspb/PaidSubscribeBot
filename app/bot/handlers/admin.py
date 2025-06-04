"""
Обработчики админ-панели для PaidSubscribeBot.
Включает управление пользователями, статистику, настройки и массовые операции.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncio

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.bot.keyboards.inline import (
    admin_menu_keyboard,
    admin_users_keyboard,
    user_management_keyboard
)
from app.bot.utils.texts import Messages
from app.bot.middlewares.auth import AdminMiddleware
from app.services.user_service import UserService
from app.services.subscription_service import SubscriptionService
from app.services.channel_service import ChannelService
from app.services.notification_service import NotificationService
from app.database.models.user import User
from app.database.models.subscription import Subscription
from app.database.models.payment import Payment
from app.config.settings import get_settings
from app.utils.logger import get_logger, log_admin_action

# Создаем роутер для админ-обработчиков
admin_router = Router()
admin_router.message.middleware(AdminMiddleware())
admin_router.callback_query.middleware(AdminMiddleware())

# Инициализируем сервисы
user_service = UserService()
subscription_service = SubscriptionService()
channel_service = ChannelService()
notification_service = NotificationService()

logger = get_logger("handlers.admin")
settings = get_settings()


@admin_router.message(Command("admin"))
async def cmd_admin_panel(message: Message):
    """Команда входа в админ-панель"""
    log_admin_action(
        admin_id=message.from_user.id,
        action="access_admin_panel"
    )
    
    text = """
👑 <b>Панель администратора</b>

Добро пожаловать в административную панель!
Здесь вы можете управлять системой, просматривать статистику и настраивать бота.
"""
    
    await message.answer(
        text,
        reply_markup=admin_menu_keyboard(),
        parse_mode="HTML"
    )


@admin_router.callback_query(F.data == "admin_menu")
async def cb_admin_menu(callback: CallbackQuery):
    """Возврат к главному меню админки"""
    text = """
👑 <b>Панель администратора</b>

Выберите раздел для управления:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=admin_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    """Показ статистики системы"""
    log_admin_action(
        admin_id=callback.from_user.id,
        action="view_stats"
    )
    
    try:
        # Получаем статистику пользователей
        total_users = await user_service.get_users_count()
        active_users = await user_service.get_active_users_count(days=7)
        new_users_today = await user_service.get_new_users_count(days=1)
        
        # Получаем статистику подписок
        active_subscriptions = await subscription_service.get_active_subscriptions_count()
        expired_subscriptions = await subscription_service.get_expired_subscriptions_count()
        
        # Получаем статистику платежей
        payments_today = await subscription_service.get_payments_count(days=1)
        revenue_today = await subscription_service.get_revenue(days=1)
        payments_month = await subscription_service.get_payments_count(days=30)
        revenue_month = await subscription_service.get_revenue(days=30)
        
        # Вычисляем конверсию
        conversion_rate = 0
        if total_users > 0:
            conversion_rate = round((active_subscriptions / total_users) * 100, 1)
        
        text = Messages.ADMIN_STATS.format(
            total_users=total_users,
            active_users=active_users,
            new_users_today=new_users_today,
            active_subscriptions=active_subscriptions,
            expired_subscriptions=expired_subscriptions,
            trial_subscriptions=0,  # TODO: Реализовать пробные подписки
            payments_today=payments_today,
            revenue_today=revenue_today,
            payments_month=payments_month,
            revenue_month=revenue_month,
            failed_payments=0,  # TODO: Реализовать статистику неудачных платежей
            conversion_rate=conversion_rate
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats")],
            [InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="admin_menu")]
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


@admin_router.callback_query(F.data == "admin_users")
async def cb_admin_users(callback: CallbackQuery):
    """Управление пользователями"""
    log_admin_action(
        admin_id=callback.from_user.id,
        action="view_users"
    )
    
    try:
        # Получаем последних пользователей
        users = await user_service.get_recent_users(limit=10)
        
        text = "👥 <b>Управление пользователями</b>\n\n"
        
        if users:
            text += "<b>Последние пользователи:</b>\n"
            for user in users:
                status = "🟢" if user.is_active else "🔴"
                text += f"{status} {user.first_name or 'Неизвестно'} (@{user.username or 'нет'})\n"
                text += f"   ID: <code>{user.telegram_id}</code>\n"
                text += f"   Создан: {user.created_at.strftime('%d.%m.%Y')}\n\n"
        else:
            text += "Пользователи не найдены."
        
        await callback.message.edit_text(
            text,
            reply_markup=admin_users_keyboard(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения пользователей: {e}")
        await callback.answer("❌ Ошибка получения пользователей", show_alert=True)
    
    await callback.answer()


@admin_router.callback_query(F.data == "admin_find_user")
async def cb_admin_find_user(callback: CallbackQuery, state: FSMContext):
    """Поиск пользователя по ID или username"""
    await state.set_state("finding_user")
    
    text = """
🔍 <b>Поиск пользователя</b>

Отправьте ID пользователя или username (с @ или без):

Примеры:
• <code>123456789</code>
• <code>@username</code>
• <code>username</code>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_users")]
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@admin_router.message(F.text, lambda m, state: state and state.get_state() == "finding_user")
async def process_find_user(message: Message, state: FSMContext):
    """Обработка поиска пользователя"""
    search_query = message.text.strip()
    
    try:
        user = None
        
        # Поиск по ID
        if search_query.isdigit():
            user = await user_service.get_user_by_telegram_id(int(search_query))
        
        # Поиск по username
        else:
            username = search_query.replace("@", "")
            user = await user_service.get_user_by_username(username)
        
        if user:
            # Получаем подписки пользователя
            subscriptions = await subscription_service.get_user_subscriptions(user.id)
            
            text = f"""
👤 <b>Пользователь найден</b>

<b>Имя:</b> {user.first_name or 'Не указано'}
<b>Username:</b> @{user.username or 'не указан'}
<b>ID:</b> <code>{user.telegram_id}</code>
<b>Язык:</b> {user.language_code or 'не указан'}
<b>Регистрация:</b> {user.created_at.strftime('%d.%m.%Y %H:%M')}
<b>Последняя активность:</b> {user.last_activity.strftime('%d.%m.%Y %H:%M') if user.last_activity else 'Никогда'}
<b>Статус:</b> {'🟢 Активен' if user.is_active else '🔴 Неактивен'}
<b>Заблокирован:</b> {'🚫 Да' if user.is_banned else '✅ Нет'}

<b>Подписки:</b> {len(subscriptions)}
"""
            
            keyboard = user_management_keyboard(user.telegram_id, user.is_banned)
            
            await message.answer(
                text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            
        else:
            await message.answer(
                "❌ Пользователь не найден",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
                ])
            )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка поиска пользователя: {e}")
        await message.answer("❌ Ошибка поиска")
        await state.clear()


@admin_router.callback_query(F.data.startswith("admin_toggle_ban_"))
async def cb_toggle_user_ban(callback: CallbackQuery):
    """Блокировка/разблокировка пользователя"""
    user_id = int(callback.data.split("_")[-1])
    
    try:
        user = await user_service.get_user_by_telegram_id(user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Переключаем статус блокировки
        new_status = not user.is_banned
        await user_service.update_user_ban_status(user_id, new_status)
        
        action = "ban" if new_status else "unban"
        log_admin_action(
            admin_id=callback.from_user.id,
            action=f"{action}_user",
            target_user_id=user_id
        )
        
        status_text = "заблокирован" if new_status else "разблокирован"
        await callback.answer(f"✅ Пользователь {status_text}")
        
        # Обновляем клавиатуру
        keyboard = user_management_keyboard(user_id, new_status)
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка изменения статуса пользователя: {e}")
        await callback.answer("❌ Ошибка изменения статуса", show_alert=True)


@admin_router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    """Массовая рассылка"""
    log_admin_action(
        admin_id=callback.from_user.id,
        action="start_broadcast"
    )
    
    await state.set_state("broadcast_message")
    
    text = """
📢 <b>Массовая рассылка</b>

Отправьте сообщение для рассылки всем пользователям.

⚠️ <b>Внимание:</b>
• Сообщение будет отправлено ВСЕМ пользователям
• Поддерживается HTML-разметка
• Можно отправлять текст, фото, видео
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_menu")]
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@admin_router.message(F.text, lambda m, state: state and state.get_state() == "broadcast_message")
async def process_broadcast(message: Message, state: FSMContext):
    """Обработка массовой рассылки"""
    broadcast_text = message.text
    
    try:
        # Получаем всех активных пользователей
        users = await user_service.get_all_active_users()
        
        if not users:
            await message.answer("❌ Нет активных пользователей для рассылки")
            await state.clear()
            return
        
        # Подтверждение рассылки
        text = f"""
📢 <b>Подтверждение рассылки</b>

<b>Получателей:</b> {len(users)}
<b>Сообщение:</b>

{broadcast_text[:200]}{'...' if len(broadcast_text) > 200 else ''}

Подтвердите отправку:
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_broadcast"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="admin_menu")
            ]
        ])
        
        # Сохраняем сообщение в состоянии
        await state.update_data(broadcast_text=broadcast_text, users_count=len(users))
        
        await message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка подготовки рассылки: {e}")
        await message.answer("❌ Ошибка подготовки рассылки")
        await state.clear()


@admin_router.callback_query(F.data == "confirm_broadcast")
async def cb_confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и выполнение рассылки"""
    data = await state.get_data()
    broadcast_text = data.get("broadcast_text")
    
    if not broadcast_text:
        await callback.answer("❌ Сообщение для рассылки не найдено", show_alert=True)
        await state.clear()
        return
    
    log_admin_action(
        admin_id=callback.from_user.id,
        action="execute_broadcast",
        message_length=len(broadcast_text)
    )
    
    await callback.message.edit_text(
        "📤 <b>Выполняется рассылка...</b>\n\nПожалуйста, подождите.",
        parse_mode="HTML"
    )
    
    try:
        # Запускаем рассылку в фоне
        await notification_service.broadcast_message(
            message=broadcast_text,
            admin_id=callback.from_user.id
        )
        
        await callback.message.edit_text(
            "✅ <b>Рассылка запущена!</b>\n\nСтатистика будет отправлена по завершении.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ В админку", callback_data="admin_menu")]
            ]),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка выполнения рассылки: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка рассылки</b>\n\nПопробуйте позже или обратитесь к разработчику.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ В админку", callback_data="admin_menu")]
            ]),
            parse_mode="HTML"
        )
    
    await state.clear()
    await callback.answer()


@admin_router.callback_query(F.data == "admin_settings")
async def cb_admin_settings(callback: CallbackQuery):
    """Настройки системы"""
    log_admin_action(
        admin_id=callback.from_user.id,
        action="view_settings"
    )
    
    text = f"""
⚙️ <b>Настройки системы</b>

<b>Режим обслуживания:</b> {'🔧 Включен' if settings.maintenance_mode else '✅ Выключен'}
<b>Цена подписки (месяц):</b> {settings.subscription_price_monthly} ₽
<b>Цена подписки (год):</b> {settings.subscription_price_yearly} ₽
<b>Ограничение запросов:</b> {'✅ Включено' if settings.rate_limit_enabled else '❌ Выключено'}

<b>Активные платежные системы:</b>
• YooMoney: {'✅' if settings.yoomoney_wallet else '❌'}
• Telegram Stars: ✅
• СБП: ✅
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔧 Включить обслуживание" if not settings.maintenance_mode else "✅ Выключить обслуживание",
                callback_data="toggle_maintenance"
            )
        ],
        [
            InlineKeyboardButton(text="💰 Изменить цены", callback_data="edit_prices"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="admin_menu")
        ]
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@admin_router.callback_query(F.data == "exit_admin")
async def cb_exit_admin(callback: CallbackQuery):
    """Выход из админ-панели"""
    log_admin_action(
        admin_id=callback.from_user.id,
        action="exit_admin_panel"
    )
    
    from app.bot.keyboards.inline import main_menu_keyboard
    
    text = """
👋 <b>Выход из админ-панели</b>

Вы вышли из режима администратора.
Для повторного входа используйте команду /admin
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer() 