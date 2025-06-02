#!/usr/bin/env python3
"""
Упрощенный тест PaidBot без использования .env файла
"""

import os
import sys
from pathlib import Path

# Устанавливаем переменные окружения напрямую
os.environ.update({
    "TELEGRAM_BOT_TOKEN": "1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "TELEGRAM_CHANNEL_ID": "-1001234567890", 
    "TELEGRAM_ADMIN_IDS": "123456789",
    "SECRET_KEY": "test_secret_key_32_characters_long",
    "ENCRYPT_KEY": "test_encrypt_key_32_chars_long!!",
    "DATABASE_URL": "sqlite+aiosqlite:///./data/test_bot.db",
    "DEBUG": "true",
    "LOG_LEVEL": "INFO"
})

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Тестирование импортов"""
    print("🔍 Тестирование импортов...")
    
    try:
        print("📋 Импорт настроек...")
        from app.config.settings import Settings
        
        # Создаем настройки напрямую
        settings = Settings(
            telegram_bot_token="1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            telegram_channel_id="-1001234567890",
            telegram_admin_ids="123456789",
            secret_key="test_secret_key_32_characters_long",
            encrypt_key="test_encrypt_key_32_chars_long!!"
        )
        print(f"✅ Настройки созданы: {settings.telegram_bot_token[:10]}...")
        
        print("📝 Импорт логгера...")
        from app.utils.logger import get_logger
        logger = get_logger("test")
        print("✅ Логгер импортирован")
        
        print("🗄️ Импорт базы данных...")
        from app.config.database import Base
        print("✅ База данных импортирована")
        
        print("🤖 Импорт хендлеров...")
        from app.bot.handlers import start
        print("✅ Хендлеры импортированы")
        
        print("\n🎉 Все импорты успешны!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    print(f"\n{'✅ Тест пройден' if success else '❌ Тест провален'}")
    sys.exit(0 if success else 1) 