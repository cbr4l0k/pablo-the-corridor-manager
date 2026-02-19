# Quick Start Guide

## 🚀 Get Up and Running in 5 Minutes

## TypeScript + Local Convex (Migration Path)

```bash
bun install
cp .env.local.example .env.local
bun run convex:dev:local
```

In another terminal:

```bash
bun run seed:convex
bun run bot:dev
```

### Prerequisites Check
```bash
# Check if you have the required tools
python --version  # Should be 3.10+
docker --version
docker-compose --version
```

### Step 1: Get a Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Follow prompts to name your bot
4. Copy the token (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Get Your Group Chat ID

1. Add your bot to your corridor group
2. Send any message in the group (e.g., "test")
3. Visit this URL in your browser (replace `<YOUR_TOKEN>`):
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
4. Look for `"chat":{"id":-1001234567890}`
5. Copy that negative number (e.g., `-1001234567890`)

### Step 3: Configure

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your favorite editor
nano .env  # or vim, code, etc.
```

Set these values:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=-1001234567890
POSTGRES_PASSWORD=choose_something_secure
```

Save and exit.

### Step 4: Start Database

```bash
docker-compose up -d
```

Wait 10 seconds for PostgreSQL to start up.

### Step 5: Setup Python Environment

```bash
# Install dependencies with uv (much faster than pip!)
uv sync

# This creates a .venv directory and installs all dependencies
# No need to manually create or activate virtual environment!
```

### Step 6: Initialize Database

```bash
uv run python scripts/populate_db.py
```

You should see:
```
INFO - Creating task types...
INFO - Created 22 task types
INFO - Creating test people...
INFO - Created 3 test people
INFO - Creating current week...
INFO - Created week X/2026 with 22 task instances
INFO - Database population completed successfully!
```

### Step 7: Verify Setup

```bash
uv run python scripts/test_setup.py
```

All tests should pass ✅

### Step 8: Start the Bot

```bash
uv run python src/bot.py
```

You should see:
```
INFO - Starting Corridor Bot...
INFO - Application started
```

### Step 9: Test It!

In your Telegram corridor group:

1. Send `/start` - Bot should welcome you
2. Send `/status` - Should show this week's tasks
3. Send `/tasks` - Should list all 22 tasks
4. Send `/complete Toilet 1` - Should mark task complete
5. Send `/mystats` - Should show your stats

## 🎉 Success!

You now have a working corridor cleaning bot!

## Common Issues

### "Connection refused" when starting bot
- PostgreSQL not running: `docker-compose up -d`
- Wait 10-20 seconds after starting PostgreSQL

### "No active week found"
- Database not populated: `python scripts/populate_db.py`

### Bot doesn't respond in group
- Bot not admin in group (doesn't need to be, but helps)
- Wrong TELEGRAM_CHAT_ID in .env
- Check token is correct: visit `https://api.telegram.org/bot<TOKEN>/getMe`

### "Database already contains data"
- Reset it: `python scripts/reset_db.py`
- Then repopulate: `python scripts/populate_db.py`

## Using Makefile (Optional Shortcut)

If you have `make` installed:

```bash
make setup      # Initial setup
make install    # Install dependencies with uv
make populate   # Populate database
make test       # Run tests
make start      # Start bot
make reset      # Reset database (dangerous!)
```

## Next Steps

1. Add your real corridor members (they use `/start`)
2. Configure task opt-outs if needed (see README.md)
3. Start using it for real!
4. Later: Add scheduled reminders (Phase 2)

## Help & Support

- Full documentation: `README.md`
- Database guide: Check pgAdmin at `http://localhost:5050`
- Reset everything: `make reset && make populate`

---

**Ready to clean! 🧹**
