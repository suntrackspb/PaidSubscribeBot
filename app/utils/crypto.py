"""
Модуль для шифрования и дешифрования данных в PaidSubscribeBot.
Используется для защиты конфиденциальной информации.
"""

import base64
import hashlib
from typing import Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config.settings import get_settings
from app.utils.logger import get_logger


class CryptoService:
    """
    Сервис для шифрования и дешифрования данных.
    
    Использует симметричное шифрование Fernet для защиты данных.
    """
    
    def __init__(self):
        self.logger = get_logger("utils.crypto")
        self.settings = get_settings()
        self._fernet = self._create_fernet()
    
    def _create_fernet(self) -> Fernet:
        """
        Создание объекта Fernet для шифрования.
        
        Returns:
            Fernet: Объект для шифрования
        """
        # Используем ключ из настроек
        key = self.settings.encrypt_key.encode()
        
        # Создаем ключ для Fernet из настроек
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'salt_',  # В продакшене должна быть случайная соль
            iterations=100000,
        )
        fernet_key = base64.urlsafe_b64encode(kdf.derive(key))
        return Fernet(fernet_key)
    
    def encrypt(self, data: Union[str, bytes]) -> str:
        """
        Шифрование данных.
        
        Args:
            data: Данные для шифрования
            
        Returns:
            str: Зашифрованные данные в base64
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            encrypted_data = self._fernet.encrypt(data)
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            self.logger.error("Ошибка шифрования данных", error=str(e))
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Дешифрование данных.
        
        Args:
            encrypted_data: Зашифрованные данные в base64
            
        Returns:
            str: Расшифрованные данные
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = self._fernet.decrypt(encrypted_bytes)
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            self.logger.error("Ошибка дешифрования данных", error=str(e))
            raise
    
    def hash_data(self, data: str, salt: Optional[str] = None) -> str:
        """
        Хеширование данных с солью.
        
        Args:
            data: Данные для хеширования
            salt: Соль (если не указана, используется из настроек)
            
        Returns:
            str: Хеш в hex формате
        """
        if salt is None:
            salt = self.settings.secret_key
        
        combined = f"{data}{salt}".encode('utf-8')
        return hashlib.sha256(combined).hexdigest()
    
    def verify_hash(self, data: str, hash_value: str, salt: Optional[str] = None) -> bool:
        """
        Проверка хеша данных.
        
        Args:
            data: Исходные данные
            hash_value: Хеш для проверки
            salt: Соль
            
        Returns:
            bool: True если хеш совпадает
        """
        return self.hash_data(data, salt) == hash_value


# Глобальный экземпляр сервиса
_crypto_service = None


def get_crypto_service() -> CryptoService:
    """
    Получение глобального экземпляра сервиса шифрования.
    
    Returns:
        CryptoService: Сервис шифрования
    """
    global _crypto_service
    if _crypto_service is None:
        _crypto_service = CryptoService()
    return _crypto_service


def encrypt_data(data: Union[str, bytes]) -> str:
    """
    Шифрование данных (удобная функция).
    
    Args:
        data: Данные для шифрования
        
    Returns:
        str: Зашифрованные данные
    """
    return get_crypto_service().encrypt(data)


def decrypt_data(encrypted_data: str) -> str:
    """
    Дешифрование данных (удобная функция).
    
    Args:
        encrypted_data: Зашифрованные данные
        
    Returns:
        str: Расшифрованные данные
    """
    return get_crypto_service().decrypt(encrypted_data)


def hash_password(password: str) -> str:
    """
    Хеширование пароля.
    
    Args:
        password: Пароль
        
    Returns:
        str: Хеш пароля
    """
    return get_crypto_service().hash_data(password)


def verify_password(password: str, hash_value: str) -> bool:
    """
    Проверка пароля.
    
    Args:
        password: Пароль
        hash_value: Хеш для проверки
        
    Returns:
        bool: True если пароль верный
    """
    return get_crypto_service().verify_hash(password, hash_value) 