# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot that integrates OpenAI's Assistant API with aiogram 3.4+. The bot supports multiple assistants, voice messages via Whisper, PDF processing with RAG, voice calls through Vapi.ai integration, and a task tracker with AI mentor for stress management and productivity.

## Development Commands

**Run the bot:**
```bash
python -m gptbot
```

**Run tests:**
```bash
pip install pytest pytest-asyncio freezegun
pytest -vv test.py
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

## Architecture

### Core Components

- **handlers.py**: Main aiogram router with message handlers and middleware
- **actions.py**: OpenAI Assistant API interactions and message processing logic
- **client.py**: OpenAI client setup and thread/assistant management
- **assistants_factory.py**: Assistant management with YAML persistence
- **users.py**: User access control and allowed users management
- **modes.py**: Bot operation modes (assistant, gpt-4.1, o4-mini, tracker)
- **tracker.py**: Task tracker with 6-step onboarding and AI mentor system
- **file_search.py**: PDF processing and RAG functionality
- **voice.py**: Voice message transcription via Whisper
- **message_queues.py**: Request queuing and rate limiting

### Configuration Files

- **tutors.yaml**: Assistant configurations and user preferences
- **threads.yaml**: Thread state persistence
- **tracker_data.yaml**: Tracker user data and AI mentor conversation history
- **allowed_users.yaml**: User access control list
- **config.py**: Bot behavior settings (response delays, polling intervals)
- **env.py**: Environment variable definitions

### Message Flow

1. Messages arrive via aiogram handlers in `handlers.py`
2. Access control checked via `users.py` middleware
3. Thread/assistant retrieved via `client.py` and `assistants_factory.py`
4. Mode-specific processing in `actions.py` (Assistant API vs direct model calls vs tracker)
5. Tracker mode handling in `tracker.py` with welcome module and AI mentor
6. Queue management via `message_queues.py` for rate limiting
7. Response formatting and delivery

### Key Patterns

- All user state persisted in YAML files (threads, assistants, users)
- Async/await throughout with proper exception handling
- Markdown formatting with aiogram ParseMode.MARKDOWN
- File download to temporary directory with cleanup
- Voice transcription and PDF RAG as optional features

## Environment Variables

Set these before running:
- `BOT_TOKEN`: Telegram bot token
- `API_KEY`: OpenAI API key  
- `ORG_ID`: OpenAI organization ID
- `LOG_LEVEL`: Logging verbosity (default: INFO)
- `WEBAPP_URL`: Mini app URL for web interface
- `VAPI_API_KEY`: Vapi.ai API key (optional)
- `VAPI_ASSISTANT_ID`: Vapi.ai assistant ID (optional)

## Task Tracker System

### Overview

The tracker mode provides stress management and productivity features with a 6-step onboarding process and AI mentor integration.

### Access Tracker Mode

Users can switch to tracker mode via `/mode` command and selecting "tracker" from the keyboard.

### Welcome Module (Phase 1) - Completed ✅

**Step 1: Greeting & Purpose Explanation**
- Friendly welcome with anxiety-focused messaging
- Confidentiality assurance
- Progress bar: ●○○○○○ 1/6

**Step 2: Anxiety Assessment**
- 5-question Likert scale survey (1-5)
- Questions cover work anxiety, concentration, overwhelm, procrastination, stress sensitivity
- Optional step with skip option
- Automatic anxiety level calculation and interpretation

**Step 3: Goal Selection**
- 4 predefined goals: task management, stress reduction, productivity, time organization
- Multiple selection with checkboxes (✅/☐)
- Goals stored in user profile for personalization

**Step 4: Notification Settings**
- 3 notification types: daily digest, deadline reminders, new task notifications
- Individual toggles for each type
- Master enable/disable switch
- Note: Actual notification delivery not yet implemented

**Step 5: AI Mentor Introduction**
- Introduction to AI mentor capabilities
- First interaction with personalized context
- Option to skip or continue chatting
- Chat history preservation

**Step 6: Completion Summary**
- Review of all user settings
- Anxiety level, goals, notifications, AI mentor status
- Transition to main tracker functionality

### AI Mentor System

**Features:**
- Personalized system prompt for stress management and productivity
- Context awareness of user's anxiety level and goals
- Conversation history persistence (last 20 messages)
- Expertise areas: stress management, planning, procrastination, work-life balance

**Integration:**
- Seamless chat after welcome module completion
- User messages automatically routed to AI mentor
- Responses formatted with "🤖 AI-ментор:" prefix

### Data Storage

**tracker_data.yaml structure:**
```yaml
user_id:
  step: "greeting|anxiety_intro|anxiety_survey|goals|notifications|ai_mentor|completion"
  completed: boolean
  started_at: timestamp
  anxiety_level: float (1.0-5.0)
  anxiety_answers: [int, int, int, int, int]
  goals: ["task_management", "stress_reduction", "productivity", "time_organization"]
  notifications:
    daily_digest: boolean
    deadline_reminders: boolean
    new_task_notifications: boolean
    enabled: boolean
  met_ai_mentor: boolean
  ai_mentor_history: [{"role": "user|assistant", "content": "text"}, ...]
