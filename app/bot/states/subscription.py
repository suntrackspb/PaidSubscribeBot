"""
Состояния FSM для управления подписками в PaidSubscribeBot.
"""

from aiogram.fsm.state import State, StatesGroup


class SubscriptionStates(StatesGroup):
    """Состояния для процесса оформления подписки"""
    
    # Выбор канала (если их несколько)
    selecting_channel = State()
    
    # Выбор плана подписки (месячный/годовой)
    selecting_plan = State()
    
    # Выбор метода оплаты
    selecting_payment = State()
    
    # Ожидание платежа
    waiting_payment = State()
    
    # Подтверждение деталей подписки
    confirming_subscription = State()


class AdminSubscriptionStates(StatesGroup):
    """Состояния для администрирования подписок"""
    
    # Создание нового канала
    creating_channel = State()
    entering_channel_title = State()
    entering_channel_username = State()
    entering_channel_description = State()
    entering_channel_prices = State()
    
    # Управление существующими каналами
    selecting_channel_to_edit = State()
    editing_channel = State()
    
    # Управление подписками пользователей
    searching_user = State()
    managing_user_subscription = State()
    
    # Массовые операции
    bulk_notification = State()
    entering_notification_text = State()


class PaymentStates(StatesGroup):
    """Состояния для обработки платежей"""
    
    # Ожидание подтверждения платежа
    waiting_confirmation = State()
    
    # Обработка неудачного платежа
    handling_failure = State()
    
    # Возврат платежа
    processing_refund = State() 