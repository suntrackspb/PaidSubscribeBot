"""
Обработчики для управления подписками в PaidSubscribeBot.
"""

from typing import Optional
from datetime import datetime, timedelta
from decimal import Decimal

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.bot.states.subscription import SubscriptionStates
from app.bot.keyboards.inline import (
    get_subscription_menu_keyboard,
    get_subscription_plans_keyboard,
    get_payment_methods_keyboard
)
from app.bot.utils.texts import MESSAGES
from app.services.user_service import UserService
from app.services.subscription_service import SubscriptionService
from app.services.channel_service import ChannelService
from app.services.notification_service import NotificationService
from app.payments.manager import PaymentManager
from app.database.models.payment import PaymentMethod
from app.utils.logger import get_logger

# Создаем роутер для обработчиков подписок
subscription_router = Router()

# Инициализируем сервисы
user_service = UserService()
subscription_service = SubscriptionService()
channel_service = ChannelService()
notification_service = NotificationService()
payment_manager = PaymentManager()

logger = get_logger("handlers.subscription")


@subscription_router.message(Command("subscription", "sub"))
async def cmd_subscription(message: Message, state: FSMContext):
    """Команда для управления подписками"""
    await state.clear()
    
    # Получаем или создаем пользователя
    user = await user_service.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code
    )
    
    # Обновляем активность
    await user_service.update_user_activity(user.telegram_id)
    
    # Получаем активные подписки пользователя
    subscriptions = await subscription_service.get_user_subscriptions(user.id, active_only=True)
    
    if subscriptions:
        # Показываем информацию об активных подписках
        text = "📋 <b>Ваши активные подписки:</b>\n\n"
        
        for sub in subscriptions:
            # Получаем информацию о канале (нужно будет добавить связь с каналом)
            text += f"🔹 Подписка до: <b>{sub.expires_at.strftime('%d.%m.%Y')}</b>\n"
            days_left = (sub.expires_at - datetime.utcnow()).days
            if days_left <= 3:
                text += f"⚠️ Осталось дней: <b>{days_left}</b>\n"
            text += "\n"
        
        keyboard = get_subscription_menu_keyboard(has_subscription=True)
    else:
        text = MESSAGES["no_subscription"]
        keyboard = get_subscription_menu_keyboard(has_subscription=False)
    
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@subscription_router.callback_query(F.data == "new_subscription")
async def callback_new_subscription(callback: CallbackQuery, state: FSMContext):
    """Создание новой подписки"""
    await callback.answer()
    
    # Получаем доступные планы подписки
    channels = await channel_service.get_all_channels(active_only=True)
    
    if not channels:
        await callback.message.edit_text(
            "❌ <b>Подписки временно недоступны</b>\n\nПопробуйте позже или обратитесь в поддержку.",
            parse_mode="HTML"
        )
        return
    
    # Пока берем первый канал (в будущем можно добавить выбор канала)
    channel = channels[0]
    
    text = f"💳 <b>Выберите план подписки</b>\n\n"
    text += f"📺 Канал: <b>{channel.title}</b>\n"
    if channel.description:
        text += f"📝 {channel.description}\n"
    text += "\n<b>Доступные планы:</b>"
    
    keyboard = get_subscription_plans_keyboard(channel)
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await state.set_state(SubscriptionStates.selecting_plan)
    await state.update_data(channel_id=channel.id)


@subscription_router.callback_query(F.data.startswith("plan_"), SubscriptionStates.selecting_plan)
async def callback_select_plan(callback: CallbackQuery, state: FSMContext):
    """Выбор плана подписки"""
    await callback.answer()
    
    plan_type = callback.data.split("_")[1]  # monthly или yearly
    data = await state.get_data()
    channel_id = data.get("channel_id")
    
    if not channel_id:
        await callback.message.edit_text("❌ Ошибка: канал не выбран")
        return
    
    # Получаем информацию о канале
    channel = await channel_service.get_channel_by_id(channel_id)
    if not channel:
        await callback.message.edit_text("❌ Ошибка: канал не найден")
        return
    
    # Определяем цену и длительность
    if plan_type == "monthly":
        price = Decimal(str(channel.monthly_price or 199))
        duration_days = 30
        plan_name = "Месячная подписка"
    else:  # yearly
        price = Decimal(str(channel.yearly_price or 1990))
        duration_days = 365
        plan_name = "Годовая подписка"
    
    # Сохраняем данные о выбранном плане
    await state.update_data(
        plan_type=plan_type,
        price=float(price),
        duration_days=duration_days,
        plan_name=plan_name
    )
    
    # Показываем методы оплаты
    text = f"💳 <b>Выберите способ оплаты</b>\n\n"
    text += f"📦 План: <b>{plan_name}</b>\n"
    text += f"💰 Стоимость: <b>{price} ₽</b>\n"
    text += f"⏰ Длительность: <b>{duration_days} дней</b>\n\n"
    text += "Выберите удобный способ оплаты:"
    
    # Получаем доступные методы оплаты
    available_methods = payment_manager.get_available_methods()
    keyboard = get_payment_methods_keyboard(available_methods)
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await state.set_state(SubscriptionStates.selecting_payment)


