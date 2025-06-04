import asyncio
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.bot.middlewares.auth import AdminRequiredMiddleware
from app.bot.utils.texts import AdminTexts
from app.services.export_service import export_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Создаем роутер для экспорта
export_router = Router()
export_router.message.middleware(AdminRequiredMiddleware())
export_router.callback_query.middleware(AdminRequiredMiddleware())

class ExportStates(StatesGroup):
    """Состояния для экспорта данных"""
    waiting_for_period = State()
    waiting_for_format = State()
    waiting_for_filters = State()

def get_export_main_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура главного меню экспорта"""
    keyboard = [
        [
            InlineKeyboardButton(text="👥 Пользователи", callback_data="export_users"),
            InlineKeyboardButton(text="📋 Подписки", callback_data="export_subscriptions")
        ],
        [
            InlineKeyboardButton(text="💳 Платежи", callback_data="export_payments"),
            InlineKeyboardButton(text="📊 Аналитика", callback_data="export_analytics")
        ],
        [
            InlineKeyboardButton(text="💾 Полный бэкап", callback_data="export_full_backup"),
            InlineKeyboardButton(text="🔄 Авто-бэкап", callback_data="export_auto_backup")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад в админ", callback_data="admin_main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_format_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора формата экспорта"""
    keyboard = [
        [
            InlineKeyboardButton(text="📄 CSV", callback_data="format_csv"),
            InlineKeyboardButton(text="📊 JSON", callback_data="format_json")
        ],
        [
            InlineKeyboardButton(text="📈 Excel", callback_data="format_excel")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="export_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_period_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора периода экспорта"""
    keyboard = [
        [
            InlineKeyboardButton(text="📅 За сегодня", callback_data="period_today"),
            InlineKeyboardButton(text="📅 За неделю", callback_data="period_week")
        ],
        [
            InlineKeyboardButton(text="📅 За месяц", callback_data="period_month"),
            InlineKeyboardButton(text="📅 За год", callback_data="period_year")
        ],
        [
            InlineKeyboardButton(text="📅 Всё время", callback_data="period_all"),
            InlineKeyboardButton(text="📅 Свой период", callback_data="period_custom")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="export_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@export_router.callback_query(F.data == "admin_export")
async def admin_export_menu(callback: CallbackQuery, state: FSMContext):
    """Главное меню экспорта данных"""
    await state.clear()
    
    text = AdminTexts.EXPORT_MENU
    await callback.message.edit_text(
        text=text,
        reply_markup=get_export_main_keyboard()
    )

@export_router.callback_query(F.data.startswith("export_"))
async def handle_export_type(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора типа экспорта"""
    export_type = callback.data.replace("export_", "")
    
    if export_type == "menu":
        await admin_export_menu(callback, state)
        return
    
    if export_type == "full_backup":
        await create_full_backup(callback)
        return
    
    if export_type == "auto_backup":
        await schedule_auto_backup(callback)
        return
    
    # Сохраняем тип экспорта в состоянии
    await state.update_data(export_type=export_type)
    
    # Предлагаем выбрать формат
    text = f"📤 **Экспорт данных**\n\n"
    text += f"Выбрано: {export_type.replace('_', ' ').title()}\n\n"
    text += "Выберите формат экспорта:"
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_format_keyboard()
    )

@export_router.callback_query(F.data.startswith("format_"))
async def handle_format_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора формата"""
    format_type = callback.data.replace("format_", "")
    data = await state.get_data()
    
    await state.update_data(format=format_type)
    
    # Предлагаем выбрать период
    text = f"📤 **Экспорт данных**\n\n"
    text += f"Тип: {data['export_type'].replace('_', ' ').title()}\n"
    text += f"Формат: {format_type.upper()}\n\n"
    text += "Выберите период для экспорта:"
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_period_keyboard()
    )

@export_router.callback_query(F.data.startswith("period_"))
async def handle_period_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора периода"""
    period = callback.data.replace("period_", "")
    data = await state.get_data()
    
    # Определяем даты
    end_date = datetime.utcnow()
    start_date = None
    
    if period == "today":
        start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = end_date - timedelta(days=7)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    elif period == "year":
        start_date = end_date - timedelta(days=365)
    elif period == "all":
        start_date = None
        end_date = None
    elif period == "custom":
        await callback.message.edit_text(
            "📅 Введите период в формате:\n"
            "`ДД.ММ.ГГГГ-ДД.ММ.ГГГГ`\n"
            "Например: `01.01.2024-31.01.2024`\n\n"
            "Или отправьте 'all' для экспорта всех данных",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔙 Назад", callback_data="export_" + data['export_type'])
            ]])
        )
        await state.set_state(ExportStates.waiting_for_period)
        return
    
    # Выполняем экспорт
    await perform_export(callback, state, start_date, end_date)

@export_router.message(ExportStates.waiting_for_period)
async def handle_custom_period(message: Message, state: FSMContext):
    """Обработка пользовательского периода"""
    data = await state.get_data()
    
    try:
        if message.text.lower() == "all":
            start_date = None
            end_date = None
        else:
            # Парсим формат ДД.ММ.ГГГГ-ДД.ММ.ГГГГ
            dates = message.text.split("-")
            if len(dates) != 2:
                raise ValueError("Неверный формат")
            
            start_str, end_str = dates
            start_date = datetime.strptime(start_str.strip(), "%d.%m.%Y")
            end_date = datetime.strptime(end_str.strip(), "%d.%m.%Y")
            end_date = end_date.replace(hour=23, minute=59, second=59)
        
        # Выполняем экспорт
        await perform_export(message, state, start_date, end_date)
        
    except Exception as e:
        await message.reply(
            "❌ Неверный формат даты!\n"
            "Используйте формат: `ДД.ММ.ГГГГ-ДД.ММ.ГГГГ`\n"
            "Или отправьте 'all' для всех данных"
        )

async def perform_export(
    event, 
    state: FSMContext, 
    start_date: Optional[datetime], 
    end_date: Optional[datetime]
):
    """Выполнение экспорта данных"""
    data = await state.get_data()
    export_type = data['export_type']
    format_type = data['format']
    
    # Отправляем сообщение о начале экспорта
    if hasattr(event, 'message'):
        message = event.message
    else:
        message = event
    
    status_message = await message.answer("⏳ Создание экспорта, пожалуйста подождите...")
    
    try:
        # Выполняем экспорт в зависимости от типа
        if export_type == "users":
            export_data = await export_service.export_users(
                format_type=format_type,
                start_date=start_date,
                end_date=end_date
            )
        elif export_type == "subscriptions":
            export_data = await export_service.export_subscriptions(
                format_type=format_type,
                start_date=start_date,
                end_date=end_date
            )
        elif export_type == "payments":
            export_data = await export_service.export_payments(
                format_type=format_type,
                start_date=start_date,
                end_date=end_date
            )
        elif export_type == "analytics":
            export_data = await export_service.export_analytics(
                format_type=format_type,
                start_date=start_date,
                end_date=end_date
            )
        else:
            raise ValueError(f"Неизвестный тип экспорта: {export_type}")
        
        # Подготавливаем файл для отправки
        period_str = ""
        if start_date and end_date:
            period_str = f"_{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}"
        elif start_date:
            period_str = f"_from_{start_date.strftime('%Y%m%d')}"
        
        filename = f"{export_type}{period_str}.{format_type}"
        
        if isinstance(export_data, str):
            file_data = export_data.encode('utf-8')
        else:
            file_data = export_data
        
        # Отправляем файл
        document = BufferedInputFile(file_data, filename)
        
        await status_message.delete()
        
        caption = f"📤 **Экспорт завершен**\n\n"
        caption += f"**Тип:** {export_type.replace('_', ' ').title()}\n"
        caption += f"**Формат:** {format_type.upper()}\n"
        if start_date:
            caption += f"**Период:** {start_date.strftime('%d.%m.%Y')}"
            if end_date:
                caption += f" - {end_date.strftime('%d.%m.%Y')}"
            caption += "\n"
        else:
            caption += f"**Период:** Все время\n"
        caption += f"**Размер:** {len(file_data)} байт"
        
        await message.answer_document(
            document=document,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Повторить экспорт", callback_data="export_menu"),
                InlineKeyboardButton(text="🔙 В админ", callback_data="admin_main")
            ]])
        )
        
        logger.info(f"Экспорт {export_type} в формате {format_type} выполнен")
        
    except Exception as e:
        await status_message.delete()
        await message.answer(
            f"❌ Ошибка при создании экспорта:\n{str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="export_menu")
            ]])
        )
        logger.error(f"Ошибка экспорта {export_type}: {e}")
    
    await state.clear()

async def create_full_backup(callback: CallbackQuery):
    """Создание полного бэкапа"""
    status_message = await callback.message.edit_text("⏳ Создание полного бэкапа...")
    
    try:
        backup_data = await export_service.create_full_backup()
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"full_backup_{timestamp}.zip"
        
        document = BufferedInputFile(backup_data, filename)
        
        caption = f"💾 **Полный бэкап создан**\n\n"
        caption += f"**Дата:** {datetime.utcnow().strftime('%d.%m.%Y %H:%M')}\n"
        caption += f"**Размер:** {len(backup_data)} байт\n"
        caption += f"**Содержимое:** Пользователи, подписки, платежи, аналитика"
        
        await callback.message.answer_document(
            document=document,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Создать еще", callback_data="export_full_backup"),
                InlineKeyboardButton(text="🔙 В меню", callback_data="export_menu")
            ]])
        )
        
        await status_message.delete()
        logger.info("Полный бэкап создан")
        
    except Exception as e:
        await status_message.edit_text(
            f"❌ Ошибка создания бэкапа:\n{str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="export_full_backup")
            ]])
        )
        logger.error(f"Ошибка создания бэкапа: {e}")

async def schedule_auto_backup(callback: CallbackQuery):
    """Запуск автоматического бэкапа"""
    status_message = await callback.message.edit_text("⏳ Создание автоматического бэкапа...")
    
    try:
        result = await export_service.schedule_automatic_backup()
        
        if result["success"]:
            text = f"✅ **Автоматический бэкап создан**\n\n"
            text += f"**Файл:** {result['backup_path']}\n"
            text += f"**Размер:** {result['backup_size']} байт\n"
            text += f"**Время:** {datetime.fromisoformat(result['created_at']).strftime('%d.%m.%Y %H:%M')}"
        else:
            text = f"❌ **Ошибка создания бэкапа**\n\n"
            text += f"**Ошибка:** {result['error']}"
        
        await status_message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Создать еще", callback_data="export_auto_backup"),
                InlineKeyboardButton(text="🔙 В меню", callback_data="export_menu")
            ]])
        )
        
        logger.info(f"Автоматический бэкап: {result}")
        
    except Exception as e:
        await status_message.edit_text(
            f"❌ Ошибка создания автоматического бэкапа:\n{str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="export_auto_backup")
            ]])
        )
        logger.error(f"Ошибка автоматического бэкапа: {e}")

# Команда для быстрого доступа к экспорту
@export_router.message(Command("export"))
async def export_command(message: Message, state: FSMContext):
    """Команда для быстрого доступа к экспорту"""
    await state.clear()
    
    text = AdminTexts.EXPORT_MENU
    await message.answer(
        text=text,
        reply_markup=get_export_main_keyboard()
    ) 