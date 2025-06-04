"""
Обработчики команд /start, /help для PaidSubscribeBot.
Содержит основные команды взаимодействия с ботом.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from app.bot.keyboards.inline import main_menu_keyboard, back_button
from app.bot.utils.texts import Messages
from app.config.settings import get_settings
from app.utils.logger import get_logger, log_user_action
from app.services.user_service import UserService
from app.bot.handlers.referral import process_referral_start

# Создаем роутер для обработчиков
router = Router()
logger = get_logger("handlers.start")
settings = get_settings()

# Инициализируем сервисы
user_service = UserService()


@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext) -> None:
    """
    Обработчик команды /start.
    Приветственное сообщение и главное меню.
    """
    user = message.from_user
    
    # Логируем действие пользователя
    log_user_action(
        user_id=user.id,
        action="start_command",
        username=user.username,
        first_name=user.first_name
    )
    
    # Очищаем состояние FSM
    await state.clear()
    
    try:
        # Проверяем, не заблокирован ли пользователь
        if await _is_user_banned(user.id):
            await message.answer(Messages.ERROR_USER_BANNED)
            return
        
        # Проверяем режим технического обслуживания
        if settings.maintenance_mode and user.id not in settings.admin_ids:
            await message.answer(settings.maintenance_message)
            return
        
        # Создаем или обновляем пользователя в базе данных
        await user_service.create_or_update_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code
        )
        
        # Обрабатываем реферальный код, если есть
        command_args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        if command_args:
            referral_code = command_args[0]
            await process_referral_start(user.id, referral_code)
        
        # Отправляем приветственное сообщение
        await message.answer(
            Messages.START_MESSAGE,
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        
        logger.info(
            "Пользователь запустил бота",
            user_id=user.id,
            username=user.username
        )
        
    except Exception as e:
        logger.error(
            "Ошибка в обработчике /start",
            user_id=user.id,
            error=str(e),
            exc_info=True
        )
        await message.answer(Messages.ERROR_GENERAL)


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    """
    Обработчик команды /help.
    Справочная информация о боте.
    """
    user = message.from_user
    
    log_user_action(
        user_id=user.id,
        action="help_command"
    )
    
    try:
        await message.answer(
            Messages.HELP_MESSAGE,
            reply_markup=back_button("back_to_main"),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(
            "Ошибка в обработчике /help",
            user_id=user.id,
            error=str(e),
            exc_info=True
        )
        await message.answer(Messages.ERROR_GENERAL)


@router.message(Command("support"))
async def support_command(message: Message) -> None:
    """
    Обработчик команды /support.
    Информация о поддержке.
    """
    user = message.from_user
    
    log_user_action(
        user_id=user.id,
        action="support_command"
    )
    
    try:
        await message.answer(
            Messages.SUPPORT_MESSAGE,
            reply_markup=back_button("back_to_main"),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(
            "Ошибка в обработчике /support",
            user_id=user.id,
            error=str(e),
            exc_info=True
        )
        await message.answer(Messages.ERROR_GENERAL)


@router.callback_query(F.data == "back_to_main")
async def back_to_main_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик кнопки "Назад в главное меню".
    """
    user = callback.from_user
    
    log_user_action(
        user_id=user.id,
        action="back_to_main"
    )
    
    # Очищаем состояние FSM
    await state.clear()
    
    try:
        await callback.message.edit_text(
            Messages.START_MESSAGE,
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(
            "Ошибка в обработчике back_to_main",
            user_id=user.id,
            error=str(e),
            exc_info=True
        )
        await callback.answer("Произошла ошибка")


@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery) -> None:
    """
    Обработчик кнопки "Справка".
    """
    user = callback.from_user
    
    log_user_action(
        user_id=user.id,
        action="help_button"
    )
    
    try:
        await callback.message.edit_text(
            Messages.HELP_MESSAGE,
            reply_markup=back_button("back_to_main"),
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(
            "Ошибка в обработчике help callback",
            user_id=user.id,
            error=str(e),
            exc_info=True
        )
        await callback.answer("Произошла ошибка")


@router.callback_query(F.data == "support")
async def support_callback(callback: CallbackQuery) -> None:
    """
    Обработчик кнопки "Поддержка".
    """
    user = callback.from_user
    
    log_user_action(
        user_id=user.id,
        action="support_button"
    )
    
    try:
        await callback.message.edit_text(
            Messages.SUPPORT_MESSAGE,
            reply_markup=back_button("back_to_main"),
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(
            "Ошибка в обработчике support callback",
            user_id=user.id,
            error=str(e),
            exc_info=True
        )
        await callback.answer("Произошла ошибка")


@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик кнопки "Главное меню".
    """
    user = callback.from_user
    
    log_user_action(
        user_id=user.id,
        action="main_menu"
    )
    
    # Очищаем состояние FSM
    await state.clear()
    
    try:
        await callback.message.edit_text(
            Messages.START_MESSAGE,
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(
            "Ошибка в обработчике main_menu",
            user_id=user.id,
            error=str(e),
            exc_info=True
        )
        await callback.answer("Произошла ошибка")


async def _is_user_banned(user_id: int) -> bool:
    """
    Проверка заблокирован ли пользователь.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        bool: True если пользователь заблокирован
    """
    # TODO: Реализовать проверку в базе данных
    # Пока возвращаем False
    return False 