@subscription_router.callback_query(F.data.startswith("pay_"), SubscriptionStates.selecting_payment)
async def callback_select_payment(callback: CallbackQuery, state: FSMContext):
    """Выбор метода оплаты и создание платежа"""
    await callback.answer()
    
    method_name = callback.data.split("_", 1)[1]
    data = await state.get_data()
    
    try:
        # Конвертируем название метода в enum
        payment_method = PaymentMethod(method_name)
    except ValueError:
        await callback.message.edit_text("❌ Неизвестный метод оплаты")
        return
    
    # Получаем пользователя
    user = await user_service.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.edit_text("❌ Ошибка: пользователь не найден")
        return
    
    # Создаем платежный запрос
    from app.payments.base import PaymentRequest
    
    payment_request = PaymentRequest(
        amount=Decimal(str(data["price"])),
        currency="RUB",
        description=f"Подписка: {data['plan_name']}",
        user_id=user.telegram_id,
        return_url="https://t.me/your_bot",  # Заменить на реальный URL
        metadata={
            "user_id": user.id,
            "channel_id": data["channel_id"],
            "plan_type": data["plan_type"],
            "duration_days": data["duration_days"]
        }
    )
    
    try:
        # Создаем платеж через менеджер
        payment_response = await payment_manager.create_payment(payment_method, payment_request)
        
        # Сохраняем ID платежа в состоянии
        await state.update_data(payment_id=payment_response.payment_id)
        
        # Отправляем информацию о платеже
        text = f"💳 <b>Платеж создан</b>\n\n"
        text += f"📦 План: <b>{data['plan_name']}</b>\n"
        text += f"💰 Сумма: <b>{data['price']} ₽</b>\n"
        text += f"💳 Метод: <b>{payment_method.value}</b>\n\n"
        
        if payment_response.payment_url:
            text += "Для оплаты перейдите по ссылке:"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить", url=payment_response.payment_url)],
                [InlineKeyboardButton(text="🔄 Проверить статус", callback_data=f"check_payment_{payment_response.payment_id}")],
                [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_payment")]
            ])
        elif payment_response.qr_code:
            text += "Отсканируйте QR-код для оплаты:"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Проверить статус", callback_data=f"check_payment_{payment_response.payment_id}")],
                [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_payment")]
            ])
            # TODO: Отправить QR-код как изображение
        else:
            text += f"ID платежа: <code>{payment_response.payment_id}</code>"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Проверить статус", callback_data=f"check_payment_{payment_response.payment_id}")],
                [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_payment")]
            ])
        
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await state.set_state(SubscriptionStates.waiting_payment)
        
        logger.info(
            "Создан платеж для подписки",
            user_id=user.telegram_id,
            payment_id=payment_response.payment_id,
            amount=float(payment_request.amount),
            method=payment_method.value
        )
        
    except Exception as e:
        logger.error("Ошибка создания платежа", error=str(e), user_id=user.telegram_id)
        await callback.message.edit_text(
            f"❌ <b>Ошибка создания платежа</b>\n\n{str(e)}\n\nПопробуйте другой способ оплаты или обратитесь в поддержку.",
            parse_mode="HTML"
        )


@subscription_router.callback_query(F.data.startswith("check_payment_"))
async def callback_check_payment(callback: CallbackQuery, state: FSMContext):
    """Проверка статуса платежа"""
    await callback.answer()
    
    payment_id = callback.data.split("_", 2)[2]
    data = await state.get_data()
    
    # Получаем метод оплаты из данных состояния
    # TODO: Нужно сохранять метод оплаты в состоянии
    
    try:
        # Проверяем статус платежа через все доступные методы
        # (в реальном проекте нужно знать конкретный метод)
        for method in payment_manager.get_available_methods():
            try:
                status_data = await payment_manager.check_payment_status(method, payment_id)
                
                if status_data.status == "completed":
                    # Платеж успешен - создаем подписку
                    await process_successful_payment(callback, state, status_data, data)
                    return
                elif status_data.status == "failed":
                    await callback.message.edit_text(
                        f"❌ <b>Платеж отклонен</b>\n\n"
                        f"Причина: {status_data.failure_reason or 'Неизвестная ошибка'}\n\n"
                        "Попробуйте еще раз или выберите другой способ оплаты.",
                        parse_mode="HTML"
                    )
                    return
                elif status_data.status == "pending":
                    await callback.answer("⏳ Платеж обрабатывается. Подождите немного.", show_alert=True)
                    return
                    
            except Exception as e:
                continue  # Пробуем следующий метод
        
        await callback.answer("❓ Не удалось проверить статус платежа", show_alert=True)
        
    except Exception as e:
        logger.error("Ошибка проверки платежа", error=str(e), payment_id=payment_id)
        await callback.answer("❌ Ошибка проверки платежа", show_alert=True)


