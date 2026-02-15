"""Information handlers: status, stats, tasks list, map."""

from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src.database import get_db
from src.models import Person, TaskType, TaskInstance, Week, TaskOptOut
from src.menus import CATEGORY_AMOUNTS, CATEGORY_EMOJIS

# Get project root for media files
project_root = Path(__file__).parent.parent.parent


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            by_category[category]["total"] = CATEGORY_AMOUNTS.get(category, 1)
            if task.status == "completed":
                by_category[category]["completed"] += 1
        
        for category in sorted(by_category.keys()):
            emoji = CATEGORY_EMOJIS.get(category, "📦")
            stats = by_category[category]
            progress = int((stats["completed"] / stats["total"]) * 10) if stats["total"] > 0 else 0
            progress_bar = "█" * progress + "░" * (10 - progress)
            message += f"{emoji} {category.title()}: {progress_bar} {stats['completed']}/{stats['total']}\n"
        
        # Overall progress
        total = sum([CATEGORY_AMOUNTS.get(cat, 1) for cat in by_category.keys()])
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


async def show_status_callback(query):
    """Show status via callback (AVAILABLE IN BOTH)."""
    with get_db() as db:
        current_week = db.query(Week).filter_by(closed=False).order_by(Week.deadline.desc()).first()
        
        if not current_week:
            await query.edit_message_text("❌ No active week found.")
            return
        
        # Get progress summary
        all_instances = db.query(TaskInstance).filter_by(week_id=current_week.id).all()
        completed_count = len([t for t in all_instances if t.status == "completed"])
        total = sum([CATEGORY_AMOUNTS.get(cat, 1) for cat in CATEGORY_AMOUNTS.keys()])
        
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


async def cmd_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            emoji = CATEGORY_EMOJIS.get(category, "📦")
            target = CATEGORY_AMOUNTS.get(category, 1)
            message += f"{emoji} *{category.title()}* [Complete {target}/week]\n"
            for task in tasks:
                duration = f" ({task.estimated_duration_minutes}min)" if task.estimated_duration_minutes else ""
                message += f"  • {task.name}{duration}\n"
            message += "\n"
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


async def show_tasks_callback(query):
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
            emoji = CATEGORY_EMOJIS.get(category, "📦")
            target = CATEGORY_AMOUNTS.get(category, 1)
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


async def cmd_my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, is_private_chat_func, redirect_func):
    """Show detailed personal stats (PRIVATE ONLY)."""
    if not is_private_chat_func(update):
        await redirect_func(update, "My Stats")
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


async def show_stats_callback(query):
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


async def cmd_show_map(update: Update, context: ContextTypes.DEFAULT_TYPE, is_private_chat_func, redirect_func):
    """Show corridor map (PRIVATE ONLY)."""
    if not is_private_chat_func(update):
        await redirect_func(update, "Map")
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


async def show_map_callback(query):
    """Show map via callback (PRIVATE ONLY)."""
    media_path = project_root / "media" / "corridor-overview.jpg"
    
    if media_path.exists():
        with open(media_path, "rb") as img_file:
            await query.message.reply_photo(
                photo=img_file,
                caption="🗺️ *Corridor Map*",
                parse_mode=ParseMode.MARKDOWN
            )
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