```

### Implementation Details

**Key Functions in tracker.py:**
- `process_tracker_message()`: Main message handler
- `process_tracker_callback()`: Inline keyboard handler
- `chat_with_ai_mentor()`: AI mentor communication with context
- `show_step_X()`: Individual step displays
- `TrackerUserData`: User data management class

**Navigation Features:**
- Back/forward buttons on each step
- Progress bar visualization
- State persistence between sessions
- Skip options for optional steps

### Future Development (Not Yet Implemented)

**Phase 2 - Core Tracker Features:**
- Task creation and management
- Priority setting and categorization
- Deadline tracking
- Progress monitoring

**Phase 3 - Notification System:**
- Scheduled daily digests
- Deadline reminders
- Background notification worker
- User timezone handling

**Phase 4 - Advanced Features:**
- Task analytics and insights
- Stress level tracking over time
- Productivity metrics
- Integration with calendar systems

### Development Notes for Future Work

**Current Implementation Status:**
- ✅ **Phase 1: Welcome Module** - Completed (January 2025)
- ✅ **Phase 2: Core Task Management** - Completed (January 2025)  
- ✅ **Phase 3: Notification System** - Completed (January 2025)

**Next Development Priorities (Phase 4):**

1. **Advanced Task Features**
   - Task deadline setting UI (deadlines work in background)
   - Task description editing interface
   - Task categories and tags
   - Task templates for common workflows
   - Bulk task operations (mark multiple as complete)

2. **Enhanced Analytics**
   - Productivity metrics dashboard
   - Stress level tracking over time
   - Task completion patterns analysis
   - Weekly/monthly productivity reports
   - Goal achievement tracking

3. **AI Mentor Enhancements**
   - Task-specific advice integration
   - Proactive check-ins based on user anxiety level
   - Personalized stress management techniques
   - Context-aware productivity suggestions
   - Integration with task completion patterns

4. **Advanced Notification Features**
   - Custom notification schedules per user
   - Smart notification timing based on activity patterns
   - Notification snoozing and postponing
   - Integration with external calendar systems
   - Reminder escalation for overdue tasks

5. **User Experience Improvements**
   - Task search and filtering by keywords
   - Quick actions with keyboard shortcuts
   - Export/import functionality for tasks
   - Multi-language support
   - Dark/light theme preferences

**Testing Current Implementation:**
- Run bot: `python -m gptbot`
- Use `/mode` → select "tracker"
- Test complete 3-phase system:
  - **Phase 1**: Complete welcome module flow
  - **Phase 2**: Create, manage, and organize tasks
  - **Phase 3**: Configure notifications and timezone
- Verify AI mentor conversations preserve context
- Check data persistence in `tracker_data.yaml`
- Test notification system with manual digest

**Current Status**: Phase 1 (Welcome Module) + Phase 2 (Core Task Management) + Phase 3 (Notification System) fully implemented and functional ✅

## Phase 2 - Core Task Management Features ✅

### Task Management System

**Features Implemented:**
- ✅ Task creation with title, description, and priority
- ✅ Task status tracking (pending, in_progress, completed, cancelled)  
- ✅ Task priority levels (low, medium, high, urgent)
- ✅ Complete CRUD operations (create, read, update, delete)
- ✅ Task filtering by status (pending, in_progress, completed)
- ✅ Task sorting by priority and creation date
- ✅ Interactive task management UI with inline keyboards

**Task Data Structure:**
```yaml
tasks:
  - id: "uuid"
    title: "Task title" 
    description: "Optional description"
    priority: "low|medium|high|urgent"
    status: "pending|in_progress|completed|cancelled"
    created_at: timestamp
    updated_at: timestamp
    due_date: timestamp (optional)
    completed_at: timestamp (optional)
