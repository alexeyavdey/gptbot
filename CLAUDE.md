# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot that integrates OpenAI's Assistant API with aiogram 3.4+. The bot supports multiple assistants, voice messages via Whisper, PDF processing with RAG, voice calls through Vapi.ai integration, and a comprehensive task tracker with AI mentor for stress management and productivity.

**Key Tracker Features (5 Complete Phases):**
- 📋 **Task Management**: Full CRUD with priorities, statuses, and filtering
- 🧠 **AI Mentor**: Context-aware guidance with 30-day long-term memory  
- 🌙 **Evening Tracker**: Daily reflection sessions with progress support and gratitude practice
- 🔔 **Smart Notifications**: Timezone-aware daily digests and deadline reminders
- 📊 **Analytics**: Automated daily summaries and productivity insights
- 🤖 **LangChain AI Agents**: Three specialized agents for intelligent request processing

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

**Test AI agents:**
```bash
python test_ai_agents.py
```

## Architecture

### Core Components

- **handlers.py**: Main aiogram router with message handlers and middleware
- **actions.py**: Enhanced with AI agents integration and message processing logic
- **ai_agents.py**: LangChain-based AI agents for intelligent request processing
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
4. Mode-specific processing in `actions.py`:
   - **Tracker mode**: AI agents via `process_tracker_message_with_agents()`
   - **Assistant mode**: OpenAI Assistant API
   - **Direct models**: GPT-4.1, o4-mini direct calls
5. **AI Agent Processing** (tracker mode):
   - OrchestratorAgent analyzes intent and routes requests
   - TaskManagerAgent handles task operations
   - EveningTrackerAgent manages reflection sessions
   - Fallback to original `tracker.py` if agents fail
6. Queue management via `message_queues.py` for rate limiting
7. Response formatting and delivery

### Key Patterns

- All user state persisted in YAML files (threads, assistants, users, tracker data)
- **AI Agent Architecture**: LangChain-based agents with tool calling and natural language processing
- **Graceful Fallback**: Automatic fallback to original tracker if AI agents fail
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

The tracker mode provides stress management and productivity features with a 6-step onboarding process, AI mentor integration, and advanced LangChain AI agents for natural language task management.

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

**Next Development Priorities (Phase 5):**

1. **Advanced Task Features**
   - Task deadline setting UI (deadlines work in background)
   - Task description editing interface
   - Task categories and tags
   - Task templates for common workflows
   - Bulk task operations (mark multiple as complete)
   - Subtasks and task hierarchies
   - Task dependencies and blocking relationships

2. **Enhanced Analytics & Insights**
   - Productivity metrics dashboard
   - Stress level tracking over time
   - Task completion patterns analysis
   - Weekly/monthly productivity reports
   - Goal achievement tracking
   - Evening tracker insights visualization
   - Burnout and overload detection

3. **Advanced AI Mentor Features**
   - Proactive check-ins based on user anxiety level and productivity patterns
   - Personalized stress management techniques based on daily summaries
   - Context-aware productivity suggestions using long-term memory
   - Automatic evening tracker scheduling suggestions
   - Mood-based task prioritization recommendations
   - Weekly/monthly reflection sessions

4. **Advanced Notification Features**
   - Custom notification schedules per user
   - Smart notification timing based on activity patterns
   - Notification snoozing and postponing
   - Integration with external calendar systems
   - Reminder escalation for overdue tasks
   - Evening tracker reminder notifications

5. **User Experience Improvements**
   - Task search and filtering by keywords
   - Quick actions with keyboard shortcuts
   - Export/import functionality for tasks
   - Multi-language support
   - Dark/light theme preferences
   - Mobile-optimized interface improvements
   - Voice input for evening tracker responses

6. **Evening Tracker Enhancements**
   - Customizable reflection questions
   - Mood tracking integration
   - Weekly gratitude summaries
   - Progress photos/attachments support
   - Team/family sharing of daily summaries
   - Integration with habit tracking

