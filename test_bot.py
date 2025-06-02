#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы PaidBot
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

# Импортируем тестовые настройки
import test_config

async def test_bot():
    """Тестирование основных компонентов бота"""
    
    print("🤖 Тестирование PaidBot...")
    
    try:
        # Тестируем настройки
        print("📋 Проверка настроек...")
        from app.config.settings import get_settings
        settings = get_settings()
        print(f"✅ Настройки загружены: {settings.telegram_bot_token[:10]}...")
        
        # Тестируем логгер
        print("📝 Проверка логгера...")
        from app.utils.logger import setup_logging, get_logger
        logger = setup_logging()
        logger.info("Тестовое сообщение логгера")
        print("✅ Логгер работает")
        
        # Тестируем базу данных
        print("🗄️ Проверка базы данных...")
        from app.config.database import init_database
        await init_database()
        print("✅ База данных инициализирована")
        
        # Тестируем создание бота (без запуска)
        print("🤖 Проверка создания бота...")
        from app.main import create_bot, create_dispatcher
        bot = await create_bot()
        dp = await create_dispatcher()
        print("✅ Бот создан успешно")
        
        # Закрываем сессию бота
        await bot.session.close()
        
        print("\n🎉 Все тесты пройдены успешно!")
        print("📝 Для запуска бота с реальным токеном:")
        print("   1. Создайте .env файл с настройками")
        print("   2. Укажите реальный TELEGRAM_BOT_TOKEN")
        print("   3. Запустите: python app/main.py")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_bot())
    sys.exit(0 if success else 1) 