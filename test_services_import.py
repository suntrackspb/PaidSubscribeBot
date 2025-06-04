#!/usr/bin/env python3
"""
Тест импорта сервисов PaidSubscribeBot
"""

import os
import sys

# Устанавливаем переменные окружения для тестирования
os.environ['TELEGRAM_BOT_TOKEN'] = '1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
os.environ['TELEGRAM_CHANNEL_ID'] = '@test_channel'
os.environ['TELEGRAM_ADMIN_IDS'] = '123456789'
os.environ['SECRET_KEY'] = '01234567890123456789012345678901'
os.environ['ENCRYPT_KEY'] = '01234567890123456789012345678901'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./data/test.db'
os.environ['DEBUG'] = 'true'

def test_services_import():
    """Тестирование импорта всех сервисов"""
    try:
        print("🔄 Тестирование импорта сервисов...")
        
        # Тестируем импорт UserService
        from app.services.user_service import UserService
        print("✅ UserService импортирован успешно")
        
        # Тестируем импорт SubscriptionService
        from app.services.subscription_service import SubscriptionService
        print("✅ SubscriptionService импортирован успешно")
        
        # Тестируем импорт ChannelService
        from app.services.channel_service import ChannelService
        print("✅ ChannelService импортирован успешно")
        
        # Тестируем импорт NotificationService
        from app.services.notification_service import NotificationService
        print("✅ NotificationService импортирован успешно")
        
        # Тестируем создание экземпляров
        user_service = UserService()
        subscription_service = SubscriptionService()
        channel_service = ChannelService()
        notification_service = NotificationService()
        
        print("✅ Все сервисы успешно созданы")
        
        print("\n🎉 Все тесты пройдены успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_services_import()
    sys.exit(0 if success else 1) 