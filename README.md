# Pablo: The Corridor Manager 🧹

![pablo-the-corridor-manager](./docs/pablito.png)

    > trust on pablito, he knows what to do.

This is software for managing taks of a corridor, helps setting timed reminders of tasks, keeping track of done tasks and administering penalties if unmet criteria, all with a telegram bot interface.

## Principles

This bot is designed to manage the corridor tasks in a fair and transparent way, promoting cooperation and shared responsibility among residents. The main principles are:

1. **Uneven contribution**: Not everyone has to do the same amount of tasks every week, but over time everyone should contribute fairly according to their capabilities and availability. This system allows for flexibility and acknowledges that some weeks people may be busier than others. But makes clear when someone is not contributing and asks why. 


---

## Features (Phase 1 - MVP)

✅ User registration via `/start`  
✅ Task completion tracking  
✅ Weekly status reports  
✅ Task instructions  
✅ Personal statistics  
✅ Task opt-out system (for people with private fridges, etc.)  
✅ PostgreSQL database with proper data modeling  

## Architecture

```
corridor-bot/
├── src/
│   ├── bot.py           # Main bot implementation
│   ├── models.py        # SQLAlchemy database models
│   ├── database.py      # Database connection
│   └── config.py        # Configuration management
├── scripts/
│   ├── populate_db.py   # Initial data population
│   └── reset_db.py      # Database reset utility
├── alembic/             # Database migrations
├── docker-compose.yml   # PostgreSQL container setup
├── requirements.txt     # Python dependencies
└── .env                 # Environment variables (create from .env.example)
```

## Prerequisites

