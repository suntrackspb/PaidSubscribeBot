"""
Middleware для PaidSubscribeBot.
"""

from app.bot.middlewares.auth import AuthMiddleware, AdminMiddleware

__all__ = ["AuthMiddleware", "AdminMiddleware"]
