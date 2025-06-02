"""
Точка входа в приложение PaidSubscribeBot.
Инициализация и запуск Telegram бота.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

# Добавляем корневую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.settings import get_settings
from app.config.database import init_database, close_database
from app.utils.logger import setup_logging, get_logger
from app.bot.handlers import start
from app.bot.handlers import payments  # Добавляем импорт платежей

# Инициализируем логгер
logger = get_logger(__name__)

async def create_bot() -> Bot:
    """
    Создание экземпляра бота.
    
    Returns:
        Bot: Экземпляр Telegram бота
    """
    settings = get_settings()
    
    # Создаем бота с настройками по умолчанию
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            protect_content=False,
        )
    )
    
    return bot


async def create_dispatcher() -> Dispatcher:
    """
    Создание диспетчера с подключенными роутерами.
    
    Returns:
        Dispatcher: Настроенный диспетчер
    """
    # Создаем диспетчер с хранилищем в памяти
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Подключаем роутеры
    dp.include_router(start.router)
    dp.include_router(payments.router)  # Добавляем роутер платежей
    
    return dp


async def setup_bot_commands(bot: Bot) -> None:
    """
    Настройка команд бота в меню.
    
    Args:
        bot: Экземпляр бота
    """
    from aiogram.types import BotCommand, BotCommandScopeDefault
    
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="help", description="📖 Справка"),
        BotCommand(command="subscription", description="📋 Моя подписка"),
        BotCommand(command="pay", description="💳 Оплатить подписку"),
        BotCommand(command="support", description="🆘 Поддержка"),
    ]
    
    await bot.set_my_commands(commands, BotCommandScopeDefault())


async def setup_admin_commands(bot: Bot) -> None:
    """
    Настройка админских команд.
    
    Args:
        bot: Экземпляр бота
    """
    from aiogram.types import BotCommand, BotCommandScopeChat
    
    settings = get_settings()
    
    admin_commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="help", description="📖 Справка"),
        BotCommand(command="subscription", description="📋 Моя подписка"),
        BotCommand(command="pay", description="💳 Оплатить подписку"),
        BotCommand(command="support", description="🆘 Поддержка"),
        BotCommand(command="admin", description="👑 Панель администратора"),
        BotCommand(command="stats", description="📊 Статистика"),
        BotCommand(command="users", description="👥 Пользователи"),
        BotCommand(command="broadcast", description="📢 Рассылка"),
        BotCommand(command="settings", description="⚙️ Настройки"),
    ]
    
    # Устанавливаем команды для каждого администратора
    for admin_id in settings.admin_ids:
        try:
            await bot.set_my_commands(
                admin_commands,
                BotCommandScopeChat(chat_id=admin_id)
            )
        except Exception as e:
            logger.warning(f"Не удалось установить команды для админа {admin_id}: {e}")


async def on_startup(bot: Bot, dispatcher: Dispatcher) -> None:
    """
    Действия при запуске бота.
    
    Args:
        bot: Экземпляр бота
        dispatcher: Диспетчер
    """
    settings = get_settings()
    
    logger.info("Запуск PaidSubscribeBot...")
    
    # Инициализация базы данных
    try:
        await init_database()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}")
        raise
    
    # Настройка команд бота
    try:
        await setup_bot_commands(bot)
        await setup_admin_commands(bot)
        logger.info("Команды бота настроены")
    except Exception as e:
        logger.error(f"Ошибка настройки команд: {e}")
    
    # Получение информации о боте
    try:
        bot_info = await bot.get_me()
        logger.info(
            "Бот запущен",
            bot_id=bot_info.id,
            bot_username=bot_info.username,
            bot_name=bot_info.first_name
        )
    except Exception as e:
        logger.error(f"Ошибка получения информации о боте: {e}")
        raise
    
    # Уведомление администраторов о запуске
    startup_message = f"🤖 <b>PaidSubscribeBot запущен!</b>\n\n" \
                     f"<b>Версия:</b> 1.0.0\n" \
                     f"<b>Время запуска:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n" \
                     f"<b>Режим:</b> {'🔧 Техническое обслуживание' if settings.maintenance_mode else '✅ Рабочий'}"
    
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, startup_message, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление админу {admin_id}: {e}")


async def on_shutdown(bot: Bot, dispatcher: Dispatcher) -> None:
    """
    Действия при остановке бота.
    
    Args:
        bot: Экземпляр бота
        dispatcher: Диспетчер
    """
    logger.info("Остановка PaidSubscribeBot...")
    
    # Закрытие соединения с базой данных
    try:
        await close_database()
        logger.info("Соединения с базой данных закрыты")
    except Exception as e:
        logger.error(f"Ошибка закрытия базы данных: {e}")
    
    # Уведомление администраторов об остановке
    settings = get_settings()
    shutdown_message = f"🔴 <b>PaidSubscribeBot остановлен</b>\n\n" \
                      f"<b>Время остановки:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
    
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, shutdown_message, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление об остановке админу {admin_id}: {e}")
    
    # Закрытие сессии бота
    await bot.session.close()


async def main() -> None:
    """Основная функция запуска приложения"""
    
    # Настройка логирования
    global logger
    logger = setup_logging()
    
    try:
        # Создание бота и диспетчера
        bot = await create_bot()
        dp = await create_dispatcher()
        
        # Регистрация startup и shutdown хуков
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        # Запуск поллинга
        logger.info("Запуск поллинга...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("PaidSubscribeBot остановлен")


if __name__ == "__main__":
    # Проверка версии Python
    if sys.version_info < (3, 9):
        print("❌ Требуется Python 3.9 или выше")
        sys.exit(1)
    
    # Проверка наличия файла .env
    if not Path(".env").exists():
        print("❌ Файл .env не найден!")
        print("Скопируйте env.example в .env и настройте переменные окружения")
        sys.exit(1)
    
    try:
        # Запуск приложения
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🔴 Остановка по Ctrl+C")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1) 