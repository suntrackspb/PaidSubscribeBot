"""
Обработчики платежей для PaidSubscribeBot.
Обрабатывают создание платежей, выбор способов оплаты и успешные платежи.
"""

from decimal import Decimal
from typing import Optional

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery
from aiogram.filters import Command

from app.bot.keyboards.inline import (
    get_payment_methods_keyboard,
    get_subscription_plans_keyboard,
    get_main_menu_keyboard
)
from app.bot.utils.texts import (
    PAYMENT_METHODS_TEXT,
    PAYMENT_CREATED_TEXT,
    PAYMENT_ERROR_TEXT,
    PAYMENT_SUCCESS_TEXT,
    SUBSCRIPTION_PLANS_TEXT
)
from app.payments.manager import payment_manager
from app.payments.base import PaymentRequest, PaymentProviderError
from app.database.models.payment import PaymentMethod
from app.utils.logger import get_logger

router = Router()
logger = get_logger("bot.payments")


@router.message(Command("pay", "payment", "subscribe"))
async def cmd_payment(message: Message):
    """Команда для начала процесса оплаты"""
    try:
        # Показываем тарифные планы
        keyboard = get_subscription_plans_keyboard()
        await message.answer(
            SUBSCRIPTION_PLANS_TEXT,
            reply_markup=keyboard
        )
        
        logger.info(
            "Пользователь запросил оплату",
            user_id=message.from_user.id,
            username=message.from_user.username
        )
        
    except Exception as e:
        logger.error(
            "Ошибка обработки команды оплаты",
            user_id=message.from_user.id,
            error=str(e)
        )
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.callback_query(F.data.startswith("subscription_"))
async def process_subscription_selection(callback: CallbackQuery):
    """Обработка выбора тарифного плана"""
    try:
        await callback.answer()
        
        # Извлекаем тип подписки из callback_data
        subscription_type = callback.data.split("_")[1]
        
        # Определяем цену в зависимости от типа
        prices = {
            "basic": 199,
            "premium": 499,
            "vip": 999
        }
        
        price = prices.get(subscription_type, 199)
        
        # Сохраняем выбор пользователя (в реальном приложении - в базе данных)
        # Здесь используем простое хранение в callback_data
        
        # Показываем способы оплаты
        available_methods = payment_manager.get_available_methods()
        keyboard = get_payment_methods_keyboard(available_methods, subscription_type, price)
        
        await callback.message.edit_text(
            PAYMENT_METHODS_TEXT.format(
                plan=subscription_type.title(),
                price=price
            ),
            reply_markup=keyboard
        )
        
        logger.info(
            "Пользователь выбрал тарифный план",
            user_id=callback.from_user.id,
            subscription_type=subscription_type,
            price=price
        )
        
    except Exception as e:
        logger.error(
            "Ошибка обработки выбора подписки",
            user_id=callback.from_user.id,
            error=str(e)
        )
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("pay_"))
async def process_payment_method_selection(callback: CallbackQuery):
    """Обработка выбора способа оплаты"""
    try:
        await callback.answer()
        
        # Парсим данные: pay_method_subscription_price
        parts = callback.data.split("_")
        method_str = parts[1]
        subscription_type = parts[2]
        price = int(parts[3])
        
        # Получаем метод оплаты
        method_mapping = {
            "yoomoney": PaymentMethod.YOOMONEY,
            "stars": PaymentMethod.TELEGRAM_STARS,
            "sbp": PaymentMethod.SBP,
            "card": PaymentMethod.BANK_CARD
        }
        
        payment_method = method_mapping.get(method_str)
        if not payment_method:
            await callback.answer("❌ Неизвестный способ оплаты", show_alert=True)
            return
        
        # Проверяем доступность метода
        if not payment_manager.is_method_available(payment_method):
            await callback.answer("❌ Этот способ оплаты временно недоступен", show_alert=True)
            return
        
        # Создаем платеж
        payment_request = PaymentRequest(
            amount=Decimal(str(price)),
            currency="RUB",
            description=f"Подписка {subscription_type.title()}",
            user_id=callback.from_user.id,
            metadata={
                "subscription_type": subscription_type,
                "user_id": callback.from_user.id,
                "username": callback.from_user.username
            }
        )
        
        try:
            payment_response = await payment_manager.create_payment(payment_method, payment_request)
            
            # Обрабатываем ответ в зависимости от метода оплаты
            if payment_method == PaymentMethod.TELEGRAM_STARS:
                # Для Telegram Stars отправляем инвойс
                provider = payment_manager.get_provider(payment_method)
                if provider and hasattr(provider, 'send_invoice_to_user'):
                    success = await provider.send_invoice_to_user(
                        callback.from_user.id,
                        payment_response.metadata
                    )
                    if success:
                        await callback.message.edit_text(
                            "⭐ Инвойс отправлен! Проверьте сообщения от бота.",
                            reply_markup=get_main_menu_keyboard()
                        )
                    else:
                        await callback.message.edit_text(
                            "❌ Ошибка отправки инвойса. Попробуйте позже.",
                            reply_markup=get_main_menu_keyboard()
                        )
                
            elif payment_method == PaymentMethod.SBP:
                # Для СБП показываем QR-код
                text = PAYMENT_CREATED_TEXT.format(
                    method="СБП",
                    amount=price,
                    payment_id=payment_response.payment_id[:8]
                )
                
                if payment_response.qr_code_url:
                    # В реальном боте здесь бы отправлялось изображение QR-кода
                    text += "\n\n📱 QR-код для оплаты создан. Отсканируйте его в банковском приложении."
                
                if payment_response.payment_url:
                    text += f"\n\n🔗 [Открыть в банковском приложении]({payment_response.payment_url})"
                
                await callback.message.edit_text(
                    text,
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode="Markdown"
                )
                
            else:
                # Для других методов показываем ссылку на оплату
                text = PAYMENT_CREATED_TEXT.format(
                    method=payment_manager.get_provider(payment_method).name,
                    amount=price,
                    payment_id=payment_response.payment_id[:8]
                )
                
                if payment_response.payment_url:
                    text += f"\n\n🔗 [Перейти к оплате]({payment_response.payment_url})"
                
                await callback.message.edit_text(
                    text,
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode="Markdown"
                )
            
            logger.info(
                "Платеж создан",
                user_id=callback.from_user.id,
                payment_method=payment_method.value,
                payment_id=payment_response.payment_id,
                amount=price
            )
            
        except PaymentProviderError as e:
            await callback.message.edit_text(
                PAYMENT_ERROR_TEXT.format(error=str(e)),
                reply_markup=get_main_menu_keyboard()
            )
            
            logger.error(
                "Ошибка создания платежа",
                user_id=callback.from_user.id,
                payment_method=payment_method.value,
                error=str(e)
            )
        
    except Exception as e:
        logger.error(
            "Ошибка обработки выбора способа оплаты",
            user_id=callback.from_user.id,
            error=str(e)
        )
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """Обработка pre_checkout_query для Telegram Stars"""
    try:
        # Для Telegram Stars всегда подтверждаем платеж
        await pre_checkout_query.answer(ok=True)
        
        logger.info(
            "Pre-checkout query обработан",
            user_id=pre_checkout_query.from_user.id,
            total_amount=pre_checkout_query.total_amount,
            currency=pre_checkout_query.currency
        )
        
    except Exception as e:
        logger.error(
            "Ошибка обработки pre_checkout_query",
            user_id=pre_checkout_query.from_user.id,
            error=str(e)
        )
        await pre_checkout_query.answer(ok=False, error_message="Произошла ошибка")


