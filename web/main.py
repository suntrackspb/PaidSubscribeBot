"""
Веб-панель администратора для PaidSubscribeBot.
FastAPI приложение с интерфейсом управления.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
import secrets

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.settings import get_settings
from app.config.database import AsyncSessionLocal
from app.services.user_service import UserService
from app.services.subscription_service import SubscriptionService
from app.services.export_service import ExportService
from app.utils.logger import get_logger

# Настройки
settings = get_settings()
logger = get_logger(__name__)

# Создаем FastAPI приложение
app = FastAPI(
    title="PaidBot Admin Panel",
    description="Панель администратора для управления Telegram ботом",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы и шаблоны
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# Базовая аутентификация
security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Проверка учетных данных администратора"""
    correct_username = secrets.compare_digest(credentials.username, settings.admin_username)
    correct_password = secrets.compare_digest(credentials.password, settings.admin_password)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Инициализация сервисов
user_service = UserService()
subscription_service = SubscriptionService()
export_service = ExportService()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, username: str = Depends(verify_credentials)):
    """Главная страница панели администратора"""
    try:
        # Получаем основную статистику
        stats = await get_dashboard_stats()
        
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "username": username,
                "stats": stats,
                "current_time": datetime.now()
            }
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки дашборда: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки данных")

