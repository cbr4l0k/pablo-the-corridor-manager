"""Corridor Cleaning Bot - Main Bot Class (Refactored)."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from telegram.constants import ParseMode

from src.config import settings
from src.database import get_db
from src.models import Person
from src.menus import create_main_menu
from src.reminders import setup_reminders
from src.week_manager import setup_week_rollover

# Import handlers
from src.handlers import (
    handle_complete_flow,
    handle_amend_flow,
    handle_ask_flow,
    cmd_status,
    show_status_callback,
    cmd_tasks,
    show_tasks_callback,
    cmd_my_stats,
    show_stats_callback,
    cmd_show_map,
    show_map_callback,
    cmd_optout,
    handle_optout_flow,
    cmd_who_opted_out,
    show_whooptedout_callback,
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, settings.log_level)
)
logger = logging.getLogger(__name__)


class CorridorBot:
    """Main bot class with private/group chat controls."""
    
    def __init__(self):
        """Initialize the bot."""
        self.app = Application.builder().token(settings.telegram_bot_token).build()
        self.group_chat_id = settings.telegram_chat_id
        self._register_handlers()
        
        # Setup reminders (twice a week)
        setup_reminders(self.app, self.group_chat_id)
        
        # Setup automatic week rollover
        setup_week_rollover(self.app, self.group_chat_id)
    
    def _register_handlers(self):
        """Register all command and callback handlers."""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("menu", self.cmd_menu))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("status", cmd_status))
        self.app.add_handler(CommandHandler("tasks", cmd_tasks))
        self.app.add_handler(CommandHandler("mystats", self._cmd_my_stats_wrapper))
        self.app.add_handler(CommandHandler("map", self._cmd_show_map_wrapper))
        self.app.add_handler(CommandHandler("optout", self._cmd_optout_wrapper))
        self.app.add_handler(CommandHandler("whooptedout", cmd_who_opted_out))
        
        # Callback handler for button clicks
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
    
    def is_private_chat(self, update: Update) -> bool:
        """Check if the message is from a private chat."""
        return update.effective_chat.type == "private"
    
    async def redirect_to_private(self, update: Update, action_name: str):
        """Redirect user to private chat for private actions."""
        bot_username = (await update.get_bot()).username
        text = (
            f"🔒 *{action_name} is only available in private chat!*\n\n"
            f"Click the button below to open private chat with me:"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "💬 Open Private Chat",
                url=f"https://t.me/{bot_username}"
            )
        ]])
        
        if update.callback_query:
            await update.callback_query.answer("This action requires private chat!")
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def notify_group(self, message: str):
        """Send a notification to the group chat."""
        if self.group_chat_id:
            try:
                await self.app.bot.send_message(
                    chat_id=self.group_chat_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to send group notification: {e}")
    
    # ========== Wrapper functions for handlers that need bot methods ==========
    
    async def _cmd_my_stats_wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Wrapper for cmd_my_stats to pass bot methods."""
        await cmd_my_stats(update, context, self.is_private_chat, self.redirect_to_private)
    
    async def _cmd_show_map_wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Wrapper for cmd_show_map to pass bot methods."""
        await cmd_show_map(update, context, self.is_private_chat, self.redirect_to_private)
    
    async def _cmd_optout_wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Wrapper for cmd_optout to pass bot methods."""
        await cmd_optout(update, context, self.is_private_chat, self.redirect_to_private, self.notify_group)
    
    # ========== Callback Handler ==========
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all button clicks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        parts = data.split(":")
        action = parts[0]
        
        # Define which actions require private chat
        private_actions = ["complete", "amend", "ask", "optout", "mystats", "map"]
        
        # Check if action requires private chat
        if action in private_actions and not self.is_private_chat(update):
            await self.redirect_to_private(update, action.title())
            return
        
        # Route to appropriate handler
        if action == "menu":
            await self.show_main_menu(query)
        elif action == "status":
            await show_status_callback(query)
        elif action == "tasks":
            await show_tasks_callback(query)
        elif action == "mystats":
            await show_stats_callback(query)
        elif action == "map":
            await show_map_callback(query)
        elif action == "help":
            await self.show_help_callback(query)
        elif action == "whooptedout":
            await show_whooptedout_callback(query)
        elif action == "complete":
            await handle_complete_flow(query, parts, self.notify_group)
        elif action == "amend":
            await handle_amend_flow(query, parts, self.notify_group)
        elif action == "ask":
            await handle_ask_flow(query, parts)
        elif action == "optout":
            await handle_optout_flow(query)
    
    async def show_main_menu(self, query):
        """Show the main menu."""
        is_private = query.message.chat.type == "private"
        
        if is_private:
            text = (
                "🤖 *Pablito's Corridor Manager*\n\n"
                "🔒 Private Menu - Choose an action:"
            )
        else:
            text = (
                "🤖 *Pablito's Corridor Manager*\n\n"
                "👥 Group Menu - Public actions only:"
            )
        
        await query.edit_message_text(
            text=text,
            reply_markup=create_main_menu(is_private),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def show_help_callback(self, query):
        """Show help via callback."""
        is_private = query.message.chat.type == "private"
        
        if is_private:
            text = (
                "🤖 *Pablito's Corridor Manager*\n\n"
                "🔒 *Private Chat Commands:*\n"
                "/menu - Show full menu\n"
                "/status - Weekly status\n"
                "/tasks - List all tasks\n"
                "/mystats - Your stats\n"
                "/map - Corridor map\n"
                "/optout <task> <reason> - Opt out\n"
                "/whooptedout - See opt-outs\n\n"
                "💡 Use buttons for easy task management!"
            )
        else:
            text = (
                "🤖 *Pablito's Corridor Manager*\n\n"
                "👥 *Group Chat Commands:*\n"
                "/status - Weekly status\n"
                "/tasks - List all tasks\n"
                "/whooptedout - See opt-outs\n\n"
                "🔒 *Private Actions:*\n"
                "To complete tasks, amend, or see your stats,\n"
                "message me privately\n\n"
                "💡 Use buttons for quick access!"
            )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("« Back to Menu", callback_data="menu")
        ]])
        
        await query.edit_message_text(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ========== Command Handlers ==========
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Register user and show menu."""
        user = update.effective_user
        is_private = self.is_private_chat(update)
        
        with get_db() as db:
            person = db.query(Person).filter_by(telegram_id=user.id).first()
            
            if not person:
                person = Person(
                    telegram_id=user.id,
                    name=user.first_name,
                    username=user.username
                )
                db.add(person)
                db.commit()
                
                message = f"Bienvenido Mijo 😉! You're registered, {user.first_name}!\n\n"
            else:
                message = f"👋 Quiubo papi, {person.name}!\n\n"
        
        if is_private:
            message += "🔒 Private menu below (all features):"
        else:
            message += "👥 Group menu below (public features only):"
        
        await update.message.reply_text(
            message,
            reply_markup=create_main_menu(is_private)
        )
    
    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show the main menu."""
        is_private = self.is_private_chat(update)
        
        if is_private:
            text = "🤖 *Pablito's Corridor Manager*\n\n🔒 Choose an action:"
        else:
            text = "🤖 *Pablito's Corridor Manager*\n\n👥 Public actions:"
        
        await update.message.reply_text(
            text,
            reply_markup=create_main_menu(is_private),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help."""
        is_private = self.is_private_chat(update)
        
        if is_private:
            text = (
                "🤖 *Pablito's Corridor Manager*\n\n"
                "*Interactive Menu:*\n"
                "/menu - Show button menu\n"
                "/start - Register & show menu\n\n"
                "*Commands:*\n"
                "/status - Full weekly status\n"
                "/tasks - List all tasks\n"
                "/mystats - Your detailed stats\n"
                "/optout <task> <reason> - Opt out\n"
                "/whooptedout - See opt-outs\n"
                "/map - Show corridor map\n\n"
                "💡 Use buttons for easy navigation!"
            )
        else:
            text = (
                "🤖 *Pablito's Corridor Manager*\n\n"
                "*Group Commands:*\n"
                "/status - Weekly status\n"
                "/tasks - List all tasks\n"
                "/whooptedout - See opt-outs\n\n"
                "🔒 *For private actions:*\n"
                "Message me privately to:\n"
                "• Complete tasks\n"
                "• Amend tasks\n"
                "• See your stats\n"
                "• View map\n"
                "• Opt out of tasks\n\n"
                "💡 Use buttons for quick access!"
            )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    def run(self):
        """Start the bot."""
        logger.info("Starting Pablito's Corridor Manager Bot...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    bot = CorridorBot()
    bot.run()