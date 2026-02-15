"""Opt-out related handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src.database import get_db
from src.models import Person, TaskType, TaskOptOut


async def cmd_optout(update: Update, context: ContextTypes.DEFAULT_TYPE, is_private_chat_func, redirect_func, notify_group_func):
    """Allow user to opt out of a task (PRIVATE ONLY)."""
    # Check if private chat
    if not is_private_chat_func(update):
        await redirect_func(update, "Opt Out")
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
        await notify_group_func(group_message)


async def handle_optout_flow(query):
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


async def cmd_who_opted_out(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def show_whooptedout_callback(query):
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
