"""
AI-агенты для управления трекером задач через LangChain
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import pytz

from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain.agents import AgentExecutor, create_openai_tools_agent

try:
    from .logger import create_logger
    from .task_database import get_database
    from .tracker import (
        TrackerUserData, TrackerTask, TaskStatus, TaskPriority,
        EveningTrackingSession, EveningSessionState, TaskReviewItem,
        DailySummary, TRACKER_STORAGE
    )
except ImportError:
    # Fallback для тестирования
    import logging
    def create_logger(name):
        return logging.getLogger(name)
    
    # Мок классы для тестирования
    class TaskStatus:
        PENDING = "pending"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        CANCELLED = "cancelled"
    
    class TaskPriority:
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        URGENT = "urgent"
    
    from pathlib import Path
    import time
    import uuid
    
    TRACKER_STORAGE = Path("tracker_data.yaml")
    
    # Мок классы для тестирования
    class TrackerTask:
        def __init__(self, title, description="", priority="medium"):
            self.id = str(uuid.uuid4())
            self.title = title
            self.description = description
            self.priority = priority
            self.status = "pending"
            self.created_at = int(time.time())
            self.updated_at = int(time.time())
        
        def to_dict(self):
            return self.__dict__
        
        @classmethod
        def from_dict(cls, data):
            task = cls(data['title'], data.get('description', ''), data.get('priority', 'medium'))
            task.__dict__.update(data)
            return task
    
    class TrackerUserData:
        def __init__(self, user_id):
            self.user_id = user_id
            self.tasks = []
    
    class EveningTrackingSession:
        def __init__(self, user_id, date_str):
            self.user_id = user_id
            self.date = date_str
        
        def to_dict(self):
            return self.__dict__
        
        @classmethod
        def from_dict(cls, data):
            session = cls(data['user_id'], data['date'])
            session.__dict__.update(data)
            return session
    
    class EveningSessionState:
        STARTING = "starting"
        TASK_REVIEW = "task_review"
        GRATITUDE = "gratitude"
        SUMMARY = "summary"
        COMPLETED = "completed"
    
    class TaskReviewItem:
        def __init__(self, task_id, task_title):
            self.task_id = task_id
            self.task_title = task_title
        
        def to_dict(self):
            return self.__dict__
        
        @classmethod
        def from_dict(cls, data):
            item = cls(data['task_id'], data['task_title'])
            item.__dict__.update(data)
            return item
    
    class DailySummary:
        def __init__(self, date_str, user_id):
            self.date = date_str
            self.user_id = user_id
    
    # Мок база данных для тестирования
    class MockDatabase:
        def __init__(self):
            self.tasks = {}
            self.users = {}
        
        def ensure_user_exists(self, user_id):
            if user_id not in self.users:
                self.users[user_id] = {'tasks': []}
            return True
        
        def create_task(self, user_id, title, description='', priority='medium', due_date=None):
            task_id = str(uuid.uuid4())
            task = {
                'id': task_id,
                'user_id': user_id,
                'title': title,
                'description': description,
                'priority': priority,
                'status': 'pending',
                'created_at': int(time.time()),
                'updated_at': int(time.time()),
                'due_date': due_date,
                'completed_at': None
            }
            if user_id not in self.tasks:
                self.tasks[user_id] = []
            self.tasks[user_id].append(task)
            return task_id
        
        def get_tasks(self, user_id, status=None):
            user_tasks = self.tasks.get(user_id, [])
            if status:
                return [t for t in user_tasks if t['status'] == status]
            return user_tasks
        
        def get_task_analytics(self, user_id):
            tasks = self.get_tasks(user_id)
            total = len(tasks)
            completed = len([t for t in tasks if t['status'] == 'completed'])
            return {
                'total_tasks': total,
                'completed_tasks': completed,
                'completion_rate': (completed/total*100) if total > 0 else 0
            }
        
        def update_task_status(self, task_id, user_id, new_status):
            user_tasks = self.tasks.get(user_id, [])
            for task in user_tasks:
                if task['id'] == task_id:
                    task['status'] = new_status
                    task['updated_at'] = int(time.time())
                    if new_status == 'completed':
                        task['completed_at'] = int(time.time())
                    return True
            return False
        
        def update_task_priority(self, task_id, user_id, new_priority):
            user_tasks = self.tasks.get(user_id, [])
            for task in user_tasks:
                if task['id'] == task_id:
                    task['priority'] = new_priority
                    task['updated_at'] = int(time.time())
                    return True
            return False
        
        def delete_task(self, task_id, user_id):
            user_tasks = self.tasks.get(user_id, [])
            for i, task in enumerate(user_tasks):
                if task['id'] == task_id:
                    del user_tasks[i]
                    return True
            return False
    
    def get_database():
        return MockDatabase()

logger = create_logger(__name__)

class BaseAgent:
    """Базовый класс для всех AI-агентов"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.llm = ChatOpenAI(
            api_key=api_key,
            model=model,
            temperature=0.7
        )
        self.name = self.__class__.__name__
        logger.info(f"Initialized {self.name}")
    
    def _load_user_data(self, user_id: int) -> Optional[TrackerUserData]:
        """Загрузка данных пользователя"""
        try:
            if TRACKER_STORAGE.exists():
                with open(TRACKER_STORAGE, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                    if str(user_id) in data:
                        user_data = TrackerUserData(user_id)
                        user_data.__dict__.update(data[str(user_id)])
                        # Конвертируем задачи из dict в TrackerTask
                        if 'tasks' in data[str(user_id)]:
                            user_data.tasks = [
                                TrackerTask.from_dict(task_data) 
                                for task_data in data[str(user_id)]['tasks']
                            ]
                        return user_data
            return None
        except Exception as e:
            logger.error(f"Error loading user data for {user_id}: {e}")
            return None
    
    def _save_user_data(self, user_data: TrackerUserData) -> bool:
        """Сохранение данных пользователя"""
        try:
            data = {}
            if TRACKER_STORAGE.exists():
                with open(TRACKER_STORAGE, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
            
            # Конвертируем задачи в dict для сериализации
            user_dict = user_data.__dict__.copy()
            if 'tasks' in user_dict:
                user_dict['tasks'] = [task.to_dict() for task in user_data.tasks]
            
            data[str(user_data.user_id)] = user_dict
            
            with open(TRACKER_STORAGE, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving user data for {user_data.user_id}: {e}")
            return False


class TaskManagerAgent(BaseAgent):
    """AI-агент для управления задачами"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        super().__init__(api_key, model)
        self.db = get_database()
        self.tools = self._create_tools()
        self.system_prompt = """
        Ты - AI-агент для управления задачами в трекере продуктивности. 
        Твоя цель - помочь пользователю эффективно организовать свои задачи.
        
        ВАЖНО: Ты ДОЛЖЕН использовать доступные инструменты для выполнения операций с задачами.
        
        Возможности:
        - Создание новых задач с приоритетами
        - Обновление статуса задач
        - Поиск и фильтрация задач
        - Предоставление аналитики по задачам
        - Помощь в планировании и приоритизации
        
        Всегда отвечай на русском языке, будь дружелюбным и поддерживающим.
        При работе с задачами предоставляй четкую и структурированную информацию.
        """
    
    def _create_tools(self) -> List[Tool]:
        """Создание инструментов для работы с задачами"""
        return [
            Tool(
                name="create_task",
                description="Создать новую задачu. Параметры: user_id, title, description, priority",
                func=self._create_task
            ),
            Tool(
                name="get_tasks",
                description="Получить список задач пользователя. Параметры: user_id, status (optional)",
                func=self._get_tasks
            ),
            Tool(
                name="update_task_status",
                description="Обновить статус задачи. Параметры: user_id, task_id, new_status",
                func=self._update_task_status
            ),
            Tool(
                name="update_task_priority",
                description="Обновить приоритет задачи. Параметры: user_id, task_id, new_priority",
                func=self._update_task_priority
            ),
            Tool(
                name="delete_task",
                description="Удалить задачу. Параметры: user_id, task_id",
                func=self._delete_task
            ),
            Tool(
                name="get_task_analytics",
                description="Получить аналитику по задачам пользователя. Параметры: user_id",
                func=self._get_task_analytics
            )
        ]
    
    def _create_task(self, params: str) -> str:
        """Создание новой задачи"""
        try:
            data = json.loads(params)
            user_id = data['user_id']
            title = data['title']
            description = data.get('description', '')
            priority = data.get('priority', 'medium')
            due_date = data.get('due_date')
            
            # Убеждаемся что пользователь существует
            self.db.ensure_user_exists(user_id)
            
            # Создаем задачу в базе
            task_id = self.db.create_task(user_id, title, description, priority, due_date)
            
            return json.dumps({
                "success": True,
                "task_id": task_id,
                "message": f"Задача '{title}' успешно создана"
            })
        except Exception as e:
            logger.error(f"Error in _create_task: {e}")
            return json.dumps({"success": False, "error": str(e)})
    
    def _get_tasks(self, params: str) -> str:
        """Получение списка задач"""
        try:
            data = json.loads(params)
            user_id = data['user_id']
            status_filter = data.get('status')
            
            # Убеждаемся что пользователь существует
            self.db.ensure_user_exists(user_id)
            
            # Получаем задачи из базы
            tasks = self.db.get_tasks(user_id, status_filter)
            
            return json.dumps({"success": True, "tasks": tasks})
        except Exception as e:
            logger.error(f"Error in _get_tasks: {e}")
            return json.dumps({"success": False, "error": str(e)})
    
    def _update_task_status(self, params: str) -> str:
        """Обновление статуса задачи"""
        try:
            data = json.loads(params)
            user_id = data['user_id']
            task_id = data['task_id']
            new_status = data['new_status']
            
            user_data = self._load_user_data(user_id)
            if not user_data:
                return json.dumps({"success": False, "error": "Пользователь не найден"})
            
            task = next((t for t in user_data.tasks if t.id == task_id), None)
            if not task:
                return json.dumps({"success": False, "error": "Задача не найдена"})
            
            task.status = new_status
            task.updated_at = int(datetime.now().timestamp())
            
            if new_status == TaskStatus.COMPLETED:
                task.completed_at = int(datetime.now().timestamp())
            
            if self._save_user_data(user_data):
                return json.dumps({
                    "success": True,
                    "message": f"Статус задачи '{task.title}' изменен на '{new_status}'"
                })
            else:
                return json.dumps({"success": False, "error": "Ошибка сохранения"})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def _update_task_priority(self, params: str) -> str:
        """Обновление приоритета задачи"""
        try:
            data = json.loads(params)
            user_id = data['user_id']
            task_id = data['task_id']
            new_priority = data['new_priority']
            
            user_data = self._load_user_data(user_id)
            if not user_data:
                return json.dumps({"success": False, "error": "Пользователь не найден"})
            
            task = next((t for t in user_data.tasks if t.id == task_id), None)
            if not task:
                return json.dumps({"success": False, "error": "Задача не найдена"})
            
            task.priority = new_priority
            task.updated_at = int(datetime.now().timestamp())
            
            if self._save_user_data(user_data):
                return json.dumps({
                    "success": True,
                    "message": f"Приоритет задачи '{task.title}' изменен на '{new_priority}'"
                })
            else:
                return json.dumps({"success": False, "error": "Ошибка сохранения"})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def _delete_task(self, params: str) -> str:
        """Удаление задачи"""
        try:
            data = json.loads(params)
            user_id = data['user_id']
            task_id = data['task_id']
            
            user_data = self._load_user_data(user_id)
            if not user_data:
                return json.dumps({"success": False, "error": "Пользователь не найден"})
            
            task = next((t for t in user_data.tasks if t.id == task_id), None)
            if not task:
                return json.dumps({"success": False, "error": "Задача не найдена"})
            
            user_data.tasks = [t for t in user_data.tasks if t.id != task_id]
            
            if self._save_user_data(user_data):
                return json.dumps({
                    "success": True,
                    "message": f"Задача '{task.title}' удалена"
                })
            else:
                return json.dumps({"success": False, "error": "Ошибка сохранения"})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def _get_task_analytics(self, params: str) -> str:
        """Получение аналитики по задачам"""
        try:
            data = json.loads(params)
            user_id = data['user_id']
            
            # Убеждаемся что пользователь существует
            self.db.ensure_user_exists(user_id)
            
            # Получаем аналитику из базы
            analytics = self.db.get_task_analytics(user_id)
            
            return json.dumps({"success": True, "analytics": analytics})
        except Exception as e:
            logger.error(f"Error in _get_task_analytics: {e}")
            return json.dumps({"success": False, "error": str(e)})
    
    async def process_request(self, user_id: int, message: str) -> str:
        """Обработка запроса к агенту управления задачами"""
        try:
            # Убеждаемся что пользователь существует
            self.db.ensure_user_exists(user_id)
            
            # Получаем контекст пользователя из базы
            tasks = self.db.get_tasks(user_id)
            active_tasks = [t for t in tasks if t['status'] in ['pending', 'in_progress']]
            
            # Простая логика обработки команд
            message_lower = message.lower()
            
            # Создание задачи
            if any(word in message_lower for word in ['создай', 'добавь', 'новая задача']):
                return await self._handle_create_task(user_id, message)
            
            # Подсчет задач
            elif any(word in message_lower for word in ['сколько', 'количество', 'задач', 'всего']):
                return await self._handle_count_tasks(user_id)
            
            # Показать задачи
            elif any(word in message_lower for word in ['покажи', 'список', 'мои задачи']):
                return await self._handle_show_tasks(user_id)
            
            # Аналитика/продуктивность
            elif any(word in message_lower for word in ['продуктивность', 'аналитика', 'статистика']):
                return await self._handle_analytics(user_id)
            
            else:
                # Общий ответ
                context = f"У вас {len(tasks)} задач, из них {len(active_tasks)} активных"
                return f"Я помогаю управлять задачами. {context}. Что вы хотите сделать?"
            
        except Exception as e:
            logger.error(f"Error in TaskManagerAgent.process_request: {e}")
            return "Извините, произошла ошибка при обработке вашего запроса."
    
    async def _handle_create_task(self, user_id: int, message: str) -> str:
        """Обработка создания задачи"""
        import re
        
        # Определяем приоритет сначала
        priority = 'medium'
        message_lower = message.lower()
        if 'высоким' in message_lower or 'высокий' in message_lower:
            priority = 'high'
        elif 'низким' in message_lower or 'низкий' in message_lower:
            priority = 'low'
        elif 'срочно' in message_lower or 'urgent' in message_lower:
            priority = 'urgent'
        
        # Ищем название задачи с помощью регулярных выражений
        patterns = [
            r'создай\s+задачу\s+["\']?([^"\']+)["\']?',
            r'добавь\s+задачу\s+["\']?([^"\']+)["\']?',
            r'новая\s+задача\s+["\']?([^"\']+)["\']?',
            r'создай\s+["\']?([^"\']+)["\']?',
            r'добавь\s+["\']?([^"\']+)["\']?'
        ]
        
        title = None
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Убираем лишние слова в конце
                title = re.sub(r'\s+(с|приоритетом|высоким|средним|низким|срочно).*$', '', title, flags=re.IGNORECASE)
                break
        
        if not title:
            # Простой fallback парсинг
            words = message.split()
            for i, word in enumerate(words):
                if word.lower() in ['создай', 'добавь']:
                    if i + 1 < len(words) and words[i + 1].lower() == 'задачу':
                        # Берем всё после "создай задачу"
                        title_words = words[i + 2:]
                    else:
                        # Берем всё после "создай"
                        title_words = words[i + 1:]
                    
                    if title_words:
                        title = ' '.join(title_words)
                        title = re.sub(r'\s+(с|приоритетом|высоким|средним|низким|срочно).*$', '', title, flags=re.IGNORECASE)
                    break
        
        if title and len(title.strip()) > 0:
            # Создаем задачу
            task_id = self.db.create_task(user_id, title.strip(), "", priority)
            return f"✅ Задача '{title.strip()}' создана с приоритетом {priority}!"
        else:
            return "Пожалуйста, укажите название задачи. Например: 'создай задачу купить молоко'"
    
    async def _handle_count_tasks(self, user_id: int) -> str:
        """Обработка подсчета задач"""
        tasks = self.db.get_tasks(user_id)
        total = len(tasks)
        
        if total == 0:
            return "У вас пока нет задач. Создайте первую задачу!"
        
        pending = len([t for t in tasks if t['status'] == 'pending'])
        in_progress = len([t for t in tasks if t['status'] == 'in_progress'])
        completed = len([t for t in tasks if t['status'] == 'completed'])
        
        response = f"📊 У вас всего {total} задач:\n"
        response += f"• Ожидают: {pending}\n"
        response += f"• В работе: {in_progress}\n"
        response += f"• Завершено: {completed}"
        
        return response
    
    async def _handle_show_tasks(self, user_id: int) -> str:
        """Обработка показа списка задач"""
        tasks = self.db.get_tasks(user_id)
        
        if not tasks:
            return "У вас пока нет задач. Создайте первую задачу!"
        
        # Группируем по статусу
        active_tasks = [t for t in tasks if t['status'] in ['pending', 'in_progress']]
        
        if not active_tasks:
            return "Все задачи завершены! 🎉"
        
        response = f"📋 Ваши активные задачи ({len(active_tasks)}):\n\n"
        
        for i, task in enumerate(active_tasks[:10], 1):  # Показываем максимум 10
            priority_emoji = {
                'urgent': '🔥',
                'high': '⚡',
                'medium': '📋',
                'low': '📝'
            }.get(task['priority'], '📋')
            
            status_emoji = {
                'pending': '⏳',
                'in_progress': '🔄'
            }.get(task['status'], '📋')
            
            response += f"{i}. {priority_emoji} {task['title']} {status_emoji}\n"
        
        if len(active_tasks) > 10:
            response += f"\n... и еще {len(active_tasks) - 10} задач"
        
        return response
    
    async def _handle_analytics(self, user_id: int) -> str:
        """Обработка аналитики"""
        analytics = self.db.get_task_analytics(user_id)
        
        if analytics['total_tasks'] == 0:
            return "Пока нет данных для аналитики. Создайте несколько задач!"
        
        response = f"📈 Ваша продуктивность:\n\n"
        response += f"• Всего задач: {analytics['total_tasks']}\n"
        response += f"• Завершено: {analytics['completed_tasks']}\n"
        response += f"• Процент завершения: {analytics['completion_rate']:.1f}%\n"
        
        if analytics['completion_rate'] >= 70:
            response += "\n🌟 Отличная продуктивность!"
        elif analytics['completion_rate'] >= 50:
            response += "\n👍 Хороший прогресс!"
        else:
            response += "\n💪 Есть куда расти!"
        
        return response


class EveningTrackerAgent(BaseAgent):
    """AI-агент для вечернего трекера"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        super().__init__(api_key, model)
        self.system_prompt = """
        Ты - AI-агент вечернего трекера для поддержки продуктивности и ментального здоровья.
        Твоя цель - провести пользователя через вечернюю рефлексию с заботой и поддержкой.
        
        Функции:
        - Проведение вечерней сессии обзора задач
        - Поддержка пользователя независимо от прогресса
        - Помощь в планировании следующих шагов
        - Практика благодарности
        - Создание дневных саммари для долгосрочной памяти
        
        Принципы:
        - Никогда не осуждай, всегда поддерживай
        - Фокус на прогрессе, а не на идеальности
        - Предлагай практические решения для препятствий
        - Создавай безопасное пространство для честности
        
        Всегда отвечай на русском языке с теплотой и эмпатией.
        """
    
    async def start_evening_session(self, user_id: int) -> Dict[str, Any]:
        """Начало вечерней сессии"""
        try:
            user_data = self._load_user_data(user_id)
            if not user_data:
                return {"success": False, "error": "Пользователь не найден"}
            
            # Получаем активные задачи для обзора
            active_tasks = [t for t in user_data.tasks if t.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]]
            
            if not active_tasks:
                return {"success": False, "error": "Нет активных задач для обзора"}
            
            # Проверяем, была ли уже сессия сегодня
            today = date.today().strftime("%Y-%m-%d")
            if user_data.current_evening_session and user_data.current_evening_session.get('date') == today:
                return {"success": False, "error": "Вечерняя сессия уже проведена сегодня"}
            
            # Создаем новую сессию
            session = EveningTrackingSession(user_id, today)
            session.task_reviews = [
                TaskReviewItem(task.id, task.title) for task in active_tasks
            ]
            
            user_data.current_evening_session = session.to_dict()
            self._save_user_data(user_data)
            
            return {
                "success": True,
                "session": session.to_dict(),
                "tasks_count": len(active_tasks),
                "message": f"Начинаем вечерний обзор {len(active_tasks)} активных задач"
            }
        except Exception as e:
            logger.error(f"Error starting evening session: {e}")
            return {"success": False, "error": str(e)}
    
    async def process_evening_message(self, user_id: int, message: str) -> str:
        """Обработка сообщения в рамках вечерней сессии"""
        try:
            user_data = self._load_user_data(user_id)
            if not user_data or not user_data.current_evening_session:
                return "Вечерняя сессия не найдена. Начните новую сессию."
            
            session = EveningTrackingSession.from_dict(user_data.current_evening_session)
            
            # Добавляем сообщение в историю сессии
            session.ai_conversation.append({"role": "user", "content": message})
            
            # Обрабатываем в зависимости от состояния сессии
            if session.state == EveningSessionState.TASK_REVIEW:
                response = await self._handle_task_review(session, message)
            elif session.state == EveningSessionState.GRATITUDE:
                response = await self._handle_gratitude(session, message)
            elif session.state == EveningSessionState.SUMMARY:
                response = await self._generate_daily_summary(session, user_data)
            else:
                response = "Неизвестное состояние сессии."
            
            # Сохраняем ответ в историю
            session.ai_conversation.append({"role": "assistant", "content": response})
            
            # Обновляем данные пользователя
            user_data.current_evening_session = session.to_dict()
            self._save_user_data(user_data)
            
            return response
        except Exception as e:
            logger.error(f"Error processing evening message: {e}")
            return "Извините, произошла ошибка при обработке сообщения."
    
    async def _handle_task_review(self, session: EveningTrackingSession, message: str) -> str:
        """Обработка обзора задач"""
        current_task = session.task_reviews[session.current_task_index]
        
        if not current_task.progress_description:
            # Первый ответ - записываем прогресс
            current_task.progress_description = message
            
            # Определяем, нужна ли помощь
            if any(word in message.lower() for word in ['ничего', 'не делал', 'не получилось', 'проблема', 'застрял']):
                current_task.needs_help = True
                return await self._generate_help_offer(current_task.task_title, message)
            else:
                # Генерируем поддерживающий ответ
                return await self._generate_task_support(current_task.task_title, message)
        
        elif current_task.needs_help and not current_task.help_provided:
            # Второй ответ - если нужна помощь
            current_task.help_provided = message
            help_response = await self._generate_task_help(current_task.task_title, message)
            current_task.ai_support = help_response
            current_task.completed = True
            
            return help_response + "\n\n" + self._get_next_task_or_gratitude(session)
        
        else:
            # Завершаем текущую задачу и переходим к следующей
            current_task.completed = True
            return self._get_next_task_or_gratitude(session)
    
    def _get_next_task_or_gratitude(self, session: EveningTrackingSession) -> str:
        """Переход к следующей задаче или к вопросу благодарности"""
        session.current_task_index += 1
        
        if session.current_task_index < len(session.task_reviews):
            # Переходим к следующей задаче
            next_task = session.task_reviews[session.current_task_index]
            return f"🎯 Задача {session.current_task_index + 1}/{len(session.task_reviews)}\n\n" \
                   f"Расскажите, что удалось сделать сегодня по задаче:\n**{next_task.task_title}**\n\n" \
                   f"Если ничего не делали - тоже не страшно, просто напишите 'ничего' или 'не делал'."
        else:
            # Переходим к вопросу благодарности
            session.state = EveningSessionState.GRATITUDE
            return "🙏 **Время благодарности**\n\n" \
                   "Теперь давайте закончим на позитивной ноте. " \
                   "За что вы благодарны себе сегодня? " \
                   "Это может быть что угодно - большое достижение или маленький шаг вперед."
    
    async def _handle_gratitude(self, session: EveningTrackingSession, message: str) -> str:
        """Обработка вопроса благодарности"""
        session.gratitude_answer = message
        session.state = EveningSessionState.SUMMARY
        
        # Генерируем ответ на благодарность
        gratitude_response = await self._generate_gratitude_response(message)
        
        return gratitude_response + "\n\n📝 Генерирую дневное саммари..."
    
    async def _generate_task_support(self, task_title: str, progress: str) -> str:
        """Генерация поддерживающего ответа на прогресс по задаче"""
        prompt = f"""
        Пользователь рассказал о прогрессе по задаче "{task_title}": "{progress}"
        
        Сгенерируй короткий (2-3 предложения) поддерживающий и воодушевляющий ответ.
        Подчеркни позитивные аспекты и прогресс, даже если он кажется небольшим.
        """
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        return response.content
    
    async def _generate_help_offer(self, task_title: str, progress: str) -> str:
        """Генерация предложения помощи"""
        prompt = f"""
        Пользователь не смог продвинуться по задаче "{task_title}": "{progress}"
        
        Сгенерируй поддерживающий ответ (2-3 предложения) и спроси, как можно помочь.
        Будь эмпатичным и не осуждающим. Подчеркни, что это нормально.
        """
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        return response.content + "\n\nКак я могу помочь вам с этой задачей?"
    
    async def _generate_task_help(self, task_title: str, help_request: str) -> str:
        """Генерация практической помощи по задаче"""
        prompt = f"""
        Пользователь просит помощь с задачей "{task_title}": "{help_request}"
        
        Предложи 2-3 конкретных практических совета или шага для решения проблемы.
        Будь конструктивным и поддерживающим.
        """
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        return response.content
    
    async def _generate_gratitude_response(self, gratitude: str) -> str:
        """Генерация ответа на благодарность"""
        prompt = f"""
        Пользователь выразил благодарность себе: "{gratitude}"
        
        Сгенерируй теплый, поддерживающий ответ (2-3 предложения).
        Подчеркни важность самопринятия и признания своих достижений.
        """
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        return response.content
    
    async def _generate_daily_summary(self, session: EveningTrackingSession, user_data: TrackerUserData) -> str:
        """Генерация дневного саммари"""
        try:
            # Подготавливаем данные для саммари
            tasks_with_progress = len([r for r in session.task_reviews if r.progress_description and 'ничего' not in r.progress_description.lower()])
            tasks_needing_help = len([r for r in session.task_reviews if r.needs_help])
            
            # Создаем саммари для долгосрочной памяти
            summary_data = {
                "date": session.date,
                "tasks_reviewed": len(session.task_reviews),
                "tasks_with_progress": tasks_with_progress,
                "tasks_needing_help": tasks_needing_help,
                "gratitude_theme": session.gratitude_answer[:100] if session.gratitude_answer else "",
                "productivity_level": "high" if tasks_with_progress > len(session.task_reviews) * 0.7 else "medium" if tasks_with_progress > 0 else "low"
            }
            
            # Генерируем текстовое саммари
            prompt = f"""
            На основе вечерней сессии создай краткое дневное саммари (3-4 предложения):
            
            Обзор задач:
            {chr(10).join([f"- {r.task_title}: {r.progress_description}" for r in session.task_reviews])}
            
            Благодарность: {session.gratitude_answer}
            
            Статистика: {tasks_with_progress} из {len(session.task_reviews)} задач с прогрессом
            
            Создай позитивное, мотивирующее саммари дня.
            """
            
            summary_response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            session.summary = summary_response.content
            summary_data["summary_text"] = summary_response.content
            
            # Добавляем саммари в долгосрочную память
            user_data.daily_summaries.append(summary_data)
            
            # Ограничиваем до 30 дней
            if len(user_data.daily_summaries) > 30:
                user_data.daily_summaries = user_data.daily_summaries[-30:]
            
            # Завершаем сессию
            session.state = EveningSessionState.COMPLETED
            session.completed_at = int(datetime.now().timestamp())
            user_data.current_evening_session = None
            
            return f"✨ **Дневное саммари**\n\n{summary_response.content}\n\n🌙 Вечерняя сессия завершена. Спокойной ночи!"
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            return "Произошла ошибка при создании дневного саммари."


class OrchestratorAgent(BaseAgent):
    """AI-агент-оркестратор для роутинга запросов"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        super().__init__(api_key, model)
        self.task_manager = TaskManagerAgent(api_key, model)
        self.evening_tracker = EveningTrackerAgent(api_key, model)
        
        self.system_prompt = """
        Ты - AI-оркестратор трекера продуктивности. Твоя задача - понять намерение пользователя 
        и направить запрос к подходящему агенту или ответить самостоятельно.
        
        Доступные агенты:
        1. TaskManagerAgent - для всех операций с задачами (создание, обновление, аналитика)
        2. EveningTrackerAgent - для вечерних сессий рефлексии
        3. Самостоятельные ответы - для общих вопросов, мотации, планирования
        
        Анализируй запрос и определи:
        - TASK_MANAGER: если запрос о создании, изменении, поиске задач, аналитике
        - EVENING_TRACKER: если запрос о вечерней рефлексии, обзоре дня
        - GENERAL: для общих вопросов, мотивации, планирования
        
        Отвечай только одним словом: TASK_MANAGER, EVENING_TRACKER или GENERAL
        """
    
    async def route_request(self, user_id: int, message: str) -> Dict[str, Any]:
        """Маршрутизация запроса к подходящему агенту"""
        try:
            message_lower = message.lower()
            
            # Определяем маршрут по ключевым словам
            # TASK_MANAGER - все операции с задачами
            task_keywords = [
                'создай', 'добавь', 'новая задача', 'задач', 'задачи', 'задачу',
                'сколько', 'количество', 'покажи', 'список', 'мои задачи',
                'продуктивность', 'аналитика', 'статистика', 'прогресс',
                'завершить', 'удалить', 'изменить', 'статус', 'приоритет'
            ]
            
            # EVENING_TRACKER - вечерние сессии
            evening_keywords = [
                'вечерний', 'трекер', 'итоги дня', 'подвести итоги',
                'рефлексия', 'благодарность', 'как прошел день'
            ]
            
            # Проверяем соответствие
            if any(keyword in message_lower for keyword in task_keywords):
                route = "TASK_MANAGER"
            elif any(keyword in message_lower for keyword in evening_keywords):
                route = "EVENING_TRACKER"
            else:
                route = "GENERAL"
            
            # Направляем к соответствующему агенту
            if route == "TASK_MANAGER":
                response = await self.task_manager.process_request(user_id, message)
                return {"agent": "task_manager", "response": response}
            
            elif route == "EVENING_TRACKER":
                # Проверяем, есть ли активная вечерняя сессия
                user_data = self._load_user_data(user_id)
                if user_data and user_data.current_evening_session:
                    response = await self.evening_tracker.process_evening_message(user_id, message)
                else:
                    # Начинаем новую сессию
                    session_result = await self.evening_tracker.start_evening_session(user_id)
                    if session_result["success"]:
                        response = session_result["message"] + "\n\nГотовы начать? Напишите 'да' или 'начинаем'."
                    else:
                        response = session_result["error"]
                
                return {"agent": "evening_tracker", "response": response}
            
            else:  # GENERAL
                response = await self._handle_general_request(user_id, message)
                return {"agent": "general", "response": response}
                
        except Exception as e:
            logger.error(f"Error in route_request: {e}")
            return {"agent": "error", "response": "Извините, произошла ошибка при обработке запроса."}
    
    async def _handle_general_request(self, user_id: int, message: str) -> str:
        """Обработка общих запросов"""
        try:
            # Получаем контекст пользователя
            user_data = self._load_user_data(user_id)
            context = ""
            
            if user_data:
                # Добавляем информацию о задачах
                active_tasks = len([t for t in user_data.tasks if t.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]])
                completed_tasks = len([t for t in user_data.tasks if t.status == TaskStatus.COMPLETED])
                context += f"У пользователя {active_tasks} активных задач, {completed_tasks} завершенных. "
                
                # Добавляем информацию из недавних дневных саммари
                if user_data.daily_summaries:
                    recent_summaries = user_data.daily_summaries[-5:]  # Последние 5 дней
                    context += "Недавняя активность: " + "; ".join([
                        f"{s['date']}: {s.get('productivity_level', 'unknown')} продуктивность"
                        for s in recent_summaries
                    ])
            
            general_prompt = f"""
            Ты - AI-ментор трекера продуктивности. Помогай пользователю с мотивацией, 
            планированием, стратегиями продуктивности и поддержкой.
            
            Контекст пользователя: {context}
            
            Принципы:
            - Будь поддерживающим и мотивирующим
            - Давай практические советы
            - Фокусируйся на прогрессе, а не на идеальности
            - Отвечай на русском языке
            
            Запрос пользователя: {message}
            """
            
            response = await self.llm.ainvoke([HumanMessage(content=general_prompt)])
            return response.content
            
        except Exception as e:
            logger.error(f"Error in _handle_general_request: {e}")
            return "Извините, не могу обработать ваш запрос прямо сейчас."


# Функция для инициализации агентов
def initialize_agents(api_key: str, model: str = "gpt-4") -> OrchestratorAgent:
    """Инициализация системы агентов"""
    try:
        orchestrator = OrchestratorAgent(api_key, model)
        logger.info("AI agents initialized successfully")
        return orchestrator
    except Exception as e:
        logger.error(f"Error initializing AI agents: {e}")
        raise