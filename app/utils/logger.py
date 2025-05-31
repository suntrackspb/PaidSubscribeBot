"""
Система логирования для PaidSubscribeBot.
Настройка структурированного логирования с поддержкой различных уровней.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict

import structlog
from colorlog import ColoredFormatter

from app.config.settings import get_settings


def setup_logging() -> structlog.stdlib.BoundLogger:
    """
    Настройка системы логирования.
    
    Returns:
        structlog.stdlib.BoundLogger: Настроенный логгер
    """
    settings = get_settings()
    
    # Создаем директорию для логов
    log_dir = Path(settings.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Настройка стандартного логирования
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Очищаем существующие обработчики
    root_logger.handlers.clear()
    
    # Консольный обработчик с цветным выводом
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = ColoredFormatter(
        "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s | %(message)s%(reset)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    # Файловый обработчик с ротацией
    file_handler = logging.handlers.RotatingFileHandler(
        filename=settings.log_file,
        maxBytes=settings.log_max_size,
        backupCount=settings.log_backup_count,
        encoding='utf-8'
    )
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(getattr(logging, settings.log_level.upper()))
    root_logger.addHandler(file_handler)
    
    # Отдельный файл для ошибок
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "errors.log",
        maxBytes=settings.log_max_size,
        backupCount=settings.log_backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)
    
    # Отдельный файл для платежей
    payments_logger = logging.getLogger("payments")
    payments_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "payments.log",
        maxBytes=settings.log_max_size,
        backupCount=settings.log_backup_count,
        encoding='utf-8'
    )
    payments_handler.setFormatter(file_formatter)
    payments_logger.addHandler(payments_handler)
    payments_logger.setLevel(logging.INFO)
    
    # Настройка structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not settings.debug else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Настройка логирования для библиотек
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    logger = structlog.get_logger("PaidSubscribeBot")
    logger.info("Система логирования инициализирована", log_level=settings.log_level)
    
    return logger


def get_logger(name: str = "PaidSubscribeBot") -> structlog.stdlib.BoundLogger:
    """
    Получение логгера для модуля.
    
    Args:
        name: Имя логгера
        
    Returns:
        structlog.stdlib.BoundLogger: Логгер
    """
    return structlog.get_logger(name)


def log_user_action(user_id: int, action: str, **kwargs: Any) -> None:
    """
    Логирование действий пользователя.
    
    Args:
        user_id: ID пользователя
        action: Описание действия
        **kwargs: Дополнительные параметры
    """
    logger = get_logger("user_actions")
    logger.info(
        "Действие пользователя",
        user_id=user_id,
        action=action,
        **kwargs
    )


def log_payment_event(event_type: str, payment_data: Dict[str, Any]) -> None:
    """
    Логирование событий платежей.
    
    Args:
        event_type: Тип события (created, completed, failed, etc.)
        payment_data: Данные платежа
    """
    logger = get_logger("payments")
    logger.info(
        f"Событие платежа: {event_type}",
        event_type=event_type,
        **payment_data
    )


def log_admin_action(admin_id: int, action: str, target_user_id: int = None, **kwargs: Any) -> None:
    """
    Логирование действий администратора.
    
    Args:
        admin_id: ID администратора
        action: Описание действия
        target_user_id: ID пользователя, над которым выполняется действие
        **kwargs: Дополнительные параметры
    """
    logger = get_logger("admin_actions")
    logger.info(
        "Действие администратора",
        admin_id=admin_id,
        action=action,
        target_user_id=target_user_id,
        **kwargs
    ) 