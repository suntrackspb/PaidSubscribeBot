"""
Обработчики событий Telegram бота для PaidSubscribeBot.
"""

from . import start
from . import payments
from . import subscription
from . import admin
from . import referral
from . import promo

__all__ = [
    "start",
    "payments", 
    "subscription",
    "admin",
    "referral",
    "promo"
]
