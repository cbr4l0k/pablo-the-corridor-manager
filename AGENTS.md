# AGENTS.md

## Purpose
This document is the execution playbook for migrating this project from Python to TypeScript using Convex for data/backend logic and Telegram Bot API integrations.

This is a parity-first migration:
1. Reproduce current behavior exactly.
2. Cut over safely.
3. Apply improvements only after parity is validated.

## Scope and Non-Goals
### In Scope
- Migrate bot logic from Python modules in `src/` to TypeScript.
- Move persistent data model from SQLAlchemy/PostgreSQL shape to Convex schema.
- Preserve all existing command and callback behaviors.
- Preserve reminder and week rollover automation.
- Preserve private-vs-group action restrictions.

### Out of Scope (until post-parity phase)
- New features.
- UX redesign.
- Changes to command semantics.
- Penalty automation (table exists but current behavior does not operationalize it).

## Current System Map (Python)
### Entrypoint and orchestration
- `src/bot.py`: Creates Telegram app, registers command/callback handlers, enforces private-chat restrictions, sends group notifications, schedules reminders and week rollover jobs.

### Domain and data
- `src/models.py`: Core entities:
  - `Person`
  - `TaskType`
  - `TaskOptOut`
  - `Week`
  - `TaskInstance`
  - `CompletionLog`
  - `Penalty`
- `src/database.py`: SQLAlchemy engine/session helpers.
- `scripts/populate_db.py`: Seeds canonical task types and creates current week + task instances.

### Interaction flows
- `src/handlers/task_handlers.py`:
  - Complete flow
  - Amend flow
  - Ask instructions flow
- `src/handlers/info_handlers.py`:
  - Status, tasks, stats, map
- `src/handlers/optout_handlers.py`:
  - Opt-out command and listings
- `src/menus.py`:
  - Inline keyboard composition
  - Category quotas and emojis used in progress math and menus

### Automation
- `src/reminders.py`: Reminder scheduler and reminder message generation.
- `src/week_manager.py`: Deadline check, weekly summary, week close/open, new week announcement.

## Behavioral Contracts to Preserve
### Commands
- `/start`: Register person if missing; show menu adjusted to chat type.
- `/menu`: Show private or group menu variant.
- `/help`: Show command help adjusted to chat type.
- `/status`: Detailed weekly status.
- `/tasks`: Task catalog grouped by category.
- `/mystats`: Personal stats (private only).
- `/map`: Sends corridor map image (private only).
- `/optout <task> <reason>`: Task opt-out (private only).
- `/whooptedout [task]`: Opt-out listing (public/private).

### Callback data grammar
Format: `action[:scope[:id_or_category]]`

Supported actions:
- `menu`
- `status`
- `tasks`
- `mystats`
- `map`
- `help`
- `whooptedout`
- `complete`
- `amend`
- `ask`
- `optout`

### Chat scope policy
Public-safe:
- `status`, `tasks`, `whooptedout`, `help`, `menu`

Private-only:
- `complete`, `amend`, `ask`, `optout`, `mystats`, `map`

If a private-only action is invoked from a group context, reply with private-chat redirect behavior.

## Data Model Migration Contract (SQLAlchemy -> Convex)
Define Convex tables mirroring current domain semantics.

### `people`
- `telegramId` (unique, indexed)
- `name`
- `username` (optional)
- `joinedDate`
- `active` (default true)

### `taskTypes`
- `name` (unique)
- `category`
- `description`
- `instructions`
- `mediaFileId` (optional)
- `frequency` (default weekly)
- `estimatedDurationMinutes` (optional)
- `location` (optional)

### `taskOptOuts`
- `personId` (ref `people`)
- `taskTypeId` (ref `taskTypes`)
- `reason`
- `createdAt`
- unique pair: (`personId`, `taskTypeId`)

### `weeks`
- `year`
- `weekNumber`
- `startDate`
- `deadline`
- `closed` (default false)
- unique pair: (`year`, `weekNumber`)

### `taskInstances`
- `weekId` (ref `weeks`)
- `taskTypeId` (ref `taskTypes`)
- `status` in `pending | completed | skipped`
- `completedBy` (optional ref `people`)
- `completedAt` (optional)
- `notes` (optional)
- unique pair: (`weekId`, `taskTypeId`)

### `completionLog`
- `taskInstanceId` (ref `taskInstances`)
- `personId` (optional ref `people`)
- `action` (string enum, includes at least `completed`, `amended`)
- `timestamp`
- `messageId` (optional)

### `penalties`
- `personId` (ref `people`)
- `weekId` (ref `weeks`)
- `amountEur`
- `penaltyType`
- `paid`
- `paidAt` (optional)
- `paidVia` (optional)

