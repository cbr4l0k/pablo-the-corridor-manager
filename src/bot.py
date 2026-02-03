"""Corridor Cleaning Bot - With Private/Group Chat Controls."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from datetime import datetime
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
from src.models import Person, TaskType, TaskInstance, Week, TaskOptOut, CompletionLog

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, settings.log_level)
)
logger = logging.getLogger(__name__)

# Category configuration
category_ammounts = {
    "toilet": 2,
    "shower": 2,
    "kitchen": 3,
    "fridge": 2,
    "hallway": 1,
    "laundry": 1,
    "trash": 2,
    "other": 1
}
            
category_emojis = {
    "toilet": "🚽",
    "shower": "🚿",
    "kitchen": "🍳",
    "fridge": "❄️",
    "hallway": "🚪",
    "laundry": "🧺",
    "trash": "🗑️",
    "other": "📦"
}


class CorridorBot:
    """Main bot class with private/group chat controls."""
    
    def __init__(self):
        """Initialize the bot."""
        self.app = Application.builder().token(settings.telegram_bot_token).build()
        # Get group chat ID from settings (you can configure this)
        self.group_chat_id = settings.telegram_chat_id
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all command and callback handlers."""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("menu", self.cmd_menu))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("tasks", self.cmd_tasks))
        self.app.add_handler(CommandHandler("mystats", self.cmd_my_stats))
        self.app.add_handler(CommandHandler("map", self.cmd_show_map))
        self.app.add_handler(CommandHandler("optout", self.cmd_optout))  # ADDED!
        self.app.add_handler(CommandHandler("whooptedout", self.cmd_who_opted_out))
        
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
        
        # If it's a callback query, edit the message
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
    
    def create_main_menu(self, is_private: bool = True):
        """Create the main menu keyboard based on chat type."""
        if is_private:
            # Full menu for private chat
            keyboard = [
                [
                    InlineKeyboardButton("📋 View Status", callback_data="status"),
                    InlineKeyboardButton("✅ Complete Task", callback_data="complete:categories")
                ],
                [
                    InlineKeyboardButton("❌ Amend Task", callback_data="amend:categories"),
                    InlineKeyboardButton("❓ Ask Instructions", callback_data="ask:categories")
                ],
                [
                    InlineKeyboardButton("🚫 Opt Out", callback_data="optout:categories"),
                    InlineKeyboardButton("📊 My Stats", callback_data="mystats")
                ],
                [
                    InlineKeyboardButton("🗺️ Show Map", callback_data="map"),
                    InlineKeyboardButton("💡 Help", callback_data="help")
                ]
            ]
        else:
            # Limited menu for group chat (only public actions)
            keyboard = [
                [
                    InlineKeyboardButton("📋 View Status", callback_data="status"),
                    InlineKeyboardButton("📝 List Tasks", callback_data="tasks")
                ],
                [
                    InlineKeyboardButton("👥 Who Opted Out", callback_data="whooptedout"),
                    InlineKeyboardButton("💡 Help", callback_data="help")
                ]
            ]
        
        return InlineKeyboardMarkup(keyboard)
    
    def create_category_menu(self, action="complete"):
        """Create category selection menu with progress."""
        with get_db() as db:
            current_week = db.query(Week).filter_by(closed=False).order_by(Week.deadline.desc()).first()
            
            if not current_week:
                return None
            
            # Get task counts by category
            all_instances = (
                db.query(TaskInstance)
                .filter_by(week_id=current_week.id)
                .join(TaskType)
                .all()
            )
            
            by_category = {}
            for task in all_instances:
                category = task.task_type.category or "other"
                if category not in by_category:
                    by_category[category] = {"completed": 0, "total": 0}
                if action == "complete" and task.status == "pending":
                    by_category[category]["total"] += 1
                elif action == "amend" and task.status == "completed":
                    by_category[category]["total"] += 1
                else:
                    # For ask/optout, count all tasks
                    by_category[category]["total"] += 1
                
                if task.status == "completed":
                    by_category[category]["completed"] += 1
            
            # Create buttons (2 per row)
            keyboard = []
            row = []
            for category in sorted(by_category.keys()):
                if by_category[category]["total"] == 0:
                    continue  # Skip categories with no tasks
                
                emoji = category_emojis.get(category, "📦")
                stats = by_category[category]
                button_text = f"{emoji} {category.title()} ({stats['completed']}/{category_ammounts.get(category, 1)})"
                
                row.append(InlineKeyboardButton(
                    button_text,
                    callback_data=f"{action}:category:{category}"
                ))
                
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            
            if row:  # Add remaining button
                keyboard.append(row)
            
            # Add back button
            keyboard.append([InlineKeyboardButton("« Back to Menu", callback_data="menu")])
            
            return InlineKeyboardMarkup(keyboard)
    
    def create_task_menu(self, category, action="complete"):
        """Create task selection menu for a category."""
        with get_db() as db:
            current_week = db.query(Week).filter_by(closed=False).order_by(Week.deadline.desc()).first()
            
            if not current_week:
                return None
            
            # Get tasks for this category
            query = (
                db.query(TaskInstance)
                .join(TaskType)
                .filter(
                    TaskInstance.week_id == current_week.id,
                    TaskType.category == category
                )
            )
            
            # Filter by status based on action
            if action == "complete":
                query = query.filter(TaskInstance.status == "pending")
            elif action == "amend":
                query = query.filter(TaskInstance.status == "completed")
            # For ask/optout, show all tasks
            
            tasks = query.order_by(TaskType.name).all()
            
            if not tasks:
                return None
            
            # Create buttons (1 per row for readability)
            keyboard = []
            for task in tasks:
                task_type = task.task_type
                duration = f" - {task_type.estimated_duration_minutes}min" if task_type.estimated_duration_minutes else ""
                
                # Add status indicator
                status_emoji = "✅" if task.status == "completed" else "⏳"
                button_text = f"{status_emoji} {task_type.name}{duration}"
                
                keyboard.append([InlineKeyboardButton(
                    button_text,
                    callback_data=f"{action}:task:{task.id}"
                )])
            
            # Add back button
            keyboard.append([InlineKeyboardButton("« Back to Categories", callback_data=f"{action}:categories")])
            
            return InlineKeyboardMarkup(keyboard)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all button clicks."""
        query = update.callback_query
        await query.answer()  # Acknowledge the click
        
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
            await self.show_status_callback(query)
        elif action == "tasks":
            await self.show_tasks_callback(query)
        elif action == "mystats":
            await self.show_stats_callback(query)
        elif action == "map":
            await self.show_map_callback(query)
        elif action == "help":
            await self.show_help_callback(query)
        elif action == "whooptedout":
            await self.show_whooptedout_callback(query)
        elif action == "complete":
            await self.handle_complete_flow(query, parts)
        elif action == "amend":
            await self.handle_amend_flow(query, parts)
        elif action == "ask":
            await self.handle_ask_flow(query, parts)
        elif action == "optout":
            await self.handle_optout_flow(query, parts)
    
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
            reply_markup=self.create_main_menu(is_private),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_complete_flow(self, query, parts):
        """Handle the complete task flow (PRIVATE ONLY)."""
        user = query.from_user
        
        if len(parts) == 2 and parts[1] == "categories":
            # Show category menu
            text = "✅ *Complete a Task*\n\nSelect a category:"
            keyboard = self.create_category_menu("complete")
            
            if not keyboard:
                await query.edit_message_text("❌ No active week found.")
                return
            
            await query.edit_message_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif len(parts) == 3 and parts[1] == "category":
            # Show tasks in category
            category = parts[2]
            emoji = category_emojis.get(category, "📦")
            text = f"✅ *Complete a Task*\n\n{emoji} {category.title()} - Select a task:"
            
            keyboard = self.create_task_menu(category, "complete")
            
            if not keyboard:
                await query.edit_message_text(
                    f"ℹ️ No pending tasks in {category}!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back", callback_data="complete:categories")
                    ]])
                )
                return
            
            await query.edit_message_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif len(parts) == 3 and parts[1] == "task":
            # Complete the selected task
            await self.complete_task_by_id(query, int(parts[2]))
    
    async def complete_task_by_id(self, query, task_instance_id):
        """Complete a task by its instance ID (PRIVATE ONLY)."""
        user = query.from_user
        
        with get_db() as db:
            # Get person
            person = db.query(Person).filter_by(telegram_id=user.id).first()
            if not person:
                await query.edit_message_text("❌ You're not registered! Use /start first.")
                return
            
            # Get task instance
            task_instance = db.query(TaskInstance).get(task_instance_id)
            if not task_instance or task_instance.status != "pending":
                await query.edit_message_text("❌ Task not found or already completed.")
                return
            
            # Check opt-out
            opt_out = (
                db.query(TaskOptOut)
                .filter_by(person_id=person.id, task_type_id=task_instance.task_type_id)
                .first()
            )
            
            if opt_out:
                await query.edit_message_text(
                    f"⚠️ You've opted out of '{task_instance.task_type.name}'.\n"
                    f"Reason: {opt_out.reason}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back to Menu", callback_data="menu")
                    ]])
                )
                return
            
            # Mark as complete
            task_instance.status = "completed"
            task_instance.completed_by = person.id
            task_instance.completed_at = datetime.now()
            
            # Log
            log = CompletionLog(
                task_instance_id=task_instance.id,
                person_id=person.id,
                action="completed",
                message_id=query.message.message_id
            )
            db.add(log)
            db.commit()
            
            # Get stats
            current_week = db.query(Week).get(task_instance.week_id)
            completed = db.query(TaskInstance).filter_by(
                week_id=current_week.id, status="completed"
            ).count()
            total = sum([category_ammounts.get(cat, 1) for cat in category_ammounts.keys()])
            remaining = total - completed
            
            personal_count = db.query(TaskInstance).filter_by(
                week_id=current_week.id, completed_by=person.id
            ).count()
            
            # Send confirmation in private chat
            message = (
                f"Eso es lo que nececitamos mijo!\n"
                f"✅ *Great job, {person.name}!*\n\n"
                f"Task completed: *{task_instance.task_type.name}*\n"
                f"Your tasks this week: *{personal_count}*\n"
                f"📊 Remaining: *{remaining}*"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Complete Another", callback_data="complete:categories")],
                [InlineKeyboardButton("« Back to Menu", callback_data="menu")]
            ])
            
            await query.edit_message_text(
                text=message,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # NOTIFY GROUP
            if remaining <= 0:
                group_message = (
                    f"🎉🎉🎉 ¡Mis amores! {person.name} Week Done! *{task_instance.task_type.name}*!\n"
                    f"Time to chill 😎🍹"
                )
            else:
                group_message = (
                    f"✅ {person.name} completed: *{task_instance.task_type.name}*\n"
                    f"📊 {remaining} remaining, hagamole pues!"
                )
            
            await self.notify_group(group_message)
    
    async def handle_amend_flow(self, query, parts):
        """Handle the amend task flow (PRIVATE ONLY)."""
        if len(parts) == 2 and parts[1] == "categories":
            text = "❌ *Amend a Task*\n\nSelect a category:"
            keyboard = self.create_category_menu("amend")
            
            if not keyboard:
                await query.edit_message_text("ℹ️ No completed tasks to amend.")
                return
            
            await query.edit_message_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif len(parts) == 3 and parts[1] == "category":
            category = parts[2]
            emoji = category_emojis.get(category, "📦")
            text = f"❌ *Amend a Task*\n\n{emoji} {category.title()} - Select a task:"
            
            keyboard = self.create_task_menu(category, "amend")
            
            if not keyboard:
                await query.edit_message_text(
                    f"ℹ️ No completed tasks in {category} to amend!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back", callback_data="amend:categories")
                    ]])
                )
                return
            
            await query.edit_message_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif len(parts) == 3 and parts[1] == "task":
            await self.amend_task_by_id(query, int(parts[2]))
    
    async def amend_task_by_id(self, query, task_instance_id):
        """Amend a task by its instance ID (PRIVATE ONLY)."""
        user = query.from_user
        
        with get_db() as db:
            person = db.query(Person).filter_by(telegram_id=user.id).first()
            if not person:
                await query.edit_message_text("❌ You're not registered!")
                return
            
            task_instance = db.query(TaskInstance).get(task_instance_id)
            if not task_instance or task_instance.status != "completed":
                await query.edit_message_text("❌ Task not found or not completed.")
                return
            
            # Get original completer
            original_completer = db.query(Person).get(task_instance.completed_by)
            
            # Undo completion
            task_instance.status = "pending"
            task_instance.completed_by = None
            task_instance.completed_at = None
            
            # Log amendment
            log = CompletionLog(
                task_instance_id=task_instance.id,
                person_id=person.id,
                action="amended",
                message_id=query.message.message_id
            )
            db.add(log)
            db.commit()
            
            # Send confirmation in private chat
            message = (
                f"✅ Task amended!\n\n"
                f"*{task_instance.task_type.name}* is now pending.\n"
                f"Was completed by: {original_completer.name}\n"
                f"Amended by: {person.name}"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Amend Another", callback_data="amend:categories")],
                [InlineKeyboardButton("« Back to Menu", callback_data="menu")]
            ])
            
            await query.edit_message_text(
                text=message,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # NOTIFY GROUP
            group_message = (
                f"⚠️ {person.name} amended *{task_instance.task_type.name}*\n"
                f"(was completed by {original_completer.name})"
            )
            await self.notify_group(group_message)
    
    async def handle_ask_flow(self, query, parts):
        """Handle the ask instructions flow (PRIVATE ONLY)."""
        if len(parts) == 2 and parts[1] == "categories":
            text = "❓ *Ask Instructions*\n\nSelect a category:"
            keyboard = self.create_category_menu("ask")
            
            await query.edit_message_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif len(parts) == 3 and parts[1] == "category":
            category = parts[2]
            emoji = category_emojis.get(category, "📦")
            text = f"❓ *Ask Instructions*\n\n{emoji} {category.title()} - Select a task:"
            
            keyboard = self.create_task_menu(category, "ask")
            
            await query.edit_message_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif len(parts) == 3 and parts[1] == "task":
            await self.show_task_instructions(query, int(parts[2]))
    
    async def show_task_instructions(self, query, task_instance_id):
        """Show instructions for a task (PRIVATE ONLY)."""
        with get_db() as db:
            task_instance = db.query(TaskInstance).get(task_instance_id)
            if not task_instance:
                await query.edit_message_text("❌ Task not found.")
                return
            
            task_type = task_instance.task_type
            
            message = f"📋 *{task_type.name}*\n\n"
            
            if task_type.description:
                message += f"{task_type.description}\n\n"
            
            if task_type.instructions:
                message += f"*How to do it:*\n{task_type.instructions}\n\n"
            
            if task_type.location:
                message += f"📍 Location: {task_type.location}\n"
            
            if task_type.estimated_duration_minutes:
                message += f"⏱ Time: {task_type.estimated_duration_minutes} min\n"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("❓ Ask Another", callback_data="ask:categories")],
                [InlineKeyboardButton("« Back to Menu", callback_data="menu")]
            ])
            
            await query.edit_message_text(
                text=message,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def handle_optout_flow(self, query, parts):
        """Handle opt-out flow (PRIVATE ONLY - shows message about using command)."""
        # Opt-out requires a reason, so we direct to command
        text = (
            "🚫 *Opt Out of a Task*\n\n"
            "To opt out, use this command:\n"
            "`/optout <task> <reason>`\n\n"
            "*Example:*\n"
            "`/optout Fridge 1 I have my own fridge`\n\n"
            "Or use `/whooptedout` to see current opt-outs."
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("« Back to Menu", callback_data="menu")
        ]])
        
        await query.edit_message_text(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def show_status_callback(self, query):
        """Show status via callback (AVAILABLE IN BOTH)."""
        # Reuse existing status logic
        with get_db() as db:
            current_week = db.query(Week).filter_by(closed=False).order_by(Week.deadline.desc()).first()
            
            if not current_week:
                await query.edit_message_text("❌ No active week found.")
                return
            
            # Get progress summary
            all_instances = db.query(TaskInstance).filter_by(week_id=current_week.id).all()
            completed_count = len([t for t in all_instances if t.status == "completed"])
            total = sum([category_ammounts.get(cat, 1) for cat in category_ammounts.keys()])
            
            progress = int((completed_count / total) * 10) if total > 0 else 0
            progress_bar = "█" * progress + "░" * (10 - progress)
            
            message = (
                f"📅 *Week {current_week.week_number}/{current_week.year}*\n"
                f"⏰ Deadline: {current_week.deadline.strftime('%a, %b %d at %H:%M')}\n\n"
                f"📊 Progress: {progress_bar} {completed_count}/{total}\n\n"
                f"💡 Use `/status` for detailed view"
            )
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back to Menu", callback_data="menu")
            ]])
            
            await query.edit_message_text(
                text=message,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def show_tasks_callback(self, query):
        """Show tasks list via callback (AVAILABLE IN BOTH)."""
        with get_db() as db:
            tasks = db.query(TaskType).order_by(TaskType.category, TaskType.name).all()
            
            by_category = {}
            for task in tasks:
                category = task.category or "other"
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(task)
            
            message = "📋 *All Available Tasks*\n\n"
            
            for category, tasks in sorted(by_category.items()):
                emoji = category_emojis.get(category, "📦")
                target = category_ammounts.get(category, 1)
                message += f"{emoji} *{category.title()}* [{target}/week]\n"
                for task in tasks[:3]:  # Show first 3 per category
                    duration = f" ({task.estimated_duration_minutes}min)" if task.estimated_duration_minutes else ""
                    message += f"  • {task.name}{duration}\n"
                if len(tasks) > 3:
                    message += f"  ... and {len(tasks) - 3} more\n"
                message += "\n"
            
            message += "💡 Use `/tasks` for complete list"
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back to Menu", callback_data="menu")
            ]])
            
            await query.edit_message_text(
                text=message,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def show_stats_callback(self, query):
        """Show personal stats via callback (PRIVATE ONLY)."""
        user = query.from_user
        
        with get_db() as db:
            person = db.query(Person).filter_by(telegram_id=user.id).first()
            if not person:
                await query.edit_message_text("❌ You're not registered!")
                return
            
            current_week = db.query(Week).filter_by(closed=False).order_by(Week.deadline.desc()).first()
            
            if current_week:
                week_count = db.query(TaskInstance).filter_by(
                    week_id=current_week.id, completed_by=person.id
                ).count()
            else:
                week_count = 0
            
            all_time = db.query(TaskInstance).filter_by(completed_by=person.id).count()
            
            message = (
                f"📊 *Stats for {person.name}*\n\n"
                f"This week: *{week_count}* tasks\n"
                f"All-time: *{all_time}* tasks\n\n"
                f"💡 Use `/mystats` for detailed view"
            )
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back to Menu", callback_data="menu")
            ]])
            
            await query.edit_message_text(
                text=message,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def show_map_callback(self, query):
        """Show map via callback (PRIVATE ONLY)."""
        media_path = project_root / "media" / "corridor-overview.jpg"
        
        if media_path.exists():
            with open(media_path, "rb") as img_file:
                await query.message.reply_photo(
                    photo=img_file,
                    caption="🗺️ *Corridor Map*",
                    parse_mode=ParseMode.MARKDOWN
                )
            # Edit original message
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back to Menu", callback_data="menu")
            ]])
            await query.edit_message_text(
                "Map sent above! ⬆️",
                reply_markup=keyboard
            )
        else:
            await query.edit_message_text(
                "❌ Map not found.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back to Menu", callback_data="menu")
                ]])
            )
    
    async def show_help_callback(self, query):
        """Show help via callback (AVAILABLE IN BOTH)."""
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
                "message me privately: @[bot_username]\n\n"
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
    
    async def show_whooptedout_callback(self, query):
        """Show opt-outs via callback (AVAILABLE IN BOTH)."""
        with get_db() as db:
            opt_outs = (
                db.query(TaskOptOut)
                .join(Person)
                .join(TaskType)
                .order_by(TaskType.category, TaskType.name)
                .all()
            )
            
            if not opt_outs:
                message = "ℹ️ No one has opted out yet!"
            else:
                by_task = {}
                for opt_out in opt_outs:
                    task_name = opt_out.task_type.name
                    if task_name not in by_task:
                        by_task[task_name] = []
                    person = db.query(Person).get(opt_out.person_id)
                    by_task[task_name].append(f"{person.name}")
                
                message = "📋 *Current Opt-Outs*\n\n"
                for task_name in sorted(list(by_task.keys())[:5]):  # Show first 5
                    message += f"*{task_name}:* "
                    message += ", ".join(by_task[task_name])
                    message += "\n"
                
                if len(by_task) > 5:
                    message += f"\n... and {len(by_task) - 5} more tasks\n"
                
                message += "\n💡 Use `/whooptedout` for full list"
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back to Menu", callback_data="menu")
            ]])
            
            await query.edit_message_text(
                text=message,
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
            reply_markup=self.create_main_menu(is_private)
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
            reply_markup=self.create_main_menu(is_private),
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
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed status (AVAILABLE IN BOTH)."""
        with get_db() as db:
            current_week = db.query(Week).filter_by(closed=False).order_by(Week.deadline.desc()).first()
            
            if not current_week:
                await update.message.reply_text("❌ No active week found.")
                return
            
            all_instances = (
                db.query(TaskInstance)
                .filter_by(week_id=current_week.id)
                .join(TaskType)
                .order_by(TaskType.category, TaskType.name)
                .all()
            )
            
            completed = [t for t in all_instances if t.status == "completed"]
            
            message = (
                f"📅 *Week {current_week.week_number}/{current_week.year}*\n"
                f"⏰ Deadline: {current_week.deadline.strftime('%A, %B %d at %H:%M')}\n\n"
            )
            
            # Progress by category
            message += "📈 *Progress by Category*\n"
            
            by_category = {}
            for task in all_instances:
                category = task.task_type.category or "other"
                if category not in by_category:
                    by_category[category] = {"completed": 0, "total": 0}
                by_category[category]["total"] = category_ammounts.get(category, 1)
                if task.status == "completed":
                    by_category[category]["completed"] += 1
            
            for category in sorted(by_category.keys()):
                emoji = category_emojis.get(category, "📦")
                stats = by_category[category]
                progress = int((stats["completed"] / stats["total"]) * 10) if stats["total"] > 0 else 0
                progress_bar = "█" * progress + "░" * (10 - progress)
                message += f"{emoji} {category.title()}: {progress_bar} {stats['completed']}/{stats['total']}\n"
            
            # Overall progress
            total = sum([category_ammounts.get(cat, 1) for cat in by_category.keys()])
            completed_count = len(completed)
            if total > 0:
                progress = int((completed_count / total) * 10)
                progress_bar = "█" * progress + "░" * (10 - progress)
                message += f"\n📊 *Overall*: {progress_bar} {completed_count}/{total}\n\n"
            
            # Completed tasks (last 5)
            message += f"✅ *Completed ({completed_count})*\n"
            for task in completed[-5:]:
                completer = db.query(Person).get(task.completed_by)
                message += f"  • {task.task_type.name} - {completer.name}\n"
            if completed_count > 5:
                message += f"  ... and {completed_count - 5} more\n"
            
            # Check if done
            done = all(by_category[cat]["completed"] >= by_category[cat]["total"] for cat in by_category)
            if done:
                message += f"\n🎉 All tasks done! Time to relax! 😎🍹\n"
            
            # Non-contributors
            completed_by_ids = [t.completed_by for t in completed if t.completed_by]
            active_people = db.query(Person).filter_by(active=True).all()
            not_contributed = [p for p in active_people if p.id not in completed_by_ids]
            
            if not done and not_contributed:
                message += f"\n¿Y entonces qué? 😡🔪\n"
                message += f"💭 *Haven't contributed:* "
                message += ", ".join([p.name for p in not_contributed])
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all tasks (AVAILABLE IN BOTH)."""
        with get_db() as db:
            tasks = db.query(TaskType).order_by(TaskType.category, TaskType.name).all()
            
            by_category = {}
            for task in tasks:
                category = task.category or "other"
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(task)
            
            message = "📋 *All Available Tasks*\n\n"
            
            for category, tasks in sorted(by_category.items()):
                emoji = category_emojis.get(category, "📦")
                target = category_ammounts.get(category, 1)
                message += f"{emoji} *{category.title()}* [Complete {target}/week]\n"
                for task in tasks:
                    duration = f" ({task.estimated_duration_minutes}min)" if task.estimated_duration_minutes else ""
                    message += f"  • {task.name}{duration}\n"
                message += "\n"
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_my_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed personal stats (PRIVATE ONLY)."""
        if not self.is_private_chat(update):
            await self.redirect_to_private(update, "My Stats")
            return
        
        user = update.effective_user
        
        with get_db() as db:
            person = db.query(Person).filter_by(telegram_id=user.id).first()
            if not person:
                await update.message.reply_text("❌ You're not registered! Use /start first.")
                return
            
            current_week = db.query(Week).filter_by(closed=False).order_by(Week.deadline.desc()).first()
            
            if current_week:
                week_tasks = (
                    db.query(TaskInstance)
                    .filter_by(week_id=current_week.id, completed_by=person.id)
                    .join(TaskType)
                    .all()
                )
                
                message = (
                    f"📊 *Stats for {person.name}*\n\n"
                    f"*This Week (Week {current_week.week_number}):*\n"
                    f"Tasks completed: *{len(week_tasks)}*\n"
                )
                
                if week_tasks:
                    message += "\nTasks:\n"
                    for task in week_tasks:
                        message += f"  • {task.task_type.name}\n"
            else:
                message = f"📊 *Stats for {person.name}*\n\nNo active week."
            
            all_time = db.query(TaskInstance).filter_by(completed_by=person.id).count()
            message += f"\n*All-Time:*\nTotal: *{all_time}* tasks\n"
            
            opt_outs = (
                db.query(TaskOptOut)
                .filter_by(person_id=person.id)
                .join(TaskType)
                .all()
            )
            
            if opt_outs:
                message += f"\n*Opted out of:*\n"
                for opt_out in opt_outs:
                    message += f"  • {opt_out.task_type.name}\n"
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_show_map(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show corridor map (PRIVATE ONLY)."""
        if not self.is_private_chat(update):
            await self.redirect_to_private(update, "Map")
            return
        
        media_path = project_root / "media" / "corridor-overview.jpg"
        
        if media_path.exists():
            with open(media_path, "rb") as img_file:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=img_file,
                    caption="🗺️ *Corridor Map*",
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            await update.message.reply_text("❌ Map not found.")
    
    async def cmd_optout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Allow user to opt out of a task (PRIVATE ONLY)."""
        # Check if private chat
        if not self.is_private_chat(update):
            await self.redirect_to_private(update, "Opt Out")
            return
        
        # Check arguments
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Please specify task and reason!\n\n"
                "Usage: `/optout <task_name> <reason>`\n"
                "Example: `/optout Fridge 1 I have my own fridge`\n"
                "Example: `/optout Kitchen A I don't use communal kitchen`\n\n"
                "Use /tasks to see all available tasks.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # First argument is task, rest is reason
        task_query = context.args[0]
        reason = " ".join(context.args[1:])
        user = update.effective_user
        
        with get_db() as db:
            # Get person
            person = db.query(Person).filter_by(telegram_id=user.id).first()
            if not person:
                await update.message.reply_text(
                    "❌ You're not registered! Use /start to register first."
                )
                return
            
            # Find matching task type
            task_type = (
                db.query(TaskType)
                .filter(TaskType.name.ilike(f"%{task_query}%"))
                .first()
            )
            
            if not task_type:
                await update.message.reply_text(
                    f"❌ Task matching '{task_query}' not found.\n\n"
                    f"Use /tasks to see all available tasks."
                )
                return
            
            # Check if already opted out
            existing_opt_out = (
                db.query(TaskOptOut)
                .filter_by(person_id=person.id, task_type_id=task_type.id)
                .first()
            )
            
            if existing_opt_out:
                await update.message.reply_text(
                    f"⚠️ You're already opted out of '{task_type.name}'.\n"
                    f"Current reason: {existing_opt_out.reason}\n\n"
                    f"Contact an administrator if you want to change the reason or opt back in."
                )
                return
            
            # Create opt-out
            opt_out = TaskOptOut(
                person_id=person.id,
                task_type_id=task_type.id,
                reason=reason
            )
            db.add(opt_out)
            db.commit()
            
            # Send confirmation in private chat
            message = (
                f"✅ Opt-out successful!\n\n"
                f"You've opted out of: *{task_type.name}*\n"
                f"Reason: {reason}\n\n"
                f"You won't be expected to complete this task.\n"
                f"Use `/whooptedout {task_type.name}` to see all opt-outs for this task."
            )
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            
            # NOTIFY GROUP
            group_message = (
                f"ℹ️ {person.name} opted out of *{task_type.name}*\n"
                f"Reason: {reason}"
            )
            await self.notify_group(group_message)
    
    async def cmd_who_opted_out(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show opt-outs (AVAILABLE IN BOTH)."""
        with get_db() as db:
            if not context.args:
                opt_outs = (
                    db.query(TaskOptOut)
                    .join(Person)
                    .join(TaskType)
                    .order_by(TaskType.category, TaskType.name)
                    .all()
                )
                
                if not opt_outs:
                    await update.message.reply_text("ℹ️ No opt-outs yet!")
                    return
                
                by_task = {}
                for opt_out in opt_outs:
                    task_name = opt_out.task_type.name
                    if task_name not in by_task:
                        by_task[task_name] = []
                    person = db.query(Person).get(opt_out.person_id)
                    by_task[task_name].append(f"{person.name} ({opt_out.reason})")
                
                message = "📋 *Current Opt-Outs*\n\n"
                for task_name in sorted(by_task.keys()):
                    message += f"*{task_name}:*\n"
                    for person_info in by_task[task_name]:
                        message += f"  • {person_info}\n"
                    message += "\n"
                
            else:
                task_query = " ".join(context.args)
                task_type = db.query(TaskType).filter(TaskType.name.ilike(f"%{task_query}%")).first()
                
                if not task_type:
                    await update.message.reply_text(f"❌ Task '{task_query}' not found.")
                    return
                
                opt_outs = db.query(TaskOptOut).filter_by(task_type_id=task_type.id).all()
                
                if not opt_outs:
                    message = f"ℹ️ No opt-outs for *{task_type.name}*"
                else:
                    message = f"📋 *Opt-Outs for {task_type.name}*\n\n"
                    for opt_out in opt_outs:
                        person = db.query(Person).get(opt_out.person_id)
                        message += f"• {person.name}\n  Reason: {opt_out.reason}\n\n"
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    def run(self):
        """Start the bot."""
        logger.info("Starting Pablito's Corridor Manager Bot (Private/Group Version)...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    bot = CorridorBot()
    bot.run()