@app.get("/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    username: str = Depends(verify_credentials)
):
    """Страница управления пользователями"""
    try:
        # Получаем пользователей с пагинацией
        offset = (page - 1) * limit
        
        if search:
            users = await user_service.search_users(search, limit=limit, offset=offset)
            total_users = await user_service.count_search_results(search)
        else:
            users = await user_service.get_users_paginated(limit=limit, offset=offset)
            total_users = await user_service.get_users_count()
        
        total_pages = (total_users + limit - 1) // limit
        
        return templates.TemplateResponse(
            "users.html",
            {
                "request": request,
                "username": username,
                "users": users,
                "current_page": page,
                "total_pages": total_pages,
                "total_users": total_users,
                "search": search or "",
                "limit": limit
            }
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки пользователей: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки пользователей")

@app.get("/subscriptions", response_class=HTMLResponse)
async def subscriptions_page(
    request: Request,
    page: int = 1,
    limit: int = 20,
    status_filter: Optional[str] = None,
    username: str = Depends(verify_credentials)
):
    """Страница управления подписками"""
    try:
        offset = (page - 1) * limit
        
        subscriptions = await subscription_service.get_subscriptions_paginated(
            limit=limit,
            offset=offset,
            status_filter=status_filter
        )
        
        total_subscriptions = await subscription_service.get_subscriptions_count(
            status_filter=status_filter
        )
        
        total_pages = (total_subscriptions + limit - 1) // limit
        
        return templates.TemplateResponse(
            "subscriptions.html",
            {
                "request": request,
                "username": username,
                "subscriptions": subscriptions,
                "current_page": page,
                "total_pages": total_pages,
                "total_subscriptions": total_subscriptions,
                "status_filter": status_filter or "",
                "limit": limit
            }
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки подписок: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки подписок")

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, username: str = Depends(verify_credentials)):
    """Страница аналитики"""
    try:
        # Получаем данные для графиков
        analytics_data = await get_analytics_data()
        
        return templates.TemplateResponse(
            "analytics.html",
            {
                "request": request,
                "username": username,
                "analytics": analytics_data
            }
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки аналитики: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки аналитики")

@app.get("/export", response_class=HTMLResponse)
async def export_page(request: Request, username: str = Depends(verify_credentials)):
    """Страница экспорта данных"""
    return templates.TemplateResponse(
        "export.html",
        {
            "request": request,
            "username": username
        }
    )

# API endpoints для экспорта
@app.post("/api/export/{data_type}")
async def api_export_data(
    data_type: str,
    format_type: str = "csv",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    username: str = Depends(verify_credentials)
):
    """API для экспорта данных"""
    try:
        # Парсим даты если указаны
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        # Выполняем экспорт
        if data_type == "users":
            data = await export_service.export_users(format_type, start_dt, end_dt)
        elif data_type == "subscriptions":
            data = await export_service.export_subscriptions(format_type, start_dt, end_dt)
        elif data_type == "payments":
            data = await export_service.export_payments(format_type, start_dt, end_dt)
        elif data_type == "analytics":
            data = await export_service.export_analytics(format_type, start_dt, end_dt)
        else:
            raise HTTPException(status_code=400, detail="Неизвестный тип данных")
        
        # Определяем MIME тип
        if format_type == "csv":
            media_type = "text/csv"
        elif format_type == "json":
            media_type = "application/json"
        elif format_type == "excel":
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            media_type = "application/octet-stream"
        
        # Формируем имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{data_type}_{timestamp}.{format_type}"
        
        return JSONResponse(
            content={
                "success": True,
                "filename": filename,
                "data": data if isinstance(data, str) else data.decode('utf-8') if format_type != "excel" else None,
                "size": len(data) if isinstance(data, (str, bytes)) else 0
            }
        )
        
    except Exception as e:
        logger.error(f"Ошибка экспорта {data_type}: {e}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )

@app.get("/api/stats")
async def api_get_stats(username: str = Depends(verify_credentials)):
    """API для получения статистики"""
    try:
        stats = await get_dashboard_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@app.post("/api/users/{user_id}/toggle-ban")
async def api_toggle_user_ban(
    user_id: int,
    username: str = Depends(verify_credentials)
):
    """API для блокировки/разблокировки пользователя"""
    try:
        user = await user_service.get_user_by_telegram_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Переключаем статус блокировки
        await user_service.toggle_user_ban(user_id)
        
        return JSONResponse(content={
            "success": True,
            "message": f"Пользователь {'разблокирован' if user.is_banned else 'заблокирован'}"
        })
        
    except Exception as e:
        logger.error(f"Ошибка изменения статуса пользователя {user_id}: {e}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )

async def get_dashboard_stats() -> Dict[str, Any]:
    """Получение статистики для дашборда"""
    try:
        # Статистика пользователей
        total_users = await user_service.get_users_count()
        active_users = await user_service.get_active_users_count(days=7)
        new_users_today = await user_service.get_new_users_count(days=1)
        
        # Статистика подписок
        active_subscriptions = await subscription_service.get_active_subscriptions_count()
        expired_subscriptions = await subscription_service.get_expired_subscriptions_count()
        
        # Статистика платежей
        revenue_today = await subscription_service.get_revenue(days=1)
        revenue_month = await subscription_service.get_revenue(days=30)
        payments_today = await subscription_service.get_payments_count(days=1)
        
        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "new_today": new_users_today
            },
            "subscriptions": {
                "active": active_subscriptions,
                "expired": expired_subscriptions
            },
            "revenue": {
                "today": float(revenue_today),
                "month": float(revenue_month),
                "payments_today": payments_today
            }
        }
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return {}

async def get_analytics_data() -> Dict[str, Any]:
    """Получение данных для аналитики"""
    try:
        # Получаем базовую статистику
        stats = await get_dashboard_stats()
        
        # Формируем данные для графиков
        revenue_chart = {
            "labels": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
            "data": [1200, 1900, 3000, 5000, 2000, 3000, 4500]
        }
        
        payment_methods_chart = {
            "labels": ["YooMoney", "Telegram Stars", "СБП", "Другие"],
            "data": [45, 30, 20, 5]
        }
        
        user_activity_chart = {
            "labels": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
            "data": [65, 78, 90, 81, 56, 55, 40]
        }
        
        return {
            "monthly_revenue": stats.get("monthly_revenue", 0),
            "new_subscriptions": stats.get("new_subscriptions", 0),
            "conversion_rate": stats.get("conversion_rate", 0),
            "avg_payment": stats.get("avg_payment", 0),
            "total_users": stats.get("total_users", 0),
            "active_subscriptions": stats.get("active_subscriptions", 0),
            "successful_payments": stats.get("successful_payments", 0),
            "failed_payments": stats.get("failed_payments", 0),
            "revenue_chart": revenue_chart,
            "payment_methods_chart": payment_methods_chart,
            "user_activity_chart": user_activity_chart
        }
    except Exception as e:
        logger.error(f"Ошибка получения данных аналитики: {e}")
        # Возвращаем пустые данные в случае ошибки
        return {
            "monthly_revenue": 0,
            "new_subscriptions": 0,
            "conversion_rate": 0,
            "avg_payment": 0,
            "total_users": 0,
            "active_subscriptions": 0,
            "successful_payments": 0,
            "failed_payments": 0,
            "revenue_chart": {"labels": [], "data": []},
            "payment_methods_chart": {"labels": [], "data": []},
            "user_activity_chart": {"labels": [], "data": []}
        }

@app.post("/api/subscriptions/{subscription_id}/toggle")
async def api_toggle_subscription(
    subscription_id: int,
    action_data: dict,
    username: str = Depends(verify_credentials)
):
    """API для активации/деактивации подписки"""
    try:
        action = action_data.get('action')
        
        if action == 'activate':
            success = await subscription_service.activate_subscription(subscription_id)
        elif action == 'deactivate':
            success = await subscription_service.deactivate_subscription(subscription_id)
        else:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Неверное действие"}
            )
        
        if success:
            return {"success": True, "message": "Подписка обновлена"}
        else:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Подписка не найдена"}
            )
    except Exception as e:
        logger.error(f"Ошибка управления подпиской: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Внутренняя ошибка сервера"}
        )

