# Реализация LLM-анализа для определения задач

## Новый подход

Вместо простого текстового поиска теперь используется **специализированный AI-агент TaskSelectorAgent**, который анализирует намерения пользователя с помощью LLM и контекста разговора.

## Архитектура решения

### 1. TaskSelectorAgent - Агент анализа намерений

**Назначение**: Анализирует сообщение пользователя, список задач и историю разговора для определения:
- Какое действие хочет выполнить пользователь (delete/update/view/create)
- Какие конкретные задачи имеет в виду пользователь  
- Уровень уверенности в выборе
- Требуется ли подтверждение

**Входные данные**:
```python
{
  "user_message": "удали задачу про стратегию",
  "tasks": [
    {
      "task_id": "uuid",
      "title": "Стратегия сайта Банка",
      "description": "Подготовить презентацию",
      "status": "pending",
      "priority": "high"
    }
  ],
  "conversation_history": [
    {"role": "user", "content": "покажи задачу про презентацию"},
    {"role": "assistant", "content": "Стратегия сайта Банка"}
  ]
}
```

**Выходные данные**:
```json
{
  "action": "delete",
  "selected_tasks": [
    {
      "task_id": "uuid",
      "title": "Стратегия сайта Банка",
      "confidence": 0.95,
      "reasoning": "Найдено по ключевым словам 'стратегия'"
    }
  ],
  "requires_confirmation": true,
  "suggested_response": "Найдена задача для удаления с подтверждением"
}
```

### 2. TaskManagementAgent - Обновленный агент управления

**Интеграция с TaskSelectorAgent**:
```python
class TaskManagementAgent(BaseAgent):
    def __init__(self, api_key: str, model: str = "gpt-4.1"):
        super().__init__(api_key, model)
        self.task_selector = TaskSelectorAgent(api_key, model)  # Новый агент
        
    async def process_message(self, user_id: int, message: str, context: Dict = None):
        # 1. Получаем список всех задач пользователя
        tasks = self.db.get_tasks(user_id)
        
        # 2. Анализируем намерение через TaskSelectorAgent
        intent_analysis = await self.task_selector.analyze_user_intent(
            user_message=message,
            tasks=tasks,
            conversation_history=context.get('conversation_history', [])
        )
        
        # 3. Выполняем соответствующее действие
        action = intent_analysis.get('action')
        selected_tasks = intent_analysis.get('selected_tasks', [])
        
        if action == 'delete':
            return await self._handle_delete_action(user_id, selected_tasks, ...)
        elif action == 'view':
            return await self._handle_view_action(user_id, selected_tasks)
        # ... другие действия
```

## Алгоритм работы

### 1️⃣ **Получение контекста**
```python
# Получаем ВСЕ задачи пользователя с полной информацией
tasks = self.db.get_tasks(user_id)

# Получаем историю разговора для контекста  
conversation_history = context.get('conversation_history', [])
```

### 2️⃣ **LLM-анализ намерения**
```python
intent_analysis = await self.task_selector.analyze_user_intent(
    user_message="удали задачу про стратегию",
    tasks=tasks,  # Полный список с task_id
    conversation_history=conversation_history
)
```

**LLM получает**:
- Сообщение пользователя
- Полный список задач с ID, названиями, описаниями, статусами, приоритетами
- Контекст последних 5 сообщений разговора

**LLM анализирует**:
- Упоминания частичных названий ("стратегия" → находит задачи со словом "стратегия")
- Контекстные ссылки ("эту задачу", "её", "последнюю" → ищет в истории разговора)
- Морфологию русского языка ("стратегию" = "стратегия")
- Уровень уверенности в выборе

### 3️⃣ **Обработка результата**
```python
action = intent_analysis.get('action')           # delete/update/view/create
selected_tasks = intent_analysis.get('selected_tasks', [])  # Список найденных задач с task_id
requires_confirmation = intent_analysis.get('requires_confirmation', True)

if action == 'delete':
    if len(selected_tasks) == 1 and requires_confirmation:
        # Показываем задачу и запрашиваем подтверждение
        return format_confirmation_request(selected_tasks[0])
    elif len(selected_tasks) > 1:
        # Показываем все найденные и просим уточнить
        return format_selection_request(selected_tasks)
```

## Преимущества нового подхода

### ✅ **Умный анализ контекста**
- **Понимание ссылок**: "удали её" после обсуждения конкретной задачи
- **Морфология**: "стратегию" корректно находит "Стратегия банка"
- **Частичные совпадения**: "презентация" находит "Подготовить презентацию для Влада"

### ✅ **Уровень уверенности**
```json
{
  "selected_tasks": [
    {
      "task_id": "uuid",
      "confidence": 0.95,  // Высокая уверенность = можно предложить прямое действие
      "reasoning": "Точное совпадение по ключевым словам"
    }
  ]
}
```

### ✅ **Обработка неоднозначности**
```
Пользователь: "удали задачу про стратегию"
Найдено: 3 задачи

LLM анализ → selected_tasks: [task1, task2, task3]
Система → "Найдено 3 задачи, уточните выбор"
```