7. **Integration & Automation**
   - Calendar synchronization (Google, Outlook)
   - Task import from project management tools
   - Automated task creation from emails/messages
   - API for third-party integrations
   - Webhook support for external triggers

**Testing Current Implementation:**
- Run bot: `python -m gptbot`
- Use `/mode` → select "tracker"
- Test complete 5-phase system:
  - **Phase 1**: Complete welcome module flow
  - **Phase 2**: Create, manage, and organize tasks via natural language
  - **Phase 3**: Configure notifications and timezone
  - **Phase 4**: Run evening tracker session with AI support  
  - **Phase 5**: Natural language queries automatically routed to AI agents
- **Test AI Agents**: Use natural language like "создай задачу купить молоко", "покажи продуктивность"
- **Test Agent Routing**: Try task, evening tracker, and general productivity queries
- Verify AI mentor conversations preserve context and daily summaries
- Check data persistence in `tracker_data.yaml`
- Test notification system with manual digest
- Test evening tracker with `/вечерний` command
- Verify long-term memory in AI mentor responses
- **Fallback Testing**: Agents gracefully fall back to original tracker on errors

**Current Status**: Phase 1 (Welcome Module) + Phase 2 (Core Task Management) + Phase 3 (Notification System) + Phase 4 (Evening AI Tracker) + Phase 5 (LangChain AI Agents) fully implemented and functional ✅

## Phase 5 - LangChain AI Agents Architecture ✅

### Overview

The tracker has been refactored to use three specialized LangChain AI agents for intelligent request processing and enhanced user experience.

### AI Agents Architecture

**Three-Agent System:**
1. **TaskManagerAgent** - Handles all task-related operations
2. **EveningTrackerAgent** - Manages evening reflection sessions  
3. **OrchestratorAgent** - Routes requests to appropriate agents

**Key Features:**
- ✅ LangChain-based architecture with ChatOpenAI integration
- ✅ Tool-based function calling for task operations
- ✅ Intelligent request routing and intent recognition
- ✅ Seamless fallback to original tracker functionality
- ✅ Enhanced AI mentor capabilities with 30-day memory
- ✅ Natural language task management and analysis

### Agent Capabilities

**TaskManagerAgent:**
- Create, update, delete tasks via natural language
- Task analytics and productivity insights
- Status and priority management
- Smart task filtering and search
- Integration with existing task data structure

**EveningTrackerAgent:**  
- Guided evening reflection sessions
- Intelligent progress assessment
- Personalized support and encouragement
- Daily summary generation with long-term memory
- Gratitude practice facilitation

**OrchestratorAgent:**
- Intent recognition and request classification
- Dynamic agent routing (TASK_MANAGER/EVENING_TRACKER/GENERAL)
- Context-aware responses for general productivity questions
- Cross-agent communication and data sharing

### Technical Implementation

**Core Files:**
- `ai_agents.py` (600+ lines) - Complete LangChain agent implementation
- `actions.py` - Enhanced with agent integration and fallback handling
- `handlers.py` - Updated for agent-based message processing

**LangChain Integration:**
```python
# Agent initialization
orchestrator = initialize_agents(api_key, model)

# Request processing
result = await orchestrator.route_request(user_id, message)

# Tool-based task operations
tools = [create_task, get_tasks, update_task_status, ...]
```

**Dependencies Added:**
```
langchain>=0.3.0
langchain-openai>=0.2.0
langchain-core>=0.3.0
```

### Agent Communication Flow

1. **Message Reception** → `actions.py:process_tracker_message_with_agents()`
2. **Intent Analysis** → `OrchestratorAgent.route_request()`
3. **Agent Selection** → TaskManager/EveningTracker/General handler
4. **Tool Execution** → LangChain tools with JSON parameters
5. **Response Generation** → Context-aware AI responses
6. **Fallback Handling** → Original tracker functions if agents fail

### Natural Language Capabilities

**Task Management Examples:**
- "создай задачу 'купить молоко' с высоким приоритетом"
- "покажи все мои активные задачи"
- "измени статус задачи на выполнено"
- "какая у меня продуктивность за неделю?"

