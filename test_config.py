"""
Временный файл настроек для тестирования PaidBot
"""

import os

# Устанавливаем переменные окружения для тестирования
os.environ.update({
    "TELEGRAM_BOT_TOKEN": "1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",  # Тестовый токен
    "TELEGRAM_CHANNEL_ID": "-1001234567890",
    "TELEGRAM_ADMIN_IDS": "123456789",
    "SECRET_KEY": "test_secret_key_32_characters_long",
    "ENCRYPT_KEY": "test_encrypt_key_32_chars_long!!",  # Ровно 32 символа
    "DATABASE_URL": "sqlite+aiosqlite:///./data/test_bot.db",
    "DEBUG": "true",
    "LOG_LEVEL": "INFO"
})

print("Тестовые настройки загружены!")
print("Для запуска бота используйте: python -c 'import test_config; exec(open(\"app/main.py\").read())'") 