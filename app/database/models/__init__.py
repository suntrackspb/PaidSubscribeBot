"""
Модели базы данных для PaidSubscribeBot.
Экспорт всех моделей для упрощения импорта.
"""

from app.database.models.user import User
from app.database.models.subscription import Subscription, SubscriptionStatus, SubscriptionDuration
from app.database.models.payment import Payment, PaymentStatus, PaymentMethod
from app.database.models.channel import Channel
from app.database.models.referral import Referral, ReferralSettings
from app.database.models.promo import PromoCode, PromoCodeUsage, PromoCodeSettings, PromoCodeType

__all__ = [
    "User",
    "Subscription",
    "SubscriptionStatus",
    "SubscriptionDuration",
    "Payment",
    "PaymentStatus",
    "PaymentMethod",
    "Channel",
    "Referral",
    "ReferralSettings",
    "PromoCode",
    "PromoCodeUsage", 
    "PromoCodeSettings",
    "PromoCodeType",
]