## Known Quirks to Preserve in Parity Phase
1. Progress totals in several views use category quota constants (`CATEGORY_AMOUNTS`) instead of counting actual task rows.
2. Week creation creates task instances for all task types, regardless of opt-outs. Opt-outs block claiming/completion, not instance generation.

## TypeScript Target Architecture (Single Repo, Single Runtime)
Use one TypeScript codebase with modular boundaries:

1. `src/domain/*`
- Pure domain types, constants, and message assembly helpers.

2. `src/telegram/*`
- Command routing.
- Callback routing.
- Private/group guard utilities.
- Telegram API client wrappers (official Bot API calls via typed HTTP wrappers).

3. `convex/schema.ts` and `convex/*`
- Schema and indexes.
- Queries/mutations/actions for each flow.

4. `src/jobs/*`
- Reminder scheduler.
- Week rollover scheduler.

5. `src/app.ts` (or equivalent)
- Bootstraps Telegram update handling + scheduler wiring.

## Handler/Flow Mapping
### Task flows
- `handle_complete_flow` -> TS callback pipeline:
  - show categories -> show tasks -> complete task by instance id.
- `handle_amend_flow` -> show categories -> show completed tasks -> amend selected task.
- `handle_ask_flow` -> show categories -> show tasks -> show task instructions.

### Info flows
- `cmd_status` and callback summary view.
- `cmd_tasks` and callback short view.
- `cmd_my_stats` and callback short stats.
- `cmd_show_map` and callback map behavior.

### Opt-out flows
- `cmd_optout` command validation and creation.
- `cmd_who_opted_out` with optional task filter.
- callback short listing.

## Scheduler Contracts
### Reminders
- Days: Tuesday and Friday.
- Times: 10:00 and 18:00.
- Behavior:
  - If all tasks done: celebration message.
  - Else: remaining tasks, progress bar, deadline messaging, and non-contributors.

### Week rollover
- Daily check at 23:59.
- If no active week and auto-create enabled: create new week.
- If current week deadline passed:
  - Generate summary.
  - Post summary to group.
  - Mark week closed.
  - Create next week.
  - Post new-week announcement.

## Implementation Phases
### Phase A: Domain and data parity
- Implement Convex schema and indexes.
- Implement seed script equivalent of Python `populate_db` task definitions.
- Ensure an active week + task instances can be created identically.

Acceptance:
- Seeded task types and week/task instances match Python semantics.
- Uniqueness and status constraints enforced.

### Phase B: Read-only behavior parity
- Implement `/start`, `/menu`, `/help`, `/status`, `/tasks`, `/whooptedout`, `/map`, `/mystats` read paths and callback short views.

Acceptance:
- Message content and branching logic are equivalent at functional level.
- Private/group restrictions enforced.

### Phase C: Mutating flow parity
- Implement complete/amend/ask callback flows.
- Implement `/optout` command flow.
- Implement group notifications and completion logs.

Acceptance:
- Task state transitions and logs match Python behavior.
- Error cases match current outcomes (already completed, missing registration, opt-out block).

### Phase D: Scheduler parity
- Implement reminder jobs.
- Implement rollover jobs and summary/new-week announcements.

Acceptance:
- Jobs execute on configured cadence and produce expected side effects.

### Phase E: Post-parity fixes (explicitly deferred)
- Replace quota-constant totals with computed totals from real task instances.
- Centralize week deadline config and remove hardcoded splits across modules.
- Reduce repeated lookup patterns in contributor computations.
- Align docs/changelog with actual shipped behavior.

## Test Scenarios (Must Pass Before Cutover)
1. New user `/start` creates one person record and does not duplicate on repeated `/start`.
2. Group context invoking private-only action returns private redirect behavior.
3. Completing a pending task updates `taskInstances` and inserts `completionLog`.
4. Completing already-completed task is rejected.
5. Opted-out user cannot complete opted-out task.
6. Amend transitions completed task back to pending and logs amendment.
7. `/status` and callback status both render coherent progress from same source of truth.
8. `/whooptedout` with and without task argument returns expected lists.
9. Reminder content branches correctly for all-done vs pending and deadline proximity.
10. Rollover closes current week, posts summary, creates next week, and creates next task instances.

## Cutover Definition of Done
1. All parity tests pass.
2. End-to-end manual run in a Telegram test group passes command/callback/scheduler smoke checks.
3. Production token/chat configuration validated.
4. Python bot disabled only after TS runtime proves stable through at least one full reminder cycle and one week rollover check window.

## Defaults and Assumptions
1. Parity-first policy is mandatory.
2. Single repo/single runtime architecture is the target.
3. Telegram integration uses official Bot API through typed HTTP wrappers by default.
4. No repo-wide behavior changes outside migration scope during parity phases.
