# Testing Guide

## Running Tests

### Core Bot Tests
```bash
python -m pytest test.py -v
```

### Tracker Function Tests  
```bash
python test_tracker_simple.py
```

### Notification System Tests
```bash
python test_notifications_simple.py
```

## Manual Testing of Tracker

### Phase 1: Welcome Module
1. Run bot: `python -m gptbot`
2. Switch to tracker mode: `/mode` → select "tracker"
3. Complete 6-step onboarding:
   - Step 1: Welcome and purpose explanation
   - Step 2: Anxiety assessment (optional)
   - Step 3: Goal selection
   - Step 4: Notification settings
   - Step 5: AI mentor introduction
   - Step 6: Completion summary

### Phase 2: Task Management
After completing welcome module:

1. **Main Menu Navigation**
   - Type `/меню` to show main menu
   - Check task statistics display

2. **Task Creation**
   - Click "➕ Новая задача" or type `/новая`
   - Enter task title (minimum 3 characters)
   - Test priority selection
   - Test task description (optional)

3. **Task Management**
   - Click "📋 Мои задачи" or type `/задачи`
   - View task list
   - Click on individual tasks for details
   - Test status changes: Start → Pause → Complete
   - Test priority changes: Low → Medium → High → Urgent

4. **Task Filtering**
   - Use "🔄 В работе" to filter in-progress tasks
   - Use "✅ Выполнены" to filter completed tasks
   - Use "📋 Все задачи" to see all tasks

5. **Task Deletion**
   - Open task detail view
   - Click "🗑️ Удалить"
   - Confirm deletion dialog

6. **AI Mentor Integration**
   - Click "🤖 AI-ментор" from main menu
   - Ask questions about stress management
   - Verify conversation history is preserved

### Phase 3: Notification System
After setting up tasks and completing welcome module:

1. **Settings Access**
   - From main menu, click "⚙️ Настройки"
   - Check timezone display and current time
   - View notification status overview

2. **Timezone Configuration**
   - Click "🌍 Часовой пояс"
   - Select your timezone from the list
   - Verify current time updates correctly
   - Check that task timestamps display in local time

3. **Notification Settings**
   - Click "🔔 Уведомления"
   - Test each notification type toggle:
     - Daily digest (morning summary)
     - Deadline reminders (24h warnings)
     - New task notifications (instant)
   - Test master enable/disable switch

4. **Manual Testing**
   - Click "📬 Тестовый дайджест"
   - Verify digest message with current tasks
   - Create new tasks and check instant notifications
   - Check notification content and formatting

5. **Background Scheduler**
   - Start bot: `python -m gptbot`
   - Look for "🚀 Бот запущен с системой уведомлений"
   - Check logs for scheduler thread startup
   - Stop bot with `Ctrl+C` and verify graceful shutdown

### Data Persistence Testing
1. Create several tasks with different priorities
2. Change some task statuses
3. Configure timezone and notifications in settings
4. Stop the bot (`Ctrl+C`)
5. Restart the bot: `python -m gptbot`
6. Check that all tasks, settings, and notification preferences are preserved

### Expected Data Structure
Check `tracker_data.yaml` after testing:
```yaml
"user_id":
  step: "completed"
  completed: true
  anxiety_level: 2.5
  goals: ["task_management", "stress_reduction"]
  timezone: "Europe/Moscow"
  notification_time: "09:00"
  notifications:
    enabled: true
    daily_digest: true
    deadline_reminders: true
    new_task_notifications: false
  tasks:
    - id: "uuid"
      title: "Task title"
      priority: "high"
      status: "in_progress"
      created_at: timestamp
      updated_at: timestamp
      due_date: timestamp (optional)
      completed_at: timestamp (optional)
```

## Known Limitations
- Import tests fail due to relative imports (tracker.py uses `.logger` import)
- This doesn't affect bot functionality when run as module
- Task descriptions editing not yet implemented
- Task deadline setting UI not yet implemented (deadlines work in background)
- Notification system requires `schedule` and `pytz` libraries