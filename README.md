# PaidSubscribeBot - Telegram бот для оплаты подписки

Telegram бот для автоматизации продажи подписок на закрытые каналы с интеграцией множественных платежных систем.

## 🚀 Возможности

- **Управление подписками**: Автоматическое добавление/удаление пользователей в/из канала
- **Множественные способы оплаты**: СБП, банковские карты (Visa, Mastercard, МИР), Telegram Stars, YooMoney
- **Администрирование**: Команды бота и веб-панель для управления
- **Аналитика**: Статистика платежей и пользователей
- **Безопасность**: Шифрование данных и валидация платежей
- **Масштабируемость**: Поддержка 1000+ пользователей

## 📋 Требования

- Python 3.9+
- Redis (для кеширования)
- SQLite/PostgreSQL
- Docker и Docker Compose (опционально)

## 🛠 Установка

### Быстрый старт с Docker

1. **Клонирование репозитория:**
```bash
git clone <repository>
cd PaidSubscribeBot
```

2. **Настройка переменных окружения:**
```bash
cp env.example .env
# Отредактируйте .env файл, указав токены и настройки
```

3. **Запуск с Docker Compose:**
```bash
docker-compose -f docker/docker-compose.yml up -d
```

### Локальная установка

#### Ubuntu/Debian

1. **Обновление системы:**
```bash
sudo apt update && sudo apt upgrade -y
```

2. **Установка зависимостей:**
```bash
sudo apt install python3 python3-pip python3-venv redis-server -y
```

3. **Клонирование и настройка:**
```bash
git clone <repository>
cd PaidSubscribeBot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. **Настройка переменных окружения:**
```bash
cp env.example .env
# Отредактируйте .env файл
```

5. **Инициализация базы данных:**
```bash
python scripts/migrate.py
```

6. **Запуск:**
```bash
python app/main.py
```

#### CentOS/RHEL

1. **Установка зависимостей:**
```bash
sudo yum update -y
sudo yum install python3 python3-pip redis -y
sudo systemctl start redis
sudo systemctl enable redis
```

2. **Следуйте шагам 3-6 из инструкции для Ubuntu**

#### Windows

1. **Установка Python 3.9+ с python.org**
2. **Установка Redis for Windows**
3. **Клонирование и настройка:**
```cmd
git clone <repository>
cd PaidSubscribeBot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

4. **Настройка .env файла**
5. **Запуск:**
```cmd
startapp.bat
```

## ⚙️ Конфигурация

### Основные настройки (.env)

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL_ID=@your_channel
TELEGRAM_ADMIN_IDS=123456789,987654321

# База данных
DATABASE_URL=sqlite:///data/database.db

# YooMoney
YOOMONEY_TOKEN=your_yoomoney_token
YOOMONEY_CLIENT_ID=your_client_id

# Безопасность
SECRET_KEY=your_secret_key_32_characters_minimum
ENCRYPT_KEY=your_encryption_key_exactly_32_chars
```

### Получение токенов

1. **Telegram Bot Token:**
   - Создайте бота через @BotFather
   - Получите токен и добавьте в `TELEGRAM_BOT_TOKEN`

2. **YooMoney:**
   - Зарегистрируйтесь в YooMoney для бизнеса
   - Получите токен в личном кабинете
   - Настройте HTTP-уведомления

3. **Telegram Channel:**
   - Создайте приватный канал
   - Добавьте бота как администратора
   - Укажите ID канала в `TELEGRAM_CHANNEL_ID`

## 🎯 Использование

### Команды пользователя

- `/start` - Запуск бота, приветствие
- `/help` - Справка по командам
- `/subscription` - Информация о подписке
- `/pay` - Оплата подписки
- `/support` - Связь с поддержкой

### Команды администратора

- `/admin` - Главное меню администратора
- `/stats` - Статистика бота
- `/users` - Управление пользователями
- `/broadcast` - Рассылка сообщений
- `/settings` - Настройки бота

## 🔧 Разработка

### Установка зависимостей для разработки

```bash
pip install -r requirements-dev.txt
```

### Запуск тестов

```bash
pytest
```

### Форматирование кода

```bash
black app/
isort app/
```

### Проверка безопасности

```bash
bandit -r app/
safety check
```

## 📊 Мониторинг

### Логи

Логи сохраняются в каталоге `logs/`:
- `bot.log` - Основные логи бота
- `payments.log` - Логи платежей
- `errors.log` - Ошибки

### Метрики (опционально)

Запуск с мониторингом:
```bash
docker-compose -f docker/docker-compose.yml --profile monitoring up -d
```

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

## 🚀 Развертывание

### На VPS

1. **Подготовка сервера:**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install docker.io docker-compose nginx -y
sudo systemctl start docker
sudo systemctl enable docker
```

2. **Клонирование и запуск:**
```bash
git clone <repository>
cd PaidSubscribeBot
cp env.example .env
# Настройте .env
docker-compose -f docker/docker-compose.yml up -d
```

3. **Настройка Nginx (опционально):**
```bash
sudo cp docker/nginx.conf /etc/nginx/sites-available/PaidSubscribeBot
sudo ln -s /etc/nginx/sites-available/PaidSubscribeBot /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

### Обновление

```bash
git pull
docker-compose -f docker/docker-compose.yml down
docker-compose -f docker/docker-compose.yml up -d --build
```

## 🔒 Безопасность

- Все чувствительные данные шифруются AES-256
- Валидация webhook'ов платежных систем
- Логирование всех критических операций
- Регулярные бэкапы базы данных

## 📝 Лицензия

MIT License. Подробности в файле [LICENSE](LICENSE).

## 🤝 Поддержка

- **Документация**: [docs/](docs/)
- **Issues**: Создайте issue в репозитории
- **Telegram**: @your_support_bot

## 📈 Roadmap

- [ ] Интеграция с Stripe
- [ ] Поддержка криптовалют
- [ ] Мобильное приложение администратора
- [ ] API для интеграции с внешними системами
- [ ] Многоязычность

---

**Разработано с ❤️ для автоматизации продаж в Telegram** 