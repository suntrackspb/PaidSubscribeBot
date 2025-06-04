#!/usr/bin/env python3
"""
Тест интеграции системы подписок PaidSubscribeBot
"""

import os
import sys
import asyncio

# Устанавливаем переменные окружения для тестирования
os.environ['TELEGRAM_BOT_TOKEN'] = '1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
os.environ['TELEGRAM_CHANNEL_ID'] = '@test_channel'
os.environ['TELEGRAM_ADMIN_IDS'] = '123456789'
os.environ['SECRET_KEY'] = '01234567890123456789012345678901'
os.environ['ENCRYPT_KEY'] = '01234567890123456789012345678901'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./data/test.db'
os.environ['DEBUG'] = 'true'

async def test_subscription_system():
    """Тестирование интеграции системы подписок"""
    try:
        print("🔄 Тестирование системы подписок...")
        
        # Тестируем импорт новых обработчиков
        from app.bot.handlers.subscription import subscription_router
        print("✅ Обработчики подписок импортированы")
        
        # Тестируем импорт состояний
        from app.bot.states.subscription import SubscriptionStates
        print("✅ Состояния FSM импортированы")
        
        # Тестируем импорт задач
        from app.tasks import SubscriptionTaskManager, get_task_manager
        print("✅ Менеджер задач импортирован")
        
        # Тестируем импорт обновленных клавиатур
        from app.bot.keyboards.inline import (
            get_subscription_menu_keyboard,
            get_subscription_plans_keyboard,
            get_payment_methods_keyboard
        )
        print("✅ Обновленные клавиатуры импортированы")
        
        # Тестируем импорт обновленных текстов
        from app.bot.utils.texts import MESSAGES, format_subscription_info
        print("✅ Обновленные тексты импортированы")
        
        # Проверяем наличие всех сервисов
        from app.services import (
            UserService,
            SubscriptionService, 
            ChannelService,
            NotificationService
        )
        
        user_service = UserService()
        subscription_service = SubscriptionService()
        channel_service = ChannelService()
        notification_service = NotificationService()
        
        print("✅ Все сервисы инициализированы")
        
        # Тестируем создание клавиатур
        subscription_menu = get_subscription_menu_keyboard(has_subscription=False)
        payment_methods = get_payment_methods_keyboard([])
        print("✅ Клавиатуры создаются корректно")
        
        # Тестируем форматирование текстов
        no_sub_text = MESSAGES["no_subscription"]
        print("✅ Тексты сообщений доступны")
        
        print("\n🎉 Все тесты интеграции пройдены успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_routes_registration():
    """Тестирование регистрации маршрутов"""
    try:
        print("\n🔄 Тестирование регистрации маршрутов...")
        
        from app.bot.handlers.subscription import subscription_router
        
        # Проверяем, что роутер содержит обработчики
        handlers_count = len(subscription_router.message.handlers) + len(subscription_router.callback_query.handlers)
        print(f"✅ Зарегистрировано обработчиков: {handlers_count}")
        
        if handlers_count > 0:
            print("✅ Обработчики подписок зарегистрированы")
            return True
        else:
            print("⚠️ Обработчики не найдены")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при проверке маршрутов: {e}")
        return False

def test_states_enum():
    """Тестирование состояний FSM"""
    try:
        print("\n🔄 Тестирование состояний FSM...")
        
        from app.bot.states.subscription import SubscriptionStates, AdminSubscriptionStates, PaymentStates
        
        # Проверяем основные состояния
        states = [
            SubscriptionStates.selecting_plan,
            SubscriptionStates.selecting_payment,
            SubscriptionStates.waiting_payment,
            AdminSubscriptionStates.creating_channel,
            PaymentStates.waiting_confirmation
        ]
        
        for state in states:
            print(f"✅ Состояние {state.state} доступно")
        
        print("✅ Все состояния FSM работают корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании состояний: {e}")
        return False

async def main():
    """Главная функция тестирования"""
    print("🚀 Запуск тестирования интеграции PaidSubscribeBot\n")
    
    # Запускаем все тесты
    tests = [
        test_subscription_system(),
        test_routes_registration(),
        test_states_enum()
    ]
    
    results = []
    for test in tests:
        if asyncio.iscoroutine(test):
            result = await test
        else:
            result = test
        results.append(result)
    
    # Подводим итоги
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Результаты тестирования:")
    print(f"✅ Пройдено: {passed}/{total}")
    print(f"❌ Провалено: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 Все тесты пройдены! Система готова к работе.")
        return True
    else:
        print("\n⚠️ Некоторые тесты провалены. Требуется исправление.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 