**Evening Tracker Examples:**
- "начинаем вечерний трекер"
- "хочу подвести итоги дня"
- "расскажи как прошел день"

**General Support Examples:**
- "как мне лучше планировать время?"
- "что делать если прокрастинирую?"
- "дай совет по продуктивности"

### Testing and Validation

**Test Coverage:**
- Unit tests for each agent type
- Integration tests for agent communication
- Data persistence validation
- Fallback mechanism testing
- Natural language processing accuracy

**Testing Command:**
```bash
python test_ai_agents.py
```

### Performance Benefits

**Enhanced User Experience:**
- Natural language task management
- Intelligent context understanding
- Personalized productivity advice
- Seamless agent-to-agent communication
- Robust error handling with graceful fallback

**Technical Advantages:**
- Modular agent architecture
- Tool-based function calling
- Improved maintainability
- Enhanced extensibility for future features
- Production-ready error handling

### Future Development (Phase 6+)

**Potential Enhancements:**
- Multi-language support for international users
- Voice-to-text integration with agent processing
- Advanced analytics dashboard with AI insights
- Calendar integration with intelligent scheduling
- Team collaboration features with shared agents
- Mobile app with agent-powered notifications

### Usage with New Architecture

**Current Functionality:**
- All existing tracker features remain fully functional
- Enhanced with natural language processing
- Intelligent agent routing for optimal responses
- Improved AI mentor with extended memory
- Seamless transition from UI-based to conversational interface

**Commands:**
- `/mode` → "tracker" → Access enhanced agent-powered experience
- Natural language queries automatically routed to appropriate agents
- Existing UI navigation preserved as fallback option

**Data Compatibility:**
- Full backward compatibility with existing tracker_data.yaml
- Enhanced data structures for agent memory and context
- Seamless migration of existing user data and preferences

## Phase 4 - Evening AI Tracker System ✅

### Overview

The evening AI tracker provides personalized daily reflection sessions where users review each active task, receive AI support, and end with gratitude practice. All sessions are stored as daily summaries in the AI mentor's long-term memory.

### Core Features

**Session Flow:**
1. **Task Review** - Goes through each active task (pending/in-progress)
2. **Progress Check** - "What did you accomplish today on this task?"
3. **AI Support** - Encouraging response for any progress level
4. **Help Offer** - If no progress: "How can I help with this task?"
5. **Practical Help** - AI provides actionable advice for obstacles
6. **Gratitude Question** - "What are you grateful for about yourself today?"
7. **Daily Summary** - AI generates and saves comprehensive day summary

**Smart Features:**
- **Availability Check** - Only available when there are active tasks and no session today
- **Timezone Aware** - Works with user's local date/time
- **Progress Detection** - Automatically detects if user made progress or needs help
- **Long-term Memory** - Last 30 days stored in AI mentor's context
- **Emotional Support** - Non-judgmental, encouraging responses regardless of progress

### Data Structure

**Evening Session:**
```yaml
current_evening_session:
  user_id: 123
  date: "2025-06-14"
  state: "task_review|gratitude|summary|completed"
  task_reviews:
    - task_id: "uuid"
      task_title: "Task name"
      progress_description: "What user accomplished"
      needs_help: boolean
      help_provided: "User's help request"
      ai_support: "AI encouragement"
      completed: boolean
  current_task_index: 0
  gratitude_answer: "User's gratitude response"
  summary: "AI-generated day summary"
  ai_conversation: [{role: "user|assistant", content: "..."}]
```

**Daily Summary (Long-term Memory):**
```yaml
daily_summaries:
  - date: "2025-06-14"
    tasks_reviewed: 3
    tasks_with_progress: 2
    tasks_needing_help: 1
    gratitude_theme: "Completed important presentation"
    productivity_level: "high|medium|low"
    summary_text: "Strong day with progress on most tasks..."
    key_insights: ["User struggles with task X", "Good momentum on Y"]
    mood_indicators: ["confident", "stressed about deadlines"]
```

