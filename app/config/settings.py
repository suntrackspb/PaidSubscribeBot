"""
Конфигурация приложения PaidSubscribeBot.
Модуль содержит все настройки проекта с валидацией через Pydantic.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
from pathlib import Path


class Settings(BaseSettings):
    """Основные настройки приложения"""
    
    # Telegram Bot Configuration
    telegram_bot_token: str
    telegram_channel_id: str
    telegram_admin_ids: str
    
    # Database Configuration
    database_url: str = "sqlite:///data/database.db"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    
    # YooMoney Configuration
    yoomoney_token: Optional[str] = None
    yoomoney_client_id: Optional[str] = None
    yoomoney_redirect_uri: Optional[str] = None
    
    # Telegram Stars Configuration
    telegram_stars_enabled: bool = True
    telegram_stars_rate: int = 100
    
    # Webhook Configuration
    webhook_host: Optional[str] = None
    webhook_port: int = 8080
    webhook_path: str = "/webhook"
    webhook_secret: Optional[str] = None
    
    # Security
    secret_key: str
    encrypt_key: str
    
    # Subscription Settings
    subscription_price_monthly: int = 499
    subscription_price_yearly: int = 4990
    subscription_trial_days: int = 3
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "logs/bot.log"
    log_max_size: int = 10485760
    log_backup_count: int = 5
    
    # Development Settings
    debug: bool = False
    environment: str = "production"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_reload: bool = False
    
    # Monitoring
    sentry_dsn: Optional[str] = None
    prometheus_port: int = 9090
    
    # Backup Settings
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    backup_keep_days: int = 30
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_calls: int = 10
    rate_limit_period: int = 60
    
    # Maintenance Mode
    maintenance_mode: bool = False
    maintenance_message: str = "Бот временно недоступен. Попробуйте позже."
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @field_validator("telegram_admin_ids")
    def parse_admin_ids(cls, v):
        """Парсинг ID администраторов из строки в список"""
        if isinstance(v, str):
            return [int(admin_id.strip()) for admin_id in v.split(",") if admin_id.strip()]
        return v
    
    @field_validator("encrypt_key")
    def validate_encrypt_key(cls, v):
        """Проверка длины ключа шифрования"""
        if len(v) != 32:
            raise ValueError("Ключ шифрования должен быть длиной 32 символа")
        return v
    
    @field_validator("secret_key")
    def validate_secret_key(cls, v):
        """Проверка минимальной длины секретного ключа"""
        if len(v) < 32:
            raise ValueError("Секретный ключ должен быть не менее 32 символов")
        return v
    
    @property
    def admin_ids(self) -> List[int]:
        """Получение списка ID администраторов"""
        if isinstance(self.telegram_admin_ids, list):
            return self.telegram_admin_ids
        return [int(admin_id.strip()) for admin_id in self.telegram_admin_ids.split(",") if admin_id.strip()]
    
    @property
    def webhook_url(self) -> Optional[str]:
        """Полный URL webhook'а"""
        if self.webhook_host:
            return f"{self.webhook_host}{self.webhook_path}"
        return None
    
    @property
    def log_dir(self) -> Path:
        """Каталог для логов"""
        log_path = Path(self.log_file).parent
        log_path.mkdir(parents=True, exist_ok=True)
        return log_path
    
    @property
    def data_dir(self) -> Path:
        """Каталог для данных"""
        data_path = Path("data")
        data_path.mkdir(parents=True, exist_ok=True)
        return data_path
    
    def is_admin(self, user_id: int) -> bool:
        """Проверка является ли пользователь администратором"""
        return user_id in self.admin_ids
    
    def get_subscription_price(self, duration: str) -> int:
        """Получение цены подписки по длительности"""
        prices = {
            "monthly": self.subscription_price_monthly,
            "yearly": self.subscription_price_yearly,
        }
        return prices.get(duration, self.subscription_price_monthly)


# Создание глобального экземпляра настроек
_settings = None


def get_settings() -> Settings:
    """Получение настроек приложения"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings 