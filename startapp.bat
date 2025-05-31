@echo off
echo ========================================
echo       PaidSubscribeBot - Telegram Bot
echo ========================================
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден. Установите Python 3.9+ с python.org
    pause
    exit /b 1
)

REM Проверка наличия виртуального окружения
if not exist "venv\" (
    echo Создание виртуального окружения...
    python -m venv venv
    if errorlevel 1 (
        echo ОШИБКА: Не удалось создать виртуальное окружение
        pause
        exit /b 1
    )
)

REM Активация виртуального окружения
echo Активация виртуального окружения...
call venv\Scripts\activate.bat

REM Проверка наличия .env файла
if not exist ".env" (
    echo ВНИМАНИЕ: Файл .env не найден!
    echo Копирование примера конфигурации...
    copy env.example .env
    echo.
    echo ВАЖНО: Отредактируйте файл .env перед запуском!
    echo Укажите токены и настройки в файле .env
    echo.
    pause
)

REM Установка зависимостей
echo Проверка зависимостей...
pip install -r requirements.txt
if errorlevel 1 (
    echo ОШИБКА: Не удалось установить зависимости
    pause
    exit /b 1
)

REM Создание необходимых каталогов
if not exist "data\" mkdir data
if not exist "logs\" mkdir logs

REM Запуск приложения
echo.
echo Запуск PaidSubscribeBot...
echo Для остановки нажмите Ctrl+C
echo.
python app/main.py

REM Пауза при ошибке
if errorlevel 1 (
    echo.
    echo ОШИБКА: Приложение завершилось с ошибкой
    pause
)

echo.
echo Приложение остановлено.
pause 