### User Interface

**Access Points:**
- Main menu button "🌙 Вечерний трекер" (appears when available)
- Command: `/вечерний`, `/evening`, `вечерний трекер`
- Automatically hidden if no active tasks or already completed today

**Session UI:**
- Progress indicator: "(2/4)" for current task
- Clear task names and context
- Supportive messaging throughout
- Final summary with statistics

### AI Integration

**Enhanced AI Mentor Memory:**
- Daily summaries included in AI mentor context
- Last 5 days shown for pattern recognition  
- Productivity trends and recurring challenges visible
- Gratitude themes tracked over time

**AI Response Types:**
1. **Task Support** - Encouraging responses to progress reports
2. **Practical Help** - Actionable advice for stuck tasks
3. **Gratitude Response** - Warm acknowledgment of self-appreciation
4. **Daily Summary** - Comprehensive day analysis

### Technical Implementation

**Key Functions:**
- `start_evening_session()` - Initializes session with active tasks
- `process_evening_session()` - Handles all user messages during session
- `handle_task_review()` - Manages individual task discussions
- `generate_task_support()` - AI encouragement for progress
- `generate_task_help()` - AI practical advice for obstacles
- `generate_daily_summary()` - Creates long-term memory summary
- `can_start_evening_session()` - Availability logic

**Session States:**
- `starting` - Initial setup
- `task_review` - Going through tasks
- `gratitude` - Gratitude question
- `summary` - Generating final summary
- `completed` - Session finished

**Memory Management:**
- Sessions stored temporarily during active session
- Completed sessions converted to daily summaries
- Long-term memory limited to 30 days
- AI context includes recent productivity patterns

### Usage Example

```
User: /вечерний

Bot: 🌙 Вечерний AI-трекер

Давайте подведем итоги дня! Я пройдусь по каждой из ваших 3 активных задач, поддержу вас и помогу, если нужно.

📋 Задачи для обзора:
1. 🔥 Подготовить презентацию
2. 📋 Написать отчет  
3. ⚡ Встреча с клиентом

🎯 В конце поговорим о том, за что вы благодарны себе сегодня.

[Начать вечерний трекер] [Не сейчас]

User: [Начать вечерний трекер]

Bot: 🤖 Вечерний AI-трекер (1/3)

Расскажите, что удалось сделать сегодня по задаче:
**Подготовить презентацию**

Если ничего не делали - тоже не страшно, просто напишите 'ничего' или 'не делал'.

User: Сделал структуру и первые 5 слайдов

Bot: 🤖 Вечерний AI-трекер:

Отличный прогресс! Структура - это основа всей презентации, а 5 слайдов уже конкретный результат. Вы двигаетесь в правильном направлении!

[Session continues through all tasks, then gratitude, then final summary]
```

### Integration with Existing Features

**AI Mentor Enhancement:**
- Now has access to 30-day productivity history
- Can reference past challenges and patterns
- Provides more contextual advice based on trends
- Remembers what help was provided before

**Settings Integration:**
- Evening tracker can be enabled/disabled in settings
- Timezone settings affect daily date calculations  
- Notification preferences include evening tracker timing

**Task Management Integration:**
- Only active tasks (pending/in-progress) are reviewed
- Task priorities and statuses visible in session
- Progress discussions can influence task management advice

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
- `/вечерний`, `/evening`, `вечерний трекер` - Start evening AI tracker session

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

### Five-Phase Implementation Complete

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

**Phase 4: Evening AI Tracker** ✅
- Guided daily reflection sessions with AI support
- Task-by-task progress review and encouragement
- Gratitude practice and daily summaries
- 30-day long-term memory for AI mentor context
- Personalized stress management and productivity insights

**Phase 5: LangChain AI Agents** ✅
- Three specialized agents: TaskManager, EveningTracker, Orchestrator
- Natural language task management and query processing
- Intelligent request routing and intent recognition
- Tool-based function calling with JSON parameters
- Graceful fallback to original tracker functionality