@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """Обработка успешного платежа Telegram Stars"""
    try:
        payment = message.successful_payment
        
        # Обрабатываем платеж через менеджер
        payment_data = {
            "telegram_payment_charge_id": payment.telegram_payment_charge_id,
            "total_amount": payment.total_amount,
            "currency": payment.currency,
            "invoice_payload": payment.invoice_payload
        }
        
        try:
            payment_id, status_data = await payment_manager.process_webhook(
                PaymentMethod.TELEGRAM_STARS,
                payment_data
            )
            
            # Здесь должна быть логика активации подписки
            # В реальном приложении - обновление базы данных
            
            await message.answer(
                PAYMENT_SUCCESS_TEXT.format(
                    amount=payment.total_amount,
                    currency="⭐"
                ),
                reply_markup=get_main_menu_keyboard()
            )
            
            logger.info(
                "Успешный платеж Telegram Stars обработан",
                user_id=message.from_user.id,
                payment_id=payment_id,
                amount=payment.total_amount
            )
            
        except PaymentProviderError as e:
            logger.error(
                "Ошибка обработки успешного платежа",
                user_id=message.from_user.id,
                error=str(e)
            )
            await message.answer("❌ Ошибка обработки платежа. Обратитесь в поддержку.")
        
    except Exception as e:
        logger.error(
            "Ошибка обработки successful_payment",
            user_id=message.from_user.id,
            error=str(e)
        )
        await message.answer("❌ Произошла ошибка. Обратитесь в поддержку.") 