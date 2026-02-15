"""Task-related handlers: complete, amend, ask instructions."""

from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src.database import get_db
from src.models import Person, TaskType, TaskInstance, Week, TaskOptOut, CompletionLog
from src.menus import CATEGORY_AMOUNTS, CATEGORY_EMOJIS, create_category_menu, create_task_menu


async def handle_complete_flow(query, parts, notify_group_func):
    """Handle the complete task flow (PRIVATE ONLY)."""
    if len(parts) == 2 and parts[1] == "categories":
        # Show category menu
        text = "✅ *Complete a Task*\n\nSelect a category:"
        keyboard = create_category_menu("complete")
        
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
        emoji = CATEGORY_EMOJIS.get(category, "📦")
        text = f"✅ *Complete a Task*\n\n{emoji} {category.title()} - Select a task:"
        
        keyboard = create_task_menu(category, "complete")
        
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
        await complete_task_by_id(query, int(parts[2]), notify_group_func)


async def complete_task_by_id(query, task_instance_id, notify_group_func):
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
        total = sum([CATEGORY_AMOUNTS.get(cat, 1) for cat in CATEGORY_AMOUNTS.keys()])
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
        
        await notify_group_func(group_message)


async def handle_amend_flow(query, parts, notify_group_func):
    """Handle the amend task flow (PRIVATE ONLY)."""
    if len(parts) == 2 and parts[1] == "categories":
        text = "❌ *Amend a Task*\n\nSelect a category:"
        keyboard = create_category_menu("amend")
        
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
        emoji = CATEGORY_EMOJIS.get(category, "📦")
        text = f"❌ *Amend a Task*\n\n{emoji} {category.title()} - Select a task:"
        
        keyboard = create_task_menu(category, "amend")
        
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
        await amend_task_by_id(query, int(parts[2]), notify_group_func)


async def amend_task_by_id(query, task_instance_id, notify_group_func):
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
        await notify_group_func(group_message)


async def handle_ask_flow(query, parts):
    """Handle the ask instructions flow (PRIVATE ONLY)."""
    if len(parts) == 2 and parts[1] == "categories":
        text = "❓ *Ask Instructions*\n\nSelect a category:"
        keyboard = create_category_menu("ask")
        
        await query.edit_message_text(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif len(parts) == 3 and parts[1] == "category":
        category = parts[2]
        emoji = CATEGORY_EMOJIS.get(category, "📦")
        text = f"❓ *Ask Instructions*\n\n{emoji} {category.title()} - Select a task:"
        
        keyboard = create_task_menu(category, "ask")
        
        await query.edit_message_text(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif len(parts) == 3 and parts[1] == "task":
        await show_task_instructions(query, int(parts[2]))


async def show_task_instructions(query, task_instance_id):
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