### Technical Architecture

**Core Files:**
- `tracker.py` (1000+ lines) - Complete tracker implementation
- `notifications.py` (400+ lines) - Notification management system
- `ai_agents.py` (600+ lines) - LangChain AI agents implementation
- `actions.py` - Enhanced with AI agents integration
- `handlers.py` - Updated for agent-based message processing
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
  
  # Phase 4 - Evening AI Tracker
  current_evening_session: null
  daily_summaries:
    - date: "2025-06-14"
      tasks_reviewed: 3
      tasks_with_progress: 2
      productivity_level: "high"
      summary_text: "Strong day with good progress..."
      
  # Phase 5 - AI Agents
  # Agent routing and responses handled by ai_agents.py
  # All existing data structures remain compatible
```

### Feature Matrix

| Feature | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Status |
|---------|---------|---------|---------|---------|---------|---------|
| User Onboarding | ✅ | - | - | - | - | Complete |
| Anxiety Assessment | ✅ | - | - | - | - | Complete |
| AI Mentor Chat | ✅ | ✅ | ✅ | ✅ | ✅ | Complete |
| Task CRUD | - | ✅ | - | - | ✅ | Complete |
| Priority Management | - | ✅ | - | - | ✅ | Complete |
| Status Tracking | - | ✅ | - | - | ✅ | Complete |
| Interactive UI | ✅ | ✅ | ✅ | ✅ | - | Complete |
| Daily Digest | - | - | ✅ | - | - | Complete |
| Deadline Alerts | - | - | ✅ | - | - | Complete |
| Timezone Support | - | - | ✅ | ✅ | - | Complete |
| Settings Interface | - | - | ✅ | - | - | Complete |
| Evening AI Tracker | - | - | - | ✅ | ✅ | Complete |
| Long-term Memory | - | - | - | ✅ | ✅ | Complete |
| Daily Summaries | - | - | - | ✅ | ✅ | Complete |
| Progress Support | - | - | - | ✅ | ✅ | Complete |
| Gratitude Practice | - | - | - | ✅ | ✅ | Complete |
| Natural Language Processing | - | - | - | - | ✅ | Complete |
| AI Agent Routing | - | - | - | - | ✅ | Complete |
| Tool-based Function Calling | - | - | - | - | ✅ | Complete |
| Intelligent Intent Recognition | - | - | - | - | ✅ | Complete |
| Graceful Fallback System | - | - | - | - | ✅ | Complete |

### Production Readiness

**Completed Features:** 
- ✅ Complete user workflow from onboarding to AI-powered daily reflection
- ✅ Natural language task management with LangChain AI agents
- ✅ Intelligent request routing and intent recognition
- ✅ Persistent data storage with YAML (tasks, sessions, summaries, agent data)
- ✅ Comprehensive error handling and graceful fallback systems
- ✅ Tool-based function calling with JSON parameter handling
- ✅ Timezone-aware operations  
- ✅ Background notification system
- ✅ Evening AI tracker with long-term memory
- ✅ Daily summary generation and storage
- ✅ Comprehensive testing suite
- ✅ Graceful shutdown handling

**Ready for Deployment:**
The tracker is now a complete, production-ready stress management and productivity tool with:
- Trust-building onboarding experience
- **Natural language task management** via LangChain AI agents
- **Intelligent request routing** with intent recognition
- **Multi-agent architecture** for specialized functionality
- Intelligent notification system with timezone support
- AI-powered mentoring with 30-day memory
- Evening reflection and gratitude practice
- Automated daily summaries and insights
- **Graceful fallback** to original tracker if agents fail
- Robust technical architecture with comprehensive error handling

**Usage:** `/mode` → "tracker" → Complete 5-phase experience
- **Phase 1**: Welcome & Assessment
- **Phase 2**: Natural Language Task Management  
- **Phase 3**: Notifications & Timezone
- **Phase 4**: Evening AI Tracker & Long-term Memory
- **Phase 5**: LangChain AI Agents with Intelligent Routing