@app.post("/api/subscriptions/{subscription_id}/extend")
async def api_extend_subscription(
    subscription_id: int,
    extend_data: dict,
    username: str = Depends(verify_credentials)
):
    """API для продления подписки"""
    try:
        days = extend_data.get('days', 30)
        success = await subscription_service.extend_subscription(subscription_id, days)
        
        if success:
            return {"success": True, "message": f"Подписка продлена на {days} дней"}
        else:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Подписка не найдена"}
            )
    except Exception as e:
        logger.error(f"Ошибка продления подписки: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Внутренняя ошибка сервера"}
        )

@app.delete("/api/subscriptions/{subscription_id}")
async def api_delete_subscription(
    subscription_id: int,
    username: str = Depends(verify_credentials)
):
    """API для удаления подписки"""
    try:
        success = await subscription_service.delete_subscription(subscription_id)
        
        if success:
            return {"success": True, "message": "Подписка удалена"}
        else:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Подписка не найдена"}
            )
    except Exception as e:
        logger.error(f"Ошибка удаления подписки: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Внутренняя ошибка сервера"}
        )

@app.get("/api/subscriptions/stats")
async def api_get_subscription_stats(username: str = Depends(verify_credentials)):
    """API для получения статистики подписок"""
    try:
        stats = await subscription_service.get_subscription_stats()
        return {
            "active": stats.get("active_count", 0),
            "expired": stats.get("expired_count", 0),
            "expiring": stats.get("expiring_count", 0)
        }
    except Exception as e:
        logger.error(f"Ошибка получения статистики подписок: {e}")
        return {"active": 0, "expired": 0, "expiring": 0}

@app.get("/api/analytics/top-channels")
async def api_get_top_channels(username: str = Depends(verify_credentials)):
    """API для получения топ каналов"""
    try:
        # Заглушка для топ каналов
        return [
            {"name": "Основной канал", "subscribers": 150, "revenue": 45000, "growth": 12.5},
            {"name": "VIP канал", "subscribers": 75, "revenue": 67500, "growth": 8.3},
            {"name": "Новости", "subscribers": 200, "revenue": 30000, "growth": -2.1}
        ]
    except Exception as e:
        logger.error(f"Ошибка получения топ каналов: {e}")
        return []

@app.get("/api/analytics/revenue-chart")
async def api_get_revenue_chart(
    period: str = "30days",
    username: str = Depends(verify_credentials)
):
    """API для получения данных графика доходов"""
    try:
        # Заглушка для данных графика
        if period == "7days":
            return {
                "labels": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
                "data": [1200, 1900, 3000, 5000, 2000, 3000, 4500]
            }
        elif period == "30days":
            return {
                "labels": [f"День {i}" for i in range(1, 31)],
                "data": [1000 + i * 100 for i in range(30)]
            }
        else:
            return {
                "labels": ["Янв", "Фев", "Мар"],
                "data": [45000, 52000, 48000]
            }
    except Exception as e:
        logger.error(f"Ошибка получения данных графика: {e}")
        return {"labels": [], "data": []}

@app.get("/api/analytics/stats")
async def api_get_analytics_stats(username: str = Depends(verify_credentials)):
    """API для получения аналитической статистики"""
    try:
        stats = await get_dashboard_stats()
        return {
            "monthly_revenue": stats.get("monthly_revenue", 0),
            "new_subscriptions": stats.get("new_subscriptions", 0),
            "conversion_rate": stats.get("conversion_rate", 0),
            "avg_payment": stats.get("avg_payment", 0)
        }
    except Exception as e:
        logger.error(f"Ошибка получения аналитической статистики: {e}")
        return {
            "monthly_revenue": 0,
            "new_subscriptions": 0,
            "conversion_rate": 0,
            "avg_payment": 0
        }

@app.get("/api/channels")
async def api_get_channels(username: str = Depends(verify_credentials)):
    """API для получения списка каналов"""
    try:
        # Заглушка для каналов
        return [
            {"id": 1, "name": "Основной канал"},
            {"id": 2, "name": "VIP канал"},
            {"id": 3, "name": "Новости"}
        ]
    except Exception as e:
        logger.error(f"Ошибка получения каналов: {e}")
        return []

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "web.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    ) 