- Python 3.10+
- Docker & Docker Compose (for PostgreSQL)
- A Telegram Bot Token (from [@BotFather](https://t.me/botfather))

## Quick Start

### 1. Clone and Setup

```bash
cd corridor-bot
cp .env.example .env
```

### TypeScript + Convex Migration Bootstrap (Bun)

For the parity migration workstream, initialize Convex and schema tooling with Bun:

```bash
bun install
bun run convex:dev
```

In a separate terminal, run the parity seed entrypoint:

```bash
bun run seed:convex
```

This will seed:
- Canonical task types from `scripts/populate_db.py`
- Current ISO week record (if missing)
- Task instances for all task types in that week (parity behavior)

### 2. Configure Environment

Edit `.env` and set:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_group_chat_id
POSTGRES_PASSWORD=choose_a_secure_password
```

**Getting your Telegram Chat ID:**
1. Add your bot to your corridor group
2. Send a message in the group
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Look for `"chat":{"id":-1001234567890}` - that's your chat ID

### 3. Start PostgreSQL

```bash
docker-compose up -d
```

This starts:
- PostgreSQL on port 5432
- pgAdmin on port 5050 (optional, for database management)

### 4. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Initialize Database

```bash
# Populate with initial data (task types, test users, current week)
python scripts/populate_db.py
```

This creates:
- All 22 task types (toilets, showers, kitchen, fridges, etc.)
- 3 test users (Alice, Bob, Charlie)
- Current week with all task instances

### 6. Run the Bot

```bash
python src/bot.py
```

You should see:
```
INFO - Starting Corridor Bot...
INFO - Application started
```

## Usage

### Basic Commands

**For Users:**
- `/start` - Register as a new user
- `/help` - Show all commands
- `/status` - View this week's task status
- `/tasks` - List all available tasks
- `/complete <task>` - Mark a task complete (e.g., `/complete Toilet 1`)
- `/done <task>` - Alias for `/complete`
- `/ask <task>` - Get instructions for a task
- `/mystats` - View your personal statistics

### Testing with Fake Users

The database comes with 3 test users:
- **Alice** (ID: 123456789) - Opted out of all fridges
- **Bob** (ID: 987654321)
- **Charlie** (ID: 555555555)

You can test by:
1. Creating a private chat with your bot
2. Sending `/start` to register your real Telegram account
3. Using the commands above

### Database Management (Optional)

**Access pgAdmin:**
1. Open http://localhost:5050
2. Login with credentials from `.env` (default: admin@corridor.local / admin)
3. Add server:
   - Host: postgres
   - Database: corridor
   - User/Password: from your `.env`

**Reset Database:**
```bash
python scripts/reset_db.py
python scripts/populate_db.py
```

## Data Model

### Core Tables

**people** - Corridor residents
- Stores Telegram ID, name, username
- Tracks active status

**task_types** - Task definitions
- 22 predefined tasks (toilets, showers, kitchen, etc.)
- Includes instructions, duration estimates, locations

**task_opt_outs** - Task exemptions
- People with private fridges/kitchens can opt out
- Stores reason for opt-out

**weeks** - Weekly cycles
- Tracks year, week number, deadline
- Closed flag prevents late completions

**task_instances** - Specific tasks for each week
- Links week + task_type
- Tracks completion status, who completed, when

**completion_log** - Audit trail
- Logs all completion actions
- Useful for disputes/corrections

**penalties** - Penalty tracking (Phase 2)
- Currently unused, reserved for future

## Configuration

### Week Settings

Edit in `.env`:
```env
WEEK_DEADLINE_DAY=friday
WEEK_DEADLINE_HOUR=12
WEEK_DEADLINE_MINUTE=0
```

### Database Connection

PostgreSQL settings in `.env`:
```env
POSTGRES_DB=corridor
POSTGRES_USER=corridor_admin
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost  # or container name if bot runs in Docker
POSTGRES_PORT=5432
```

## Development

### Project Structure

```python
# src/models.py - Database models
Person, TaskType, TaskOptOut, Week, TaskInstance, CompletionLog, Penalty

# src/database.py - Database utilities
init_db()          # Create all tables
drop_db()          # Drop all tables
get_db()           # Context manager for sessions
get_db_session()   # Direct session (remember to close!)

# src/bot.py - Bot implementation
CorridorBot class with command handlers

# src/config.py - Configuration
Settings class (loaded from .env)
```

### Adding New Task Types

```python
from src.database import get_db
from src.models import TaskType

with get_db() as db:
    new_task = TaskType(
        name="Balcony",
        category="outdoor",
        description="Clean the balcony area",
        instructions="1. Sweep floor\n2. Wipe railings\n3. Empty ashtray",
        estimated_duration_minutes=15,
        location="3rd floor balcony"
    )
    db.add(new_task)
```

### Adding Opt-Outs

```python
from src.models import Person, TaskType, TaskOptOut

with get_db() as db:
    person = db.query(Person).filter_by(telegram_id=123456789).first()
    task = db.query(TaskType).filter_by(name="Fridge 1").first()
    
    opt_out = TaskOptOut(
        person_id=person.id,
        task_type_id=task.id,
        reason="Has private fridge in room"
    )
    db.add(opt_out)
```

## Troubleshooting

### Bot doesn't start
- Check `TELEGRAM_BOT_TOKEN` in `.env`
- Verify token with: `curl https://api.telegram.org/bot<TOKEN>/getMe`

### Database connection fails
- Ensure Docker containers are running: `docker-compose ps`
- Check PostgreSQL logs: `docker-compose logs postgres`
- Verify credentials in `.env` match docker-compose.yml

### Tasks not showing
- Check if current week exists: `python -c "from src.database import *; from src.models import *; db = get_db_session(); print(db.query(Week).all())"`
- Re-run population script: `python scripts/populate_db.py`

### "No active week found"
- Week might have auto-closed (if deadline passed)
- Manually create a new week or wait for Monday automation (Phase 2)

## Next Steps (Phase 2)

- [ ] Scheduled reminders (Wednesday, Friday)
- [ ] Automatic week generation (Monday 00:01)
- [ ] Automatic week closing (Friday 12:01)
- [ ] Penalty calculation
- [ ] Photo evidence for task completion
- [ ] Admin commands for manual week management

## Next Steps (Phase 3)

- [ ] Analytics dashboard (Grafana)
- [ ] Leaderboard command
- [ ] Task difficulty ratings
- [ ] Time-series analysis (procrastinated tasks, popular days, etc.)

## License

MIT

## Support

For issues or questions:
1. Check this README
2. Review `scripts/populate_db.py` for data structure examples
3. Check database with pgAdmin
4. Open an issue on GitHub (if applicable)
