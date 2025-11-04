"""Telegram bot for Dubai rental property notifications."""
import os
import logging
from datetime import time as dt_time
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

from database import Database, Property
from scraper import PropertyScraper

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class DubaiRentalBot:
    """Telegram bot for property notifications."""

    def __init__(self):
        """Initialize the bot."""
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.notification_time = os.getenv('NOTIFICATION_TIME', '09:00')
        self.max_listings = int(os.getenv('MAX_LISTINGS_PER_NOTIFICATION', '50'))

        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set in environment variables")

        self.db = Database()
        self.scraper = PropertyScraper()
        self.application = Application.builder().token(self.token).build()
        self.scheduler = AsyncIOScheduler()

    def _format_property_message(self, prop: Property) -> str:
        """Format property data as a message."""
        message = "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        message += f"🏠 <b>{prop.title}</b>\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        # Цена
        message += f"💰 <b>Цена:</b> {prop.price}\n"

        # Район/Локация
        if prop.location and prop.location != 'N/A':
            message += f"📍 <b>Район:</b> {prop.location}\n"

        # Спальни
        if prop.bedrooms and prop.bedrooms != 'N/A':
            message += f"🛏 <b>Спален:</b> {prop.bedrooms}\n"

        # Площадь
        if prop.area and prop.area != 'N/A':
            message += f"📐 <b>Площадь:</b> {prop.area}\n"

        # Источник
        message += f"\n🌐 <b>Источник:</b> {prop.source}\n"

        # Ссылка
        message += f"🔗 <a href='{prop.url}'>Открыть объявление</a>\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        return message

    async def send_property_notification(self, context: ContextTypes.DEFAULT_TYPE, properties: List[Property]):
        """Send property notifications to user."""
        if not properties:
            logger.info("No new properties to notify")
            return

        chat_id = self.chat_id or context.job.chat_id

        # Send header message
        header = f"🔔 <b>Найдено новых объявлений: {len(properties)}</b>\n\n"
        header += f"Обнаружено {len(properties)} новых предложений по аренде в Дубае! 🏠✨"

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=header,
                parse_mode=ParseMode.HTML
            )

            # Send each property
            for prop in properties[:self.max_listings]:
                message = self._format_property_message(prop)

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=False
                )

                # Mark as notified
                self.db.mark_as_notified(prop.id)

            if len(properties) > self.max_listings:
                overflow_msg = f"\n⚠️ Ещё {len(properties) - self.max_listings} объявлений доступно. "
                overflow_msg += "Используйте /stats для просмотра статистики."
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=overflow_msg,
                    parse_mode=ParseMode.HTML
                )

        except Exception as e:
            logger.error(f"Error sending notifications: {e}")

    async def scrape_and_notify(self, context: ContextTypes.DEFAULT_TYPE):
        """Scrape properties and send notifications."""
        logger.info("Starting scheduled scraping...")

        try:
            # Scrape all sites
            properties = self.scraper.scrape_all_sites()

            # Add to database
            new_count = 0
            for prop_data in properties:
                is_new = self.db.add_property(prop_data)
                if is_new:
                    new_count += 1

            logger.info(f"Found {new_count} new properties out of {len(properties)} total")

            # Mark old listings as inactive
            self.db.mark_old_listings_inactive(days=7)

            # Get new properties to notify
            new_properties = self.db.get_new_properties(limit=self.max_listings)

            # Send notifications
            if new_properties:
                await self.send_property_notification(context, new_properties)
            else:
                logger.info("No new properties to notify")

        except Exception as e:
            logger.error(f"Error in scrape_and_notify: {e}")
            if self.chat_id:
                await context.bot.send_message(
                    chat_id=self.chat_id,
                    text=f"❌ Error during scraping: {str(e)}"
                )

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_message = """
👋 <b>Добро пожаловать в Dubai Rental Bot!</b>

Я помогу вам найти новые предложения по аренде недвижимости в Дубае, отслеживая несколько сайтов с объявлениями.

<b>Доступные команды:</b>
/start - Показать это приветственное сообщение
/scan - Запустить поиск вручную
/stats - Показать статистику базы данных
/sites - Управление отслеживаемыми сайтами
/settings - Настройки бота
/help - Подробная справка

Бот автоматически сканирует сайты каждый день и присылает вам уведомления о новых объявлениях! 🏠
        """

        await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)

    async def scan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /scan command - manually trigger scraping."""
        await update.message.reply_text("🔍 Запускаю поиск... Это может занять минуту-две.")

        try:
            # Store chat_id for notifications
            context.job_queue.run_once(
                self.scrape_and_notify,
                when=0,
                chat_id=update.effective_chat.id
            )

        except Exception as e:
            logger.error(f"Error in scan command: {e}")
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command - show database statistics."""
        stats = self.db.get_statistics()

        message = "📊 <b>Статистика базы данных</b>\n\n"
        message += f"📝 Всего объявлений: {stats['total']}\n"
        message += f"✅ Активных: {stats['active']}\n"
        message += f"📬 Отправлено уведомлений: {stats['notified']}\n"
        message += f"🆕 Ожидают отправки: {stats['pending']}\n"

        await update.message.reply_text(message, parse_mode=ParseMode.HTML)

    async def sites_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sites command - show and manage sites."""
        enabled_sites = self.scraper.get_enabled_sites()

        message = "🌐 <b>Отслеживаемые сайты недвижимости</b>\n\n"
        message += "Активные сайты:\n"

        for site in enabled_sites:
            message += f"✅ {site}\n"

        all_sites = [s['name'] for s in self.scraper.config['sites']]
        disabled_sites = [s for s in all_sites if s not in enabled_sites]

        if disabled_sites:
            message += "\nОтключенные сайты:\n"
            for site in disabled_sites:
                message += f"❌ {site}\n"

        message += "\n💡 Используйте /settings для управления сайтами"

        await update.message.reply_text(message, parse_mode=ParseMode.HTML)

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command."""
        message = "⚙️ <b>Настройки бота</b>\n\n"
        message += f"🕒 Время ежедневного сканирования: {self.notification_time}\n"
        message += f"📊 Макс. объявлений за раз: {self.max_listings}\n"
        message += f"🌐 Активных сайтов: {len(self.scraper.get_enabled_sites())}\n\n"
        message += "Чтобы изменить настройки, отредактируйте файл .env и перезапустите бота."

        await update.message.reply_text(message, parse_mode=ParseMode.HTML)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """
📖 <b>Подробная справка</b>

<b>Как это работает:</b>
1. Бот автоматически сканирует сайты с недвижимостью каждый день
2. Новые объявления сохраняются в базу данных
3. Вы получаете уведомления о новых предложениях
4. Старые объявления помечаются неактивными через 7 дней

<b>Команды:</b>
/start - Приветственное сообщение и быстрый старт
/scan - Запустить поиск вручную (вместо ожидания автоматического)
/stats - Просмотреть статистику базы данных
/sites - Увидеть какие сайты отслеживаются
/settings - Посмотреть текущие настройки бота
/help - Показать это справочное сообщение

<b>Добавление своих сайтов:</b>
Вы можете добавить свои сайты с недвижимостью, отредактировав файл config/sites_config.json

<b>Поддержка:</b>
Если у вас проблемы или вопросы, смотрите файл README.md
        """

        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

    def setup_scheduler(self):
        """Set up the job scheduler for daily scans."""
        # Parse notification time
        hour, minute = map(int, self.notification_time.split(':'))

        # Schedule daily job
        self.scheduler.add_job(
            lambda: self.application.create_task(
                self.scrape_and_notify(self.application.bot)
            ),
            trigger=CronTrigger(hour=hour, minute=minute),
            id='daily_scan',
            name='Daily property scan',
            replace_existing=True
        )

        logger.info(f"Scheduled daily scan at {self.notification_time}")

    def run(self):
        """Start the bot."""
        # Register command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("scan", self.scan_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("sites", self.sites_command))
        self.application.add_handler(CommandHandler("settings", self.settings_command))
        self.application.add_handler(CommandHandler("help", self.help_command))

        # Setup scheduler
        self.setup_scheduler()
        self.scheduler.start()

        logger.info("Bot is starting...")

        # Start polling
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main entry point."""
    try:
        bot = DubaiRentalBot()
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == '__main__':
    main()
