"""Task reminder scheduler.

CONFIGURATION:
- Edit REMINDER_DAYS to set which days reminders are sent
- Edit REMINDER_TIMES to set what times reminders are sent
- Edit DEADLINE_DAY to change when the week ends
"""

from datetime import datetime, time, timedelta
from telegram.ext import Application
from telegram.constants import ParseMode

from src.database import get_db
from src.models import Person, TaskInstance, Week
from src.menus import CATEGORY_AMOUNTS

# ========== CONFIGURATION ==========

# Which days to send reminders (0=Monday, 6=Sunday)
REMINDER_DAYS = [1, 4]  # Tuesday and Friday

# What times to send reminders (24-hour format)
REMINDER_TIMES = [
    time(10, 0),  # 10:00 AM
    time(18, 0),  # 6:00 PM
]

# When does the week end? (0=Monday, 6=Sunday)
DEADLINE_DAY = 6  # Sunday

# ====================================


async def send_reminder(app: Application, group_chat_id: int):
    """Send a reminder about pending tasks to the group."""
    with get_db() as db:
        current_week = db.query(Week).filter_by(closed=False).order_by(Week.deadline.desc()).first()
        
        if not current_week:
            return  # No active week
        
        # Get all task instances for the week
        all_instances = db.query(TaskInstance).filter_by(week_id=current_week.id).all()
        completed_count = len([t for t in all_instances if t.status == "completed"])
        total = sum([CATEGORY_AMOUNTS.get(cat, 1) for cat in CATEGORY_AMOUNTS.keys()])
        remaining = total - completed_count
        
        if remaining == 0:
            # All tasks done - send celebration
            message = (
                "🎉 *All tasks completed!*\n\n"
                "Great work everyone! Time to relax 😎🍹"
            )
        else:
            # Tasks remaining - send reminder
            # Calculate days until deadline
            now = datetime.now()
            days_until_deadline = (current_week.deadline - now).days
            
            if days_until_deadline < 0:
                time_msg = "⚠️ *OVERDUE!*"
            elif days_until_deadline == 0:
                time_msg = "⏰ *Due TODAY!*"
            elif days_until_deadline == 1:
                time_msg = "⏰ *Due TOMORROW!*"
            else:
                time_msg = f"⏰ Due in *{days_until_deadline} days*"
            
            # Get non-contributors
            completed = [t for t in all_instances if t.status == "completed"]
            completed_by_ids = [t.completed_by for t in completed if t.completed_by]
            active_people = db.query(Person).filter_by(active=True).all()
            not_contributed = [p for p in active_people if p.id not in completed_by_ids]
            
            progress = int((completed_count / total) * 10) if total > 0 else 0
            progress_bar = "█" * progress + "░" * (10 - progress)
            
            message = (
                f"📢 *Task Reminder*\n\n"
                f"{time_msg}\n"
                f"Deadline: {current_week.deadline.strftime('%A, %B %d at %H:%M')}\n\n"
                f"📊 Progress: {progress_bar} {completed_count}/{total}\n"
                f"🔴 *{remaining} tasks* still need to be done!\n\n"
            )
            
            if not_contributed:
                message += f"💭 *Haven't contributed yet:*\n"
                message += ", ".join([p.name for p in not_contributed])
                message += "\n\n"
            
            message += "¡Hagámosle pues! 💪"
        
        # Send to group
        try:
            await app.bot.send_message(
                chat_id=group_chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print(f"Failed to send reminder: {e}")


def setup_reminders(app: Application, group_chat_id: int):
    """Setup reminder jobs.
    
    Call this function from your main bot to schedule reminders.
    
    Args:
        app: The Telegram Application instance
        group_chat_id: The group chat ID to send reminders to
    """
    job_queue = app.job_queue
    
    # Schedule reminders for each day and time
    for day in REMINDER_DAYS:
        for reminder_time in REMINDER_TIMES:
            job_queue.run_daily(
                callback=lambda context: send_reminder(app, group_chat_id),
                time=reminder_time,
                days=(day,),  # Tuple of days
                name=f"reminder_{day}_{reminder_time.hour}_{reminder_time.minute}"
            )
    
    print(f"✅ Reminders scheduled:")
    print(f"   Days: {REMINDER_DAYS} (0=Mon, 6=Sun)")
    print(f"   Times: {[t.strftime('%H:%M') for t in REMINDER_TIMES]}")
    print(f"   Deadline day: {DEADLINE_DAY} (changes week end)")


def get_week_deadline(week_number: int, year: int) -> datetime:
    """Calculate the deadline for a given week.
    
    This function determines when a week ends based on DEADLINE_DAY.
    
    Args:
        week_number: The ISO week number
        year: The year
        
    Returns:
        datetime of the deadline (DEADLINE_DAY at 23:59)
    """
    # Get the Monday of the given week
    jan_4 = datetime(year, 1, 4)  # Jan 4 is always in week 1
    week_start = jan_4 - timedelta(days=jan_4.weekday()) + timedelta(weeks=week_number - 1)
    
    # Calculate deadline day
    deadline = week_start + timedelta(days=DEADLINE_DAY)
    deadline = deadline.replace(hour=23, minute=59, second=59)
    
    return deadline


# ========== USAGE EXAMPLE ==========
"""
In your main bot.py file:

from src.reminders import setup_reminders

# After creating the Application:
app = Application.builder().token(token).build()

# Setup reminders
setup_reminders(app, group_chat_id)

# Then start the bot
app.run_polling()
"""