### ✅ **Контекстная память**
```
Conversation:
User: "покажи задачу про презентацию" 
Bot: "Стратегия сайта Банка — презентация для Влада"
User: "давай её удалим"  ← LLM понимает что "её" = задача из предыдущего сообщения
```

## Примеры сценариев

### Сценарий 1: Точное совпадение
```
👤 "удали задачу стратегия банка"
🧠 LLM анализ: action=delete, confidence=0.95, 1 задача найдена
🤖 "Найдена задача: Стратегия сайта Банка. Подтвердите удаление?"
👤 "да"  
🤖 "Задача удалена!"
```

### Сценарий 2: Множественные совпадения
```
👤 "удали задачу про стратегию"
🧠 LLM анализ: action=delete, 3 задачи найдены
🤖 "Найдено 3 задачи со словом 'стратегия':
     1. Стратегия сайта Банка
     2. Стратегия маркетинга  
     3. Стратегия развития
     Какую удалить?"
👤 "первую"
🧠 LLM анализ: "первую" → task_id первой задачи
🤖 "Подтвердите удаление: Стратегия сайта Банка?"
```

### Сценарий 3: Контекстная ссылка
```
👤 "покажи задачу про презентацию"
🤖 "Стратегия сайта Банка — презентация для Влада"
👤 "удали её"
🧠 LLM анализ: "её" + контекст → task_id из предыдущего сообщения  
🤖 "Подтвердите удаление: Стратегия сайта Банка?"
```

## Технические детали

### Промпт для TaskSelectorAgent
```
Ты - AI-агент для анализа намерений пользователя относительно задач.

ПРАВИЛА АНАЛИЗА:
1. Если пользователь говорит "эту задачу", "её", "последнюю" - анализируй контекст
2. Если упоминает часть названия - ищи по частичному совпадению  
3. Если несколько задач подходят - предложи уточнение
4. Всегда требуй подтверждение для удаления
5. Учитывай морфологию русского языка

ВХОДНЫЕ ДАННЫЕ:
- Сообщение пользователя  
- Список задач с ID, названием, описанием, статусом, приоритетом
- История последних сообщений для контекста

ВЫХОДНЫЕ ДАННЫЕ (JSON):
{
  "action": "delete|update|view|create",
  "selected_tasks": [...],
  "requires_confirmation": true/false,
  "suggested_response": "..."
}
```

### Обработчики действий
```python
async def _handle_delete_action(self, user_id, selected_tasks, requires_confirmation):
    if len(selected_tasks) == 1:
        if requires_confirmation:
            return format_confirmation_request(selected_tasks[0])
        else:
            return execute_deletion(selected_tasks[0])
    else:
        return format_selection_request(selected_tasks)

async def _handle_view_action(self, user_id, selected_tasks):
    if selected_tasks:
        return format_specific_tasks(selected_tasks)
    else:
        return get_all_tasks(user_id)
```

## Интеграция с существующей системой

### OrchestratorAgent
```python
class OrchestratorAgent(BaseAgent):
    def __init__(self, api_key: str, model: str = "gpt-4.1"):
        # ... другие агенты
        self.task_selector = TaskSelectorAgent(api_key, model)  # Добавляем новый агент
        
    async def route_request(self, user_id: int, message: str, user_state: Dict = None):
        # Проверка на подтверждение удаления остается
        if self._is_deletion_confirmation(message):
            task_id = self._extract_task_id_from_message(message)
            if task_id:
                return await self.task_agent.process_message(
                    user_id, message, {"task_id": task_id}
                )
        
        # Остальная логика без изменений
```

## Тестирование

### Mock-тестирование
```python
# Тест с моками для проверки логики
mock_analysis = {
    "action": "delete",
    "selected_tasks": [{"task_id": "test-id", "confidence": 0.95}],
    "requires_confirmation": True
}

with patch.object(task_agent.task_selector, 'analyze_user_intent') as mock_analyze:
    mock_analyze.return_value = mock_analysis
    result = await task_agent.process_message(user_id, "удали задачу")
    # Проверяем результат
```

### Интеграционное тестирование  
```bash
python test_task_selector_simple.py  # Mock-тесты
python test_llm_task_selection.py    # Тесты с реальным LLM (требует API ключ)
```

## Результат

✅ **Умный анализ намерений** - LLM понимает контекст и ссылки
✅ **Полный доступ к данным** - агент получает все задачи с task_id
✅ **Уровень уверенности** - система понимает насколько точно определена задача  
✅ **Обработка неоднозначности** - корректная работа с множественными совпадениями
✅ **Контекстная память** - понимание ссылок типа "эту задачу", "её"
✅ **Безопасность** - обязательное подтверждение удаления
✅ **Расширяемость** - легко добавить новые типы действий (update, create, etc.)

Этот подход реализует именно то, что вы просили: AI-агент получает список задач с task_id и историю общения, затем с помощью LLM определяет какие задачи имеет в виду пользователь для последующих операций.