async def process_successful_payment(callback: CallbackQuery, state: FSMContext, status_data, subscription_data):
    """Обработка успешного платежа"""
    user = await user_service.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.edit_text("❌ Ошибка: пользователь не найден")
        return
    
    try:
        # Создаем подписку
        subscription = await subscription_service.create_subscription(
            user_id=user.id,
            channel_id=subscription_data["channel_id"],
            duration_days=subscription_data["duration_days"],
            price=Decimal(str(subscription_data["price"]))
        )
        
        # Активируем подписку
        await subscription_service.activate_subscription(subscription.id)
        
        # Получаем информацию о канале
        channel = await channel_service.get_channel_by_id(subscription_data["channel_id"])
        
        # Добавляем пользователя в канал
        if channel:
            await channel_service.add_user_to_channel(
                user_telegram_id=user.telegram_id,
                channel_telegram_id=channel.telegram_id
            )
        
        # Отправляем уведомление об успешной оплате
        await notification_service.send_payment_success_notification(
            user=user,
            payment=status_data,  # Нужно будет адаптировать под модель Payment
            subscription=subscription
        )
        
        # Очищаем состояние
        await state.clear()
        
        text = f"✅ <b>Подписка успешно оформлена!</b>\n\n"
        text += f"📦 План: <b>{subscription_data['plan_name']}</b>\n"
        text += f"📅 Действует до: <b>{subscription.expires_at.strftime('%d.%m.%Y')}</b>\n\n"
        text += "Добро пожаловать в канал! 🎉"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Перейти в канал", url=f"https://t.me/{channel.username}" if channel and channel.username else "https://t.me/your_channel")],
            [InlineKeyboardButton(text="📋 Мои подписки", callback_data="my_subscriptions")]
        ])
        
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        
        logger.info(
            "Подписка успешно создана",
            user_id=user.telegram_id,
            subscription_id=subscription.id,
            channel_id=channel.id if channel else None
        )
        
    except Exception as e:
        logger.error("Ошибка создания подписки", error=str(e), user_id=user.telegram_id)
        await callback.message.edit_text(
            "❌ <b>Ошибка при создании подписки</b>\n\nОбратитесь в поддержку.",
            parse_mode="HTML"
        )


@subscription_router.callback_query(F.data == "my_subscriptions")
async def callback_my_subscriptions(callback: CallbackQuery):
    """Просмотр моих подписок"""
    await callback.answer()
    
    user = await user_service.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.edit_text("❌ Ошибка: пользователь не найден")
        return
    
    subscriptions = await subscription_service.get_user_subscriptions(user.id, active_only=False)
    
    if not subscriptions:
        text = "📋 <b>У вас нет подписок</b>\n\nОформите подписку для доступа к каналу."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оформить подписку", callback_data="new_subscription")]
        ])
    else:
        text = "📋 <b>Ваши подписки:</b>\n\n"
        
        for i, sub in enumerate(subscriptions, 1):
            status = "🟢 Активна" if sub.is_active and sub.expires_at > datetime.utcnow() else "🔴 Неактивна"
            text += f"{i}. {status}\n"
            text += f"   📅 До: {sub.expires_at.strftime('%d.%m.%Y')}\n"
            text += f"   💰 Цена: {sub.price} ₽\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Продлить подписку", callback_data="new_subscription")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="subscription_menu")]
        ])
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)


@subscription_router.callback_query(F.data == "cancel_payment")
async def callback_cancel_payment(callback: CallbackQuery, state: FSMContext):
    """Отмена платежа"""
    await callback.answer()
    await state.clear()
    
    text = "❌ <b>Платеж отменен</b>\n\nВы можете оформить подписку в любое время."
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оформить подписку", callback_data="new_subscription")]
    ])
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)


@subscription_router.callback_query(F.data == "subscription_menu")
async def callback_subscription_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в меню подписок"""
    await callback.answer()
    await state.clear()
    
    # Переадресация на основную команду
    await cmd_subscription(callback.message, state) 