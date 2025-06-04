"""
Модуль задач для PaidSubscribeBot.
Содержит автоматические задачи для управления подписками.
"""

from .subscription_tasks import (
    SubscriptionTaskManager,
    get_task_manager,
    start_background_tasks,
    stop_background_tasks
)

__all__ = [
    "SubscriptionTaskManager",
    "get_task_manager", 
    "start_background_tasks",
    "stop_background_tasks"
] 