```

**UI Navigation:**
- Main menu with task statistics
- Task list with quick actions
- Detailed task view with full management
- Priority selection interface
- Filtered views (in progress, completed)
- Task creation workflow

**Available Commands in Tracker Mode:**
- `/задачи`, `/tasks`, `задачи`, `tasks` - Show tasks menu
- `/новая`, `/new`, `новая задача`, `создать задачу` - Create new task
- `/меню`, `/menu`, `меню` - Show main menu

**Key Functions in tracker.py:**
- `create_task()` - Creates new task
- `update_task_status()` - Changes task status
- `update_task_priority()` - Changes task priority
- `delete_task()` - Removes task
- `get_tasks_by_status()` - Filters tasks by status
- `get_tasks_sorted()` - Sorts tasks by criteria
- `format_task_text()` - Formats task display
- `show_main_menu()` - Main interface
- `show_tasks_menu()` - Task list interface
- `show_task_detail()` - Individual task management

### Testing Task Management:
1. Run bot: `python -m gptbot`
2. Use `/mode` → select "tracker"
3. Complete welcome module if first time
4. Test main menu navigation
5. Create tasks with different priorities
6. Change task statuses (start, pause, complete)
7. Test filtering and task detail views
8. Verify data persistence in `tracker_data.yaml`

## Phase 3 - Notification System ✅

### Notification Features

**Core Features Implemented:**
- ✅ Background notification scheduler with threading
- ✅ Daily digest notifications (scheduled at 9:00 AM user time)
- ✅ Deadline reminder system (checks every 2 hours)
- ✅ New task notifications (instant)
- ✅ Timezone support for all users
- ✅ Manual notification testing
- ✅ Comprehensive notification settings UI

**Notification Types:**
1. **Daily Digest** - Morning summary of pending/in-progress tasks
2. **Deadline Reminders** - Alerts for tasks due within 24 hours
3. **New Task Notifications** - Instant alerts when tasks are created

**Timezone Support:**
- 12 popular timezones (Moscow, Kiev, London, NYC, etc.)
- Automatic locale detection
- Per-user timezone settings
- All timestamps displayed in user's local time

**Scheduler Architecture:**
- Background thread with `schedule` library
- Graceful shutdown handling with signal handlers
- Error handling and logging
- Configurable notification times

**Data Structure Extensions:**
```yaml
"user_id":
  timezone: "Europe/Moscow"
  notification_time: "09:00"
  notifications:
    enabled: true
    daily_digest: true
    deadline_reminders: true
    new_task_notifications: false
