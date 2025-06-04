import asyncio
import csv
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from io import StringIO, BytesIO
import zipfile

from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import User, Subscription, Payment, Channel, PromoCode, Notification, Referral
from app.config.database import AsyncSessionLocal
from app.utils.logger import get_logger

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

logger = get_logger(__name__)

class ExportService:
    """Сервис для экспорта данных в различных форматах"""
    
    def __init__(self):
        self.logger = logger
    
    async def export_users(
        self,
        format_type: str = "csv",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_inactive: bool = True
    ) -> Union[str, bytes]:
        """
        Экспорт пользователей
        
        Args:
            format_type: Формат экспорта (csv, json, excel)
            start_date: Начальная дата для фильтрации
            end_date: Конечная дата для фильтрации
            include_inactive: Включать неактивных пользователей
            
        Returns:
            Экспортированные данные в указанном формате
        """
        async with AsyncSessionLocal() as session:
            query = select(User).options(
                selectinload(User.subscriptions),
                selectinload(User.payments),
                selectinload(User.referral_codes_created),
                selectinload(User.referral_codes_used)
            )
            
            # Применяем фильтры
            if start_date:
                query = query.where(User.created_at >= start_date)
            if end_date:
                query = query.where(User.created_at <= end_date)
            if not include_inactive:
                query = query.where(User.is_active == True)
            
            result = await session.execute(query)
            users = result.scalars().all()
            
            # Подготавливаем данные для экспорта
            export_data = []
            for user in users:
                active_subscription = next(
                    (sub for sub in user.subscriptions if sub.is_active), None
                )
                
                user_data = {
                    "id": user.id,
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_active": user.is_active,
                    "is_admin": user.is_admin,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_activity": user.last_activity.isoformat() if user.last_activity else None,
                    "total_payments": len(user.payments),
                    "total_spent": sum(p.amount for p in user.payments if p.status == "completed"),
                    "active_subscription": active_subscription.channel.name if active_subscription and active_subscription.channel else None,
                    "subscription_expires": active_subscription.expires_at.isoformat() if active_subscription and active_subscription.expires_at else None,
                    "referrals_created": len(user.referral_codes_created),
                    "referrals_used": len([r for r in user.referral_codes_created if r.used_count > 0]),
                    "referral_earnings": sum(r.earnings for r in user.referral_codes_created)
                }
                export_data.append(user_data)
            
            return await self._format_export_data(export_data, format_type, "users")
    
    async def export_subscriptions(
        self,
        format_type: str = "csv",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        channel_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> Union[str, bytes]:
        """
        Экспорт подписок
        
        Args:
            format_type: Формат экспорта
            start_date: Начальная дата
            end_date: Конечная дата
            channel_id: ID канала для фильтрации
            status: Статус подписки (active, expired, cancelled)
            
        Returns:
            Экспортированные данные
        """
        async with AsyncSessionLocal() as session:
            query = select(Subscription).options(
                selectinload(Subscription.user),
                selectinload(Subscription.channel),
                selectinload(Subscription.payment)
            )
            
            # Применяем фильтры
            if start_date:
                query = query.where(Subscription.created_at >= start_date)
            if end_date:
                query = query.where(Subscription.created_at <= end_date)
            if channel_id:
                query = query.where(Subscription.channel_id == channel_id)
            if status:
                if status == "active":
                    query = query.where(Subscription.is_active == True)
                elif status == "expired":
                    query = query.where(
                        and_(
                            Subscription.expires_at < datetime.utcnow(),
                            Subscription.is_active == False
                        )
                    )
                elif status == "cancelled":
                    query = query.where(Subscription.is_active == False)
            
            query = query.order_by(desc(Subscription.created_at))
            result = await session.execute(query)
            subscriptions = result.scalars().all()
            
            # Подготавливаем данные
            export_data = []
            for sub in subscriptions:
                sub_data = {
                    "id": sub.id,
                    "user_id": sub.user_id,
                    "user_username": sub.user.username if sub.user else None,
                    "user_name": f"{sub.user.first_name or ''} {sub.user.last_name or ''}".strip() if sub.user else None,
                    "channel_id": sub.channel_id,
                    "channel_name": sub.channel.name if sub.channel else None,
                    "payment_id": sub.payment_id,
                    "payment_amount": sub.payment.amount if sub.payment else None,
                    "payment_method": sub.payment.method if sub.payment else None,
                    "is_active": sub.is_active,
                    "duration_days": sub.duration_days,
                    "created_at": sub.created_at.isoformat() if sub.created_at else None,
                    "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
                    "cancelled_at": sub.cancelled_at.isoformat() if sub.cancelled_at else None,
                    "auto_renewal": sub.auto_renewal
                }
                export_data.append(sub_data)
            
            return await self._format_export_data(export_data, format_type, "subscriptions")
    
    async def export_payments(
        self,
        format_type: str = "csv",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        method: Optional[str] = None
    ) -> Union[str, bytes]:
        """
        Экспорт платежей
        
        Args:
            format_type: Формат экспорта
            start_date: Начальная дата
            end_date: Конечная дата
            status: Статус платежа
            method: Метод платежа
            
        Returns:
            Экспортированные данные
        """
        async with AsyncSessionLocal() as session:
            query = select(Payment).options(
                selectinload(Payment.user),
                selectinload(Payment.subscription),
                selectinload(Payment.promo_code)
            )
            
            # Применяем фильтры
            if start_date:
                query = query.where(Payment.created_at >= start_date)
            if end_date:
                query = query.where(Payment.created_at <= end_date)
            if status:
                query = query.where(Payment.status == status)
            if method:
                query = query.where(Payment.method == method)
            
            query = query.order_by(desc(Payment.created_at))
            result = await session.execute(query)
            payments = result.scalars().all()
            
            # Подготавливаем данные
            export_data = []
            for payment in payments:
                payment_data = {
                    "id": payment.id,
                    "user_id": payment.user_id,
                    "user_username": payment.user.username if payment.user else None,
                    "subscription_id": payment.subscription_id,
                    "amount": float(payment.amount),
                    "currency": payment.currency,
                    "method": payment.method,
                    "status": payment.status,
                    "provider_payment_id": payment.provider_payment_id,
                    "promo_code": payment.promo_code.code if payment.promo_code else None,
                    "discount_amount": float(payment.discount_amount) if payment.discount_amount else 0,
                    "created_at": payment.created_at.isoformat() if payment.created_at else None,
                    "updated_at": payment.updated_at.isoformat() if payment.updated_at else None,
                    "completed_at": payment.completed_at.isoformat() if payment.completed_at else None,
                    "error_message": payment.error_message
                }
                export_data.append(payment_data)
            
            return await self._format_export_data(export_data, format_type, "payments")
    
    async def export_analytics(
        self,
        format_type: str = "json",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Union[str, bytes]:
        """
        Экспорт аналитики
        
        Args:
            format_type: Формат экспорта
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            Экспортированные данные аналитики
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        async with AsyncSessionLocal() as session:
            # Общая статистика пользователей
            total_users = await session.execute(select(func.count(User.id)))
            total_users = total_users.scalar()
            
            new_users = await session.execute(
                select(func.count(User.id)).where(
                    User.created_at.between(start_date, end_date)
                )
            )
            new_users = new_users.scalar()
            
            # Статистика подписок
            total_subscriptions = await session.execute(select(func.count(Subscription.id)))
            total_subscriptions = total_subscriptions.scalar()
            
            active_subscriptions = await session.execute(
                select(func.count(Subscription.id)).where(
                    Subscription.is_active == True
                )
            )
            active_subscriptions = active_subscriptions.scalar()
            
            # Статистика платежей
            total_revenue = await session.execute(
                select(func.sum(Payment.amount)).where(
                    and_(
                        Payment.status == "completed",
                        Payment.created_at.between(start_date, end_date)
                    )
                )
            )
            total_revenue = float(total_revenue.scalar() or 0)
            
            successful_payments = await session.execute(
                select(func.count(Payment.id)).where(
                    and_(
                        Payment.status == "completed",
                        Payment.created_at.between(start_date, end_date)
                    )
                )
            )
            successful_payments = successful_payments.scalar()
            
            # Топ каналы по подпискам
            top_channels = await session.execute(
                select(
                    Channel.name,
                    func.count(Subscription.id).label("subscriptions_count")
                ).join(Subscription).where(
                    Subscription.created_at.between(start_date, end_date)
                ).group_by(Channel.id, Channel.name).order_by(
                    desc(func.count(Subscription.id))
                ).limit(10)
            )
            top_channels = [{"name": row[0], "subscriptions": row[1]} for row in top_channels.all()]
            
            # Статистика по методам оплаты
            payment_methods = await session.execute(
                select(
                    Payment.method,
                    func.count(Payment.id).label("count"),
                    func.sum(Payment.amount).label("total")
                ).where(
                    and_(
                        Payment.status == "completed",
                        Payment.created_at.between(start_date, end_date)
                    )
                ).group_by(Payment.method)
            )
            payment_methods = [
                {
                    "method": row[0],
                    "count": row[1],
                    "total": float(row[2] or 0)
                } for row in payment_methods.all()
            ]
            
            # Собираем аналитику
            analytics_data = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "users": {
                    "total": total_users,
                    "new_in_period": new_users
                },
                "subscriptions": {
                    "total": total_subscriptions,
                    "active": active_subscriptions
                },
                "payments": {
                    "total_revenue": total_revenue,
                    "successful_payments": successful_payments,
                    "by_method": payment_methods
                },
                "top_channels": top_channels,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return await self._format_export_data(analytics_data, format_type, "analytics")
    
    async def create_full_backup(self) -> bytes:
        """
        Создание полного бэкапа всех данных в ZIP архиве
        
        Returns:
            ZIP архив с данными
        """
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Экспортируем пользователей
            users_data = await self.export_users("json")
            zip_file.writestr("users.json", users_data)
            
            # Экспортируем подписки
            subscriptions_data = await self.export_subscriptions("json")
            zip_file.writestr("subscriptions.json", subscriptions_data)
            
            # Экспортируем платежи
            payments_data = await self.export_payments("json")
            zip_file.writestr("payments.json", payments_data)
            
            # Экспортируем аналитику
            analytics_data = await self.export_analytics("json")
            zip_file.writestr("analytics.json", analytics_data)
            
            # Добавляем метаданные
            metadata = {
                "backup_created_at": datetime.utcnow().isoformat(),
                "version": "1.0",
                "description": "Полный бэкап данных PaidBot"
            }
            zip_file.writestr("metadata.json", json.dumps(metadata, indent=2, ensure_ascii=False))
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    
    async def _format_export_data(
        self,
        data: Union[List[Dict], Dict],
        format_type: str,
        data_type: str
    ) -> Union[str, bytes]:
        """
        Форматирование данных в указанный формат
        
        Args:
            data: Данные для экспорта
            format_type: Тип формата (csv, json, excel)
            data_type: Тип данных (для названия файла)
            
        Returns:
            Отформатированные данные
        """
        if format_type.lower() == "json":
            return json.dumps(data, indent=2, ensure_ascii=False, default=str)
        
        elif format_type.lower() == "csv":
            if isinstance(data, dict):
                # Для аналитики преобразуем в плоскую структуру
                flat_data = []
                for key, value in data.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            flat_data.append({
                                "category": key,
                                "metric": sub_key,
                                "value": sub_value
                            })
                    else:
                        flat_data.append({
                            "category": "general",
                            "metric": key,
                            "value": value
                        })
                data = flat_data
            
            if not data:
                return ""
            
            output = StringIO()
            fieldnames = list(data[0].keys()) if data else []
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            return output.getvalue()
        
        elif format_type.lower() == "excel" and PANDAS_AVAILABLE:
            if isinstance(data, dict):
                # Для словарей создаем DataFrame из ключей-значений
                df = pd.DataFrame(list(data.items()), columns=['Key', 'Value'])
            else:
                df = pd.DataFrame(data)
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=data_type, index=False)
            
            output.seek(0)
            return output.getvalue()
        
        else:
            raise ValueError(f"Неподдерживаемый формат: {format_type}")
    
    async def schedule_automatic_backup(self) -> Dict[str, Any]:
        """
        Запланировать автоматический бэкап
        
        Returns:
            Информация о созданном бэкапе
        """
        try:
            backup_data = await self.create_full_backup()
            
            # Сохраняем бэкап в data/backups/
            import os
            backup_dir = "data/backups"
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.zip"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            with open(backup_path, 'wb') as f:
                f.write(backup_data)
            
            self.logger.info(f"Автоматический бэкап создан: {backup_path}")
            
            return {
                "success": True,
                "backup_path": backup_path,
                "backup_size": len(backup_data),
                "created_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Ошибка создания автоматического бэкапа: {e}")
            return {
                "success": False,
                "error": str(e),
                "created_at": datetime.utcnow().isoformat()
            }

# Создаем экземпляр сервиса
export_service = ExportService()