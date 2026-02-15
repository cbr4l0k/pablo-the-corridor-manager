"""Automatic week rollover and summary messages.

This module handles:
- Checking if the current week has ended
- Sending a summary message to the group
- Creating a new week automatically
"""

from datetime import datetime, timedelta
from telegram.ext import Application
from telegram.constants import ParseMode

from src.database import get_db
from src.models import Person, TaskInstance, Week, TaskType
from src.menus import CATEGORY_AMOUNTS

# ========== CONFIGURATION ==========

# What time to check for week rollover? (24-hour format)
# This job runs daily at this time
ROLLOVER_CHECK_TIME = (23, 59)  # 11:59 PM

# Should we auto-create a new week?
AUTO_CREATE_NEW_WEEK = True

# New week deadline (days from Monday)
# 6 = Sunday, 5 = Saturday, etc.
NEW_WEEK_DEADLINE_DAY = 6  # Sunday

# New week deadline time (hour, minute)
NEW_WEEK_DEADLINE_TIME = (23, 59)  # 11:59 PM

# ====================================


async def check_and_rollover_week(app: Application, group_chat_id: int):
    """Check if week has ended and perform rollover if needed.
    
    This function:
    1. Checks if current week deadline has passed
    2. Sends summary message
    3. Closes current week
    4. Creates new week (if enabled)
    """
    with get_db() as db:
        # Get current active week
        current_week = db.query(Week).filter_by(closed=False).order_by(Week.deadline.desc()).first()
        
        if not current_week:
            # No active week - create one
            if AUTO_CREATE_NEW_WEEK:
                await create_new_week(db, app, group_chat_id)
            return
        
        # Check if deadline has passed
        now = datetime.now()
        if now < current_week.deadline:
            # Week still active
            return
        
        # Week has ended - perform rollover
        await perform_week_rollover(db, current_week, app, group_chat_id)


async def perform_week_rollover(db, current_week: Week, app: Application, group_chat_id: int):
    """Perform the week rollover process.
    
    1. Generate summary
    2. Send message to group
    3. Close current week
    4. Create new week
    """
    # Generate summary message
    summary = generate_week_summary(db, current_week)
    
    # Send to group
    try:
        await app.bot.send_message(
            chat_id=group_chat_id,
            text=summary,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"Failed to send week summary: {e}")
    
    # Close current week
    current_week.closed = True
    db.commit()
    
    # Create new week
    if AUTO_CREATE_NEW_WEEK:
        await create_new_week(db, app, group_chat_id)


def generate_week_summary(db, week: Week) -> str:
    """Generate a summary message for the completed week.
    
    Returns a message with:
    - Week completion status
    - Contributors (sorted by contribution)
    - Non-contributors with gentle reminder
    """
    # Get all task instances for the week
    all_instances = db.query(TaskInstance).filter_by(week_id=week.id).all()
    completed_tasks = [t for t in all_instances if t.status == "completed"]
    
    # Calculate total tasks
    total = sum([CATEGORY_AMOUNTS.get(cat, 1) for cat in CATEGORY_AMOUNTS.keys()])
    completed_count = len(completed_tasks)
    remaining = total - completed_count
    
    # Get all active people
    active_people = db.query(Person).filter_by(active=True).all()
    
    # Calculate contributions per person
    contributions = {}
    for task in completed_tasks:
        if task.completed_by:
            person = db.query(Person).get(task.completed_by)
            if person:
                if person.name not in contributions:
                    contributions[person.name] = 0
                contributions[person.name] += 1
    
    # Sort by contribution (descending)
    sorted_contributors = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
    
    # Find non-contributors
    contributor_names = set(contributions.keys())
    all_names = {p.name for p in active_people}
    non_contributors = sorted(all_names - contributor_names)
    
    # Build message
    message = f"📅 *Week {week.week_number}/{week.year} Summary*\n\n"
    
    # Overall status
    if remaining == 0:
        message += "🎉 *WEEK COMPLETE!* 🎉\n\n"
        message += f"All {total} tasks were completed! Amazing work everyone! 💪\n\n"
    else:
        progress_percent = int((completed_count / total) * 100) if total > 0 else 0
        message += f"📊 *Progress:* {completed_count}/{total} tasks ({progress_percent}%)\n"
        message += f"⚠️ {remaining} tasks were not completed.\n\n"
    
    # Thank contributors
    if sorted_contributors:
        message += "🌟 *Thank you to our contributors:*\n"
        for name, count in sorted_contributors:
            # Add emoji based on contribution level
            if count >= 5:
                emoji = "🏆"  # Top contributor
            elif count >= 3:
                emoji = "⭐"  # Great contributor
            else:
                emoji = "✅"  # Contributor
            
            message += f"{emoji} *{name}* - {count} task{'s' if count != 1 else ''}\n"
        
        message += "\n_Thanks to you, the corridor is a better place!_ 🏠✨\n\n"
    
    # Gentle reminder for non-contributors
    if non_contributors:
        message += "💭 *We missed you this week:*\n"
        message += ", ".join(non_contributors)
        message += "\n\n"
        message += (
            "_We would love to see you participate next week! "
            "Is there any reason you couldn't contribute to the tasks? "
            "Feel free to reach out if you need help or have concerns._\n\n"
        )
    
    message += "➡️ *New week starting now!* Let's keep our corridor clean! 🧹"
    
    return message


async def create_new_week(db, app: Application, group_chat_id: int):
    """Create a new week with task instances.
    
    This creates:
    1. New Week entry
    2. TaskInstances for all active TaskTypes
    3. Announcement message to group
    """
    # Calculate week number and deadline
    now = datetime.now()
    year = now.year
    week_number = now.isocalendar()[1]
    
    # Calculate next deadline
    # Find the next occurrence of DEADLINE_DAY
    days_until_deadline = (NEW_WEEK_DEADLINE_DAY - now.weekday()) % 7
    if days_until_deadline == 0:
        # If today is the deadline day, set it for next week
        days_until_deadline = 7
    
    deadline = now + timedelta(days=days_until_deadline)
    deadline = deadline.replace(
        hour=NEW_WEEK_DEADLINE_TIME[0],
        minute=NEW_WEEK_DEADLINE_TIME[1],
        second=59
    )
    
    # Create week
    new_week = Week(
        week_number=week_number,
        year=year,
        deadline=deadline,
        closed=False
    )
    db.add(new_week)
    db.flush()  # Get the ID
    
    # Create task instances for all task types
    task_types = db.query(TaskType).all()
    for task_type in task_types:
        task_instance = TaskInstance(
            task_type_id=task_type.id,
            week_id=new_week.id,
            status="pending"
        )
        db.add(task_instance)
    
    db.commit()
    
    # Send announcement to group
    total = sum([CATEGORY_AMOUNTS.get(cat, 1) for cat in CATEGORY_AMOUNTS.keys()])
    announcement = (
        f"🆕 *New Week Started!*\n\n"
        f"📅 Week {week_number}/{year}\n"
        f"⏰ Deadline: {deadline.strftime('%A, %B %d at %H:%M')}\n"
        f"📋 Tasks to complete: {total}\n\n"
        f"Let's make this week great! ¡Hagámosle pues! 💪"
    )
    
    try:
        await app.bot.send_message(
            chat_id=group_chat_id,
            text=announcement,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"Failed to send new week announcement: {e}")


def setup_week_rollover(app: Application, group_chat_id: int):
    """Setup automatic week rollover job.
    
    This schedules a daily job that checks if the week needs to roll over.
    
    Args:
        app: The Telegram Application instance
        group_chat_id: The group chat ID to send messages to
    """
    from datetime import time
    
    job_queue = app.job_queue
    
    # Schedule daily check at configured time
    check_time = time(hour=ROLLOVER_CHECK_TIME[0], minute=ROLLOVER_CHECK_TIME[1])
    
    job_queue.run_daily(
        callback=lambda context: check_and_rollover_week(app, group_chat_id),
        time=check_time,
        name="week_rollover_check"
    )
    
    print(f"✅ Week rollover scheduled:")
    print(f"   Check time: {check_time.strftime('%H:%M')} daily")
    print(f"   Auto-create new week: {AUTO_CREATE_NEW_WEEK}")
    print(f"   New week deadline: {NEW_WEEK_DEADLINE_DAY} (0=Mon, 6=Sun) at {NEW_WEEK_DEADLINE_TIME[0]:02d}:{NEW_WEEK_DEADLINE_TIME[1]:02d}")


# ========== MANUAL TRIGGER (for testing) ==========

async def force_week_rollover(app: Application, group_chat_id: int):
    """Manually trigger a week rollover.
    
    Use this for testing or manual rollover.
    Can be called from a command like /closeweek
    """
    with get_db() as db:
        current_week = db.query(Week).filter_by(closed=False).order_by(Week.deadline.desc()).first()
        
        if not current_week:
            return "❌ No active week to close."
        
        await perform_week_rollover(db, current_week, app, group_chat_id)
        return "✅ Week rolled over manually!"


# ========== USAGE EXAMPLE ==========
"""
In your main bot.py file:

from src.week_manager import setup_week_rollover

# After creating the Application:
app = Application.builder().token(token).build()

# Setup week rollover (in addition to reminders)
setup_week_rollover(app, group_chat_id)

# Then start the bot
app.run_polling()
"""