```

**Key Functions in notifications.py:**
- `NotificationManager` - Main notification controller
- `init_notifications()` - System initialization
- `start_scheduler()` - Background worker startup
- `send_daily_digest()` - Morning task summary
- `send_deadline_reminder()` - Deadline alerts
- `notify_new_task()` - Instant task notifications

**Settings Interface:**
- ⚙️ Settings menu from main tracker interface
- 🔔 Notification type toggles
- 🌍 Timezone selection with current time display
- 📬 Manual digest testing
- Real-time settings preview

**Integration Points:**
- Auto-notification on task creation
- Settings accessible from main menu
- Timezone-aware time display throughout tracker
- Graceful fallback if notifications disabled

### Testing Notification System:
1. Run bot: `python -m gptbot`
2. Complete tracker welcome module
3. Access settings: Main Menu → ⚙️ Настройки
4. Configure timezone: 🌍 Часовой пояс
5. Enable notifications: 🔔 Уведомления
6. Test manual digest: 📬 Тестовый дайджест
7. Create tasks and verify instant notifications
8. Check background scheduler logs

## Summary: Complete Tracker Implementation ✅

### Three-Phase Implementation Complete

**Phase 1: Welcome Module (6-Step Onboarding)** ✅
- Empathetic user experience with anxiety assessment
- Goal selection and notification preferences
- AI mentor introduction with conversation history
- Progress visualization and state persistence

**Phase 2: Core Task Management** ✅  
- Complete CRUD operations for tasks
- Priority system (low, medium, high, urgent) with visual indicators
- Status management (pending, in-progress, completed, cancelled)
- Interactive UI with inline keyboards and real-time statistics
- Task filtering, sorting, and detailed management views

**Phase 3: Notification System** ✅
- Background scheduler with threading and graceful shutdown
- Three notification types: daily digest, deadline reminders, new task alerts
- Comprehensive timezone support (12 popular timezones)
- Advanced settings interface with real-time preview
- Smart notification content with personalized insights

### Technical Architecture

**Core Files:**
- `tracker.py` (1000+ lines) - Complete tracker implementation
- `notifications.py` (400+ lines) - Notification management system
- `main.py` - Enhanced with notification system integration

**Data Structure:**
```yaml
user_data:
  # Phase 1 - Welcome Module
  step: "completed"
  completed: true
  anxiety_level: 2.5
  goals: ["task_management", "stress_reduction"]
  met_ai_mentor: true
  ai_mentor_history: [conversation...]
  
  # Phase 2 - Task Management  
  tasks:
    - id: "uuid"
      title: "Task title"
      description: "Task description"
      priority: "high"
      status: "in_progress"
      created_at: timestamp
      updated_at: timestamp
      due_date: timestamp
      completed_at: timestamp
  
  # Phase 3 - Notifications
  timezone: "Europe/Moscow"
  notification_time: "09:00"
  notifications:
    enabled: true
    daily_digest: true
    deadline_reminders: true
    new_task_notifications: false
```

### Feature Matrix

| Feature | Phase 1 | Phase 2 | Phase 3 | Status |
|---------|---------|---------|---------|---------|
| User Onboarding | ✅ | - | - | Complete |
| Anxiety Assessment | ✅ | - | - | Complete |
| AI Mentor Chat | ✅ | ✅ | ✅ | Complete |
| Task CRUD | - | ✅ | - | Complete |
| Priority Management | - | ✅ | - | Complete |
| Status Tracking | - | ✅ | - | Complete |
| Interactive UI | ✅ | ✅ | ✅ | Complete |
| Daily Digest | - | - | ✅ | Complete |
| Deadline Alerts | - | - | ✅ | Complete |
| Timezone Support | - | - | ✅ | Complete |
| Settings Interface | - | - | ✅ | Complete |

### Production Readiness

**Completed Features:** 
- ✅ Complete user workflow from onboarding to daily task management
- ✅ Persistent data storage with YAML
- ✅ Error handling and logging throughout
- ✅ Timezone-aware operations  
- ✅ Background notification system
- ✅ Comprehensive testing suite
- ✅ Graceful shutdown handling

**Ready for Deployment:**
The tracker is now a complete, production-ready stress management and productivity tool with:
- Trust-building onboarding experience
- Full task lifecycle management
- Intelligent notification system
- AI-powered mentoring capabilities
- Robust technical architecture

**Usage:** `/mode` → "tracker" → Complete 3-phase experience