#!/usr/bin/env python3
"""
Интерактивная настройка Dubai Rental Bot
Этот скрипт поможет настроить бота за несколько простых шагов
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    """Красивый заголовок"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")

def print_step(number, text):
    """Красивый шаг"""
    print(f"\n🔹 Шаг {number}: {text}")
    print("-" * 60)

def print_success(text):
    """Сообщение об успехе"""
    print(f"\n✅ {text}\n")

def print_error(text):
    """Сообщение об ошибке"""
    print(f"\n❌ {text}\n")

def print_info(text):
    """Информационное сообщение"""
    print(f"ℹ️  {text}")

def check_python_version():
    """Проверка версии Python"""
    if sys.version_info < (3, 9):
        print_error("Требуется Python 3.9 или выше!")
        print(f"Ваша версия: {sys.version}")
        print("\nСкачайте Python с https://www.python.org/downloads/")
        sys.exit(1)
    print_success(f"Python {sys.version_info.major}.{sys.version_info.minor} обнаружен")

def install_dependencies():
    """Установка зависимостей"""
    print_step(1, "Установка необходимых библиотек")
    print_info("Это может занять 1-2 минуты...")

    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"
        ])
        print_success("Все библиотеки установлены!")
    except subprocess.CalledProcessError:
        print_error("Ошибка установки библиотек")
        print("Попробуйте вручную: pip install -r requirements.txt")
        sys.exit(1)

def get_bot_token():
    """Получение токена бота"""
    print_step(2, "Получение токена Telegram бота")
    print_info("Если у вас еще нет бота, выполните следующие действия:")
    print("   1. Откройте Telegram")
    print("   2. Найдите @BotFather")
    print("   3. Отправьте команду: /newbot")
    print("   4. Следуйте инструкциям BotFather")
    print("   5. Скопируйте токен, который он вам даст")
    print()

    while True:
        token = input("📝 Вставьте токен бота сюда: ").strip()
        if token and len(token) > 20:
            return token
        print_error("Токен выглядит неправильно. Попробуйте снова.")

def get_chat_id():
    """Получение Chat ID"""
    print_step(3, "Получение вашего Chat ID")
    print_info("Чтобы бот мог отправлять вам сообщения, нужен ваш Chat ID:")
    print("   1. Откройте Telegram")
    print("   2. Найдите @userinfobot")
    print("   3. Отправьте ему любое сообщение")
    print("   4. Он пришлет вам ваш ID (это число)")
    print()

    while True:
        chat_id = input("📝 Вставьте ваш Chat ID сюда: ").strip()
        if chat_id and chat_id.isdigit():
            return chat_id
        print_error("Chat ID должен быть числом. Попробуйте снова.")

def get_notification_time():
    """Получение времени уведомлений"""
    print_step(4, "Настройка времени ежедневных уведомлений")
    print_info("В какое время вы хотите получать уведомления о новых объявлениях?")
    print("   Формат: ЧЧ:ММ (например, 09:00 или 18:30)")
    print()

    while True:
        time = input("📝 Введите время (по умолчанию 09:00): ").strip()
        if not time:
            return "09:00"
        if ":" in time:
            try:
                hours, minutes = time.split(":")
                if 0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59:
                    return time
            except:
                pass
        print_error("Неправильный формат. Используйте ЧЧ:ММ (например, 09:00)")

def create_env_file(bot_token, chat_id, notification_time):
    """Создание .env файла"""
    print_step(5, "Создание файла конфигурации")

    env_content = f"""# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN={bot_token}
TELEGRAM_CHAT_ID={chat_id}

# Notification Settings
NOTIFICATION_TIME={notification_time}
MAX_LISTINGS_PER_NOTIFICATION=50

# Database (SQLite для локальной разработки)
DATABASE_URL=sqlite:///properties.db
"""

    with open('.env', 'w') as f:
        f.write(env_content)

    print_success("Файл .env создан!")

def create_start_script():
    """Создание скрипта запуска"""
    if sys.platform == 'darwin' or sys.platform.startswith('linux'):
        # Mac/Linux
        script_content = """#!/bin/bash
echo "🚀 Запуск Dubai Rental Bot..."
cd src
python3 bot.py
"""
        script_name = "start.sh"

        with open(script_name, 'w') as f:
            f.write(script_content)

        os.chmod(script_name, 0o755)
        print_success(f"Скрипт запуска создан: {script_name}")
        return script_name

    else:
        # Windows
        script_content = """@echo off
echo 🚀 Запуск Dubai Rental Bot...
cd src
python bot.py
pause
"""
        script_name = "start.bat"

        with open(script_name, 'w') as f:
            f.write(script_content)

        print_success(f"Скрипт запуска создан: {script_name}")
        return script_name

def main():
    """Главная функция"""
    print_header("🏠 Настройка Dubai Rental Bot")
    print("Привет! Я помогу вам настроить бота за несколько минут.")
    print("Просто следуйте инструкциям ниже.")

    # Проверка Python
    check_python_version()

    # Установка зависимостей
    install_dependencies()

    # Получение данных от пользователя
    bot_token = get_bot_token()
    chat_id = get_chat_id()
    notification_time = get_notification_time()

    # Создание конфигурации
    create_env_file(bot_token, chat_id, notification_time)

    # Создание скрипта запуска
    script_name = create_start_script()

    # Финальное сообщение
    print_header("🎉 Настройка завершена!")
    print("Ваш бот готов к работе!\n")
    print("📋 Что дальше:\n")
    print("1️⃣  Запустите бота:")
    if sys.platform == 'darwin' or sys.platform.startswith('linux'):
        print(f"   ./start.sh")
        print(f"   или: cd src && python3 bot.py")
    else:
        print(f"   {script_name}")
        print(f"   или: cd src && python bot.py")

    print("\n2️⃣  Откройте Telegram и найдите вашего бота")
    print("\n3️⃣  Отправьте команду: /start")
    print("\n4️⃣  Для тестового сканирования: /scan")
    print("\n5️⃣  Бот будет автоматически сканировать сайты каждый день")
    print(f"   и присылать новые объявления в {notification_time}")

    print("\n" + "=" * 60)
    print("📚 Документация:")
    print("   README.md - Полное руководство")
    print("   QUICKSTART.md - Быстрый старт")
    print("   ADDING_SITES.md - Как добавить свои сайты")
    print("=" * 60 + "\n")

    # Спросить, запустить ли сразу
    response = input("🚀 Хотите запустить бота прямо сейчас? (да/нет): ").strip().lower()
    if response in ['да', 'yes', 'y', 'д']:
        print("\n▶️  Запускаю бота...\n")
        os.chdir('src')
        subprocess.call([sys.executable, "bot.py"])
    else:
        print("\n👋 Хорошо! Запустите бота когда будете готовы.")
        print(f"   Команда: ./start.sh\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Настройка прервана пользователем.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Произошла ошибка: {e}")
        print("Пожалуйста, создайте issue на GitHub с описанием проблемы.")
        sys.exit(1)
