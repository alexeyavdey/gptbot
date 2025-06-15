"""
Улучшенная архитектура AI-агентов с LLM роутингом
Базируется на анализе tracker.py функциональности
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
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
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
    
    from task_database import get_database
    
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

logger = create_logger(__name__)

class BaseAgent:
    """Базовый класс для всех AI-агентов"""
    
    def __init__(self, api_key: str, model: str = "gpt-4.1"):
        # Устанавливаем переменную окружения для LangChain
                
        self.llm = ChatOpenAI(
            api_key=api_key,
            model=model,
            temperature=0.3
        )
        self.db = get_database()
        self.name = self.__class__.__name__
        logger.info(f"Initialized {self.name}")
    
    async def process_message(self, user_id: int, message: str, context: Dict = None) -> str:
        """Базовый метод обработки сообщений"""
        return "Метод process_message не реализован в этом агенте."


class WelcomeAgent(BaseAgent):
    """AI-агент для приветственного модуля (6-step onboarding)"""
    
    def __init__(self, api_key: str, model: str = "gpt-4.1"):
        super().__init__(api_key, model)
        self.system_prompt = """
        Ты - AI-агент приветственного модуля трекера продуктивности.
        Твоя задача - провести пользователя через 6-шаговый процесс онбординга:

        1. Приветствие и объяснение назначения
        2. Оценка уровня тревожности (5 вопросов по шкале 1-5)
        3. Выбор целей (управление задачами, снижение стресса, продуктивность, организация времени)
        4. Настройка уведомлений (ежедневный дайджест, напоминания о дедлайнах)
        5. Знакомство с AI-ментором
        6. Завершение и переход к основному функционалу

        Будь эмпатичным, поддерживающим и сосредоточенным на снижении тревожности.
        Всегда отвечай на русском языке.
        """
    
    async def process_welcome_step(self, user_id: int, current_step: str, message: str) -> Dict[str, Any]:
        """Обработка шага приветственного модуля"""
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt + f"\n\nТекущий шаг: {current_step}"),
                ("human", "{message}")
            ])
            
            chain = prompt | self.llm | StrOutputParser()
            response = await chain.ainvoke({"message": message})
            
            return {
                "success": True,
                "response": response,
                "next_step": self._determine_next_step(current_step, message)
            }
        except Exception as e:
            logger.error(f"Error in WelcomeAgent: {e}")
            return {"success": False, "error": str(e)}
    
    def _determine_next_step(self, current_step: str, message: str) -> str:
        """Определение следующего шага на основе текущего состояния"""
        # Логика определения следующего шага
        step_mapping = {
            "greeting": "anxiety_intro",
            "anxiety_intro": "anxiety_survey", 
            "anxiety_survey": "goals",
            "goals": "notifications",
            "notifications": "ai_mentor",
            "ai_mentor": "completion"
        }
        return step_mapping.get(current_step, "completed")


class TaskManagementAgent(BaseAgent):
    """AI-агент для управления задачами (Phase 2 функциональность)"""
    
    def __init__(self, api_key: str, model: str = "gpt-4.1"):
        super().__init__(api_key, model)
        self.tools = self._create_tools()
        self.task_selector = TaskSelectorAgent(api_key, model)  # Новый агент для анализа намерений
        self.system_prompt = """
        Ты - AI-агент для управления задачами в трекере продуктивности.
        
        Твои возможности:
        - Создание, редактирование и удаление задач
        - Управление приоритетами и статусами задач
        - Фильтрация задач по различным критериям
        - Предоставление аналитики и статистики
        - Помощь в планировании и приоритизации
        
        ВАЖНО: ВСЕГДА используй доступные инструменты для операций с задачами:
        - Для получения количества/списка задач: используй get_tasks
        - Для создания задач: используй create_task
        - Для аналитики и статистики: используй get_analytics
        - Для обновления задач: используй update_task
        - Для удаления задач: используй delete_task
        
        Параметры для инструментов передавай в JSON формате с обязательным полем user_id.
        
        Примеры:
        - Для подсчета задач: get_tasks с параметрами {{"user_id": 123}}
        - Для аналитики: get_analytics с параметрами {{"user_id": 123}}
        - Для создания: create_task с параметрами {{"user_id": 123, "title": "название", "priority": "medium"}}
        - Для поиска задач для удаления: delete_task с параметрами {{"user_id": 123, "search_text": "стратегия"}}
        - Для подтверждения удаления: delete_task с параметрами {{"user_id": 123, "task_id": "uuid"}}
        
        АЛГОРИТМ УДАЛЕНИЯ ЗАДАЧ:
        1. Когда пользователь просит удалить задачу, используй delete_task с search_text
        2. Система покажет найденные задачи и попросит подтверждение
        3. Если пользователь подтверждает (говорит "да", "подтверждаю"), используй delete_task с task_id
        4. НИКОГДА не удаляй задачи без явного подтверждения пользователя
        
        При обработке подтверждений удаления:
        - Если в контексте есть task_id для удаления, сразу удаляй задачу
        - Всегда проверяй наличие task_id в дополнительном контексте
        
        Всегда отвечай на русском языке, будь дружелюбным и конструктивным.
        """
    
    def _create_tools(self) -> List[Tool]:
        """Создание инструментов для работы с задачами"""
        return [
            Tool(
                name="create_task",
                description="Создать новую задачу. Параметры: user_id, title, description, priority",
                func=self._create_task
            ),
            Tool(
                name="get_tasks",
                description="Получить список задач. Параметры: user_id, status (optional)",
                func=self._get_tasks
            ),
            Tool(
                name="update_task",
                description="Обновить задачу. Параметры: user_id, task_id, field, value",
                func=self._update_task
            ),
            Tool(
                name="delete_task",
                description="Удалить задачу. Параметры: user_id, task_id (для прямого удаления) ИЛИ user_id, search_text (для поиска похожих задач)",
                func=self._delete_task
            ),
            Tool(
                name="get_analytics",
                description="Получить аналитику по задачам. Параметры: user_id",
                func=self._get_analytics
            ),
            Tool(
                name="filter_tasks",
                description="Фильтровать задачи. Параметры: user_id, priority, status",
                func=self._filter_tasks
            )
        ]
    
    async def process_message(self, user_id: int, message: str, context: Dict = None) -> str:
        """Обработка сообщений для управления задач с использованием TaskSelectorAgent"""
        try:
            # Если в контексте есть task_id для удаления, выполняем прямое удаление
            if context and context.get('task_id'):
                delete_params = json.dumps({
                    "user_id": user_id,
                    "task_id": context['task_id']
                })
                return self._delete_task(delete_params)
            
            # Получаем все задачи пользователя для анализа
            tasks = self.db.get_tasks(user_id)
            
            # Получаем историю разговора из контекста (если есть)
            conversation_history = context.get('conversation_history', []) if context else []
            
            # Используем TaskSelectorAgent для анализа намерения
            intent_analysis = await self.task_selector.analyze_user_intent(
                user_message=message,
                tasks=tasks,
                conversation_history=conversation_history
            )
            
            logger.info(f"Intent analysis: {intent_analysis}")
            
            # Обрабатываем результат анализа
            action = intent_analysis.get('action', 'unknown')
            selected_tasks = intent_analysis.get('selected_tasks', [])
            requires_confirmation = intent_analysis.get('requires_confirmation', True)
            suggested_response = intent_analysis.get('suggested_response', '')
            
            if action == 'delete':
                return await self._handle_delete_action(user_id, selected_tasks, requires_confirmation, suggested_response)
            elif action == 'update':
                return await self._handle_update_action(user_id, selected_tasks, message)
            elif action == 'view':
                return await self._handle_view_action(user_id, selected_tasks)
            elif action == 'create':
                # Используем обычную обработку через LangChain для создания
                return await self._handle_create_action(user_id, message)
            else:
                # Для неопознанных запросов используем обычную обработку
                return await self._handle_general_action(user_id, message)
            
        except Exception as e:
            logger.error(f"Error in TaskManagementAgent.process_message: {e}")
            return f"Ошибка при обработке запроса: {str(e)}"
    
    def _create_task(self, params: str) -> str:
        """Создание новой задачи"""
        try:
            data = json.loads(params)
            user_id = data['user_id']
            title = data['title']
            description = data.get('description', '')
            priority = data.get('priority', 'medium')
            due_date = data.get('due_date')
            
            self.db.ensure_user_exists(user_id)
            task_id = self.db.create_task(user_id, title, description, priority, due_date)
            
            priority_emoji = {'urgent': '🔥', 'high': '⚡', 'medium': '📋', 'low': '📝'}.get(priority, '📋')
            return f"✅ Задача '{title}' создана с приоритетом {priority} {priority_emoji}!"
        except Exception as e:
            return f"Ошибка создания задачи: {str(e)}"
    
    def _get_tasks(self, params: str) -> str:
        """Получение списка задач"""
        try:
            data = json.loads(params)
            user_id = data['user_id']
            status = data.get('status')
            
            self.db.ensure_user_exists(user_id)
            tasks = self.db.get_tasks(user_id, status)
            
            if not tasks:
                return "У пользователя пока нет задач."
            
            # Форматируем красивый ответ
            if status:
                response = f"Задачи со статусом '{status}' ({len(tasks)}):\n"
            else:
                response = f"Все задачи пользователя ({len(tasks)}):\n"
            
            for i, task in enumerate(tasks[:10], 1):
                priority_emoji = {'urgent': '🔥', 'high': '⚡', 'medium': '📋', 'low': '📝'}.get(task['priority'], '📋')
                status_emoji = {'pending': '⏳', 'in_progress': '🔄', 'completed': '✅', 'cancelled': '❌'}.get(task['status'], '📋')
                response += f"{i}. {priority_emoji} {task['title']} {status_emoji}\n"
            
            if len(tasks) > 10:
                response += f"... и еще {len(tasks) - 10} задач"
            
            return response
        except Exception as e:
            return f"Ошибка получения задач: {str(e)}"
    
    def _update_task(self, params: str) -> str:
        """Обновление задачи"""
        try:
            data = json.loads(params)
            user_id = data['user_id']
            task_id = data['task_id']
            field = data['field']
            value = data['value']
            
            if field == 'status':
                success = self.db.update_task_status(task_id, user_id, value)
            elif field == 'priority':
                success = self.db.update_task_priority(task_id, user_id, value)
            else:
                success = False
            
            return json.dumps({
                "success": success,
                "message": f"Поле {field} обновлено" if success else "Ошибка обновления"
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def _delete_task(self, params: str) -> str:
        """Интерактивное удаление задачи с подтверждением"""
        try:
            data = json.loads(params)
            user_id = data['user_id']
            
            # Если передан task_id, это прямое удаление (для подтверждения)
            if 'task_id' in data:
                task_id = data['task_id']
                
                # Получаем информацию о задаче перед удалением
                tasks = self.db.get_tasks(user_id)
                task_to_delete = None
                for task in tasks:
                    if task['id'] == task_id:
                        task_to_delete = task
                        break
                
                if not task_to_delete:
                    return "❌ Задача не найдена или уже удалена."
                
                # Удаляем задачу
                success = self.db.delete_task(task_id, user_id)
                
                if success:
                    return f"✅ Задача '{task_to_delete['title']}' успешно удалена!"
                else:
                    return f"❌ Не удалось удалить задачу '{task_to_delete['title']}'. Попробуйте еще раз."
            
            # Если передан search_text, ищем похожие задачи
            elif 'search_text' in data:
                search_text = data['search_text'].lower()
                
                # Получаем все задачи пользователя
                tasks = self.db.get_tasks(user_id)
                
                if not tasks:
                    return "📝 У вас пока нет задач для удаления."
                
                # Ищем задачи по поисковому тексту (частичное совпадение и по словам)
                matching_tasks = []
                search_words = search_text.split()
                
                for task in tasks:
                    task_text = (task['title'] + ' ' + task.get('description', '')).lower()
                    
                    # Прямое частичное совпадение
                    if search_text in task_text:
                        matching_tasks.append(task)
                        continue
                    
                    # Поиск по отдельным словам (все слова должны быть найдены)
                    if len(search_words) > 1:
                        words_found = sum(1 for word in search_words if word in task_text)
                        if words_found >= len(search_words):
                            matching_tasks.append(task)
                            continue
                    
                    # Поиск с учетом морфологии (простая нормализация)
                    normalized_search = self._normalize_text(search_text)
                    normalized_task = self._normalize_text(task_text)
                    
                    if normalized_search in normalized_task:
                        matching_tasks.append(task)
                
                if len(matching_tasks) == 0:
                    return f"🔍 Не найдено задач, содержащих '{data['search_text']}'.\n\n📋 Ваши текущие задачи:\n" + \
                           "\n".join([f"• {task['title']}" for task in tasks[:5]]) + \
                           (f"\n... и еще {len(tasks) - 5}" if len(tasks) > 5 else "")
                
                elif len(matching_tasks) == 1:
                    # Найдена одна задача - запрашиваем подтверждение
                    task = matching_tasks[0]
                    priority_emoji = {'urgent': '🔥', 'high': '⚡', 'medium': '📋', 'low': '📝'}.get(task['priority'], '📋')
                    status_emoji = {'pending': '⏳', 'in_progress': '🔄', 'completed': '✅', 'cancelled': '❌'}.get(task['status'], '⏳')
                    
                    return f"🎯 Найдена задача для удаления:\n\n" + \
                           f"{priority_emoji} **{task['title']}**\n" + \
                           f"Статус: {status_emoji} {task['status']}\n" + \
                           f"Приоритет: {task['priority']}\n" + \
                           (f"Описание: {task['description']}\n" if task.get('description') else "") + \
                           f"\n❓ **Вы действительно хотите удалить эту задачу?**\n" + \
                           f"Напишите 'да' или 'подтверждаю удаление' для подтверждения.\n" + \
                           f"ID задачи: `{task['id']}`"
                
                else:
                    # Найдено несколько задач - показываем список для выбора
                    task_list = []
                    for i, task in enumerate(matching_tasks[:10], 1):  # Показываем максимум 10 задач
                        priority_emoji = {'urgent': '🔥', 'high': '⚡', 'medium': '📋', 'low': '📝'}.get(task['priority'], '📋')
                        status_emoji = {'pending': '⏳', 'in_progress': '🔄', 'completed': '✅', 'cancelled': '❌'}.get(task['status'], '⏳')
                        task_list.append(f"{i}. {priority_emoji} {status_emoji} **{task['title']}**")
                    
                    return f"🔍 Найдено {len(matching_tasks)} задач по запросу '{data['search_text']}':\n\n" + \
                           "\n".join(task_list) + \
                           (f"\n... и еще {len(matching_tasks) - 10}" if len(matching_tasks) > 10 else "") + \
                           f"\n\n❓ **Какую задачу хотите удалить?**\n" + \
                           f"Назовите полное название задачи или более точный поисковый запрос."
            
            else:
                return "❌ Не указан search_text для поиска задач или task_id для прямого удаления.\n\n" + \
                       "💡 Примеры использования:\n" + \
                       "• 'удали задачу про презентацию'\n" + \
                       "• 'удали задачу стратегия'\n" + \
                       "• 'удали последнюю задачу'"
                
        except Exception as e:
            return f"❌ Ошибка при удалении задачи: {str(e)}"
    
    def _normalize_text(self, text: str) -> str:
        """Простая нормализация текста для лучшего поиска"""
        # Словарь простых замен для русского языка
        replacements = {
            'стратегию': 'стратегия',
            'стратегии': 'стратегия',
            'стратегией': 'стратегия',
            'задачу': 'задача',
            'задачи': 'задача',
            'задачей': 'задача',
            'презентацию': 'презентация',
            'презентации': 'презентация',
            'презентацией': 'презентация',
            'банка': 'банк',
            'банку': 'банк',
            'банком': 'банк'
        }
        
        normalized = text
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        return normalized
    
    async def _handle_delete_action(self, user_id: int, selected_tasks: List[Dict], 
                                   requires_confirmation: bool, suggested_response: str) -> str:
        """Обработка действия удаления задач"""
        if not selected_tasks:
            return suggested_response or "Не удалось определить какую задачу удалить."
        
        if len(selected_tasks) == 1:
            task = selected_tasks[0]
            if requires_confirmation:
                # Запрашиваем подтверждение
                priority_emoji = {'urgent': '🔥', 'high': '⚡', 'medium': '📋', 'low': '📝'}.get(task.get('priority', 'medium'), '📋')
                status_emoji = {'pending': '⏳', 'in_progress': '🔄', 'completed': '✅', 'cancelled': '❌'}.get(task.get('status', 'pending'), '⏳')
                
                confirmation_text = f"🎯 Найдена задача для удаления:\n\n" + \
                                  f"{priority_emoji} **{task['title']}**\n" + \
                                  f"Статус: {status_emoji} {task.get('status', 'pending')}\n" + \
                                  f"Приоритет: {task.get('priority', 'medium')}\n"
                
                if task.get('description'):
                    confirmation_text += f"Описание: {task['description']}\n"
                
                confirmation_text += f"\n❓ **Вы действительно хотите удалить эту задачу?**\n" + \
                                   f"Напишите 'да' или 'подтверждаю удаление' для подтверждения.\n" + \
                                   f"ID задачи: `{task['task_id']}`"
                
                return confirmation_text
            else:
                # Прямое удаление (если уверенность высокая)
                delete_params = json.dumps({
                    "user_id": user_id,
                    "task_id": task['task_id']
                })
                return self._delete_task(delete_params)
        else:
            # Несколько задач - показываем список для выбора
            task_list = []
            for i, task in enumerate(selected_tasks[:10], 1):
                priority_emoji = {'urgent': '🔥', 'high': '⚡', 'medium': '📋', 'low': '📝'}.get(task.get('priority', 'medium'), '📋')
                status_emoji = {'pending': '⏳', 'in_progress': '🔄', 'completed': '✅', 'cancelled': '❌'}.get(task.get('status', 'pending'), '⏳')
                task_list.append(f"{i}. {priority_emoji} {status_emoji} **{task['title']}**")
            
            return f"🔍 Найдено {len(selected_tasks)} задач:\n\n" + \
                   "\n".join(task_list) + \
                   f"\n\n❓ **Какую задачу хотите удалить?**\n" + \
                   f"Назовите полное название задачи или более точный поисковый запрос."
    
    async def _handle_update_action(self, user_id: int, selected_tasks: List[Dict], message: str) -> str:
        """Обработка действия обновления задач"""
        # Пока используем базовую реализацию через LangChain
        return await self._handle_general_action(user_id, message)
    
    async def _handle_view_action(self, user_id: int, selected_tasks: List[Dict]) -> str:
        """Обработка действия просмотра задач"""
        if not selected_tasks:
            get_params = json.dumps({"user_id": user_id})
            return self._get_tasks(get_params)
        
        # Показываем конкретные выбранные задачи
        result = "📋 Выбранные задачи:\n\n"
        for task in selected_tasks:
            priority_emoji = {'urgent': '🔥', 'high': '⚡', 'medium': '📋', 'low': '📝'}.get(task.get('priority', 'medium'), '📋')
            status_emoji = {'pending': '⏳', 'in_progress': '🔄', 'completed': '✅', 'cancelled': '❌'}.get(task.get('status', 'pending'), '⏳')
            
            result += f"{priority_emoji} {status_emoji} **{task['title']}**\n"
            if task.get('description'):
                result += f"   Описание: {task['description']}\n"
            result += f"   Статус: {task.get('status', 'pending')} | Приоритет: {task.get('priority', 'medium')}\n\n"
        
        return result
    
    async def _handle_create_action(self, user_id: int, message: str) -> str:
        """Обработка действия создания задач"""
        return await self._handle_general_action(user_id, message)
    
    async def _handle_general_action(self, user_id: int, message: str) -> str:
        """Обработка общих запросов через LangChain"""
        try:
            # Создаем промпт с правильными переменными для агента
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                ("placeholder", "{agent_scratchpad}"),
                ("human", "{input}")
            ])
            
            # Создаем агента с инструментами
            agent = create_openai_tools_agent(self.llm, self.tools, prompt)
            agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=False)
            
            # Выполняем запрос
            result = await agent_executor.ainvoke({"input": message})
            return result.get('output', 'Произошла ошибка при обработке запроса.')
        except Exception as e:
            logger.error(f"Error in _handle_general_action: {e}")
            return f"Ошибка при обработке запроса: {str(e)}"
    
    def _get_analytics(self, params) -> str:
        """Получение аналитики"""
        try:
            # Обрабатываем разные форматы входных данных
            if isinstance(params, str):
                try:
                    data = json.loads(params)
                    user_id = data['user_id']
                except:
                    # Если это просто строка с числом
                    user_id = int(params)
            elif isinstance(params, int):
                user_id = params
            else:
                raise ValueError(f"Unexpected params type: {type(params)}")
            
            self.db.ensure_user_exists(user_id)
            analytics = self.db.get_task_analytics(user_id)
            
            if analytics['total_tasks'] == 0:
                return "Пока нет данных для аналитики. Создайте несколько задач!"
            
            response = f"📈 Ваша продуктивность:\n\n"
            response += f"• Всего задач: {analytics['total_tasks']}\n"
            response += f"• Завершено: {analytics['completed_tasks']}\n"
            response += f"• В работе: {analytics['in_progress_tasks']}\n"
            response += f"• Ожидают: {analytics['pending_tasks']}\n"
            response += f"• Процент завершения: {analytics['completion_rate']:.1f}%\n"
            
            if analytics['completion_rate'] >= 70:
                response += "\n🌟 Отличная продуктивность!"
            elif analytics['completion_rate'] >= 50:
                response += "\n👍 Хороший прогресс!"
            else:
                response += "\n💪 Есть куда расти!"
            
            return response
        except Exception as e:
            return f"Ошибка получения аналитики: {str(e)}"
    
    def _filter_tasks(self, params: str) -> str:
        """Фильтрация задач"""
        try:
            data = json.loads(params)
            user_id = data['user_id']
            priority = data.get('priority')
            status = data.get('status')
            
            self.db.ensure_user_exists(user_id)
            tasks = self.db.get_tasks(user_id, status)
            
            if priority:
                tasks = [t for t in tasks if t['priority'] == priority]
            
            return json.dumps({"success": True, "tasks": tasks})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    async def process_task_request(self, user_id: int, message: str) -> str:
        """Обработка запроса по управлению задачами"""
        try:
            logger.info(f"TaskManagementAgent processing: '{message}' for user {user_id}")
            
            # Создаем агента с tools
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt + f"\n\nТекущий пользователь ID: {user_id}. Используй этот ID во всех вызовах инструментов."),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}")
            ])
            
            agent = create_openai_tools_agent(self.llm, self.tools, prompt)
            agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)
            
            result = await agent_executor.ainvoke({"input": message})
            logger.info(f"LangChain agent result: {result}")
            return result.get("output", "Не удалось обработать запрос")
            
        except Exception as e:
            logger.error(f"Error in TaskManagementAgent: {e}")
            import traceback
            logger.error(f"TaskManagementAgent traceback: {traceback.format_exc()}")
            return "Извините, произошла ошибка при обработке запроса по задачам."


class NotificationAgent(BaseAgent):
    """AI-агент для управления уведомлениями (Phase 3 функциональность)"""
    
    def __init__(self, api_key: str, model: str = "gpt-4.1"):
        super().__init__(api_key, model)
        self.system_prompt = """
        Ты - AI-агент для управления уведомлениями в трекере продуктивности.
        
        Твои возможности:
        - Настройка типов уведомлений (ежедневный дайджест, напоминания о дедлайнах)
        - Управление временем уведомлений
        - Настройка часовых поясов
        - Генерация и отправка уведомлений
        
        Всегда отвечай на русском языке и помогай пользователю настроить удобную систему уведомлений.
        """
    
    async def process_notification_request(self, user_id: int, message: str) -> str:
        """Обработка запросов по уведомлениям"""
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                ("human", f"Пользователь {user_id}: {message}")
            ])
            
            chain = prompt | self.llm | StrOutputParser()
            response = await chain.ainvoke({"message": message})
            
            return response
        except Exception as e:
            logger.error(f"Error in NotificationAgent: {e}")
            return "Извините, произошла ошибка при обработке запроса по уведомлениям."


class EveningTrackerAgent(BaseAgent):
    """AI-агент для вечернего трекера (Phase 4 функциональность)"""
    
    def __init__(self, api_key: str, model: str = "gpt-4.1"):
        super().__init__(api_key, model)
        self.task_selector = TaskSelectorAgent(api_key, model)  # Добавляем умный селектор задач
        self.system_prompt = """
        Ты - AI-агент вечернего трекера для поддержки продуктивности и ментального здоровья.
        
        Твои задачи:
        - Проведение вечерних сессий рефлексии
        - Обзор прогресса по задачам за день
        - Предоставление поддержки и мотивации
        - Практика благодарности
        - Создание дневных саммари для долгосрочной памяти
        
        Принципы:
        - Никогда не осуждай, всегда поддерживай
        - Фокус на прогрессе, а не на идеальности
        - Создавай безопасное пространство для честности
        - Предлагай практические решения
        
        Всегда отвечай на русском языке с теплотой и эмпатией.
        """
    
    async def start_evening_session(self, user_id: int) -> Dict[str, Any]:
        """Начало вечерней сессии"""
        try:
            # Получаем активные задачи
            tasks = self.db.get_tasks(user_id, 'pending') + self.db.get_tasks(user_id, 'in_progress')
            
            if not tasks:
                return {
                    "success": False,
                    "error": "Нет активных задач для обзора"
                }
            
            # Проверяем была ли сессия сегодня
            today = date.today().strftime("%Y-%m-%d")
            
            return {
                "success": True,
                "tasks_count": len(tasks),
                "message": f"Начинаем вечерний обзор {len(tasks)} активных задач"
            }
        except Exception as e:
            logger.error(f"Error starting evening session: {e}")
            return {"success": False, "error": str(e)}
    
    async def process_evening_message(self, user_id: int, message: str, session_state: str = "starting") -> str:
        """Обработка сообщения в вечерней сессии"""
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt + f"\n\nСостояние сессии: {session_state}"),
                ("human", f"Пользователь {user_id}: {message}")
            ])
            
            chain = prompt | self.llm | StrOutputParser()
            response = await chain.ainvoke({"message": message})
            
            return response
        except Exception as e:
            logger.error(f"Error in evening tracker: {e}")
            return "Извините, произошла ошибка в вечерней сессии."
    
    async def analyze_task_context(self, user_id: int, message: str, conversation_history: List[Dict] = None) -> Dict:
        """Анализ упоминания задач в контексте вечернего трекера"""
        try:
            # Получаем все задачи пользователя
            tasks = self.db.get_tasks(user_id)
            
            if not tasks:
                return {
                    "action": "no_tasks",
                    "selected_tasks": [],
                    "suggested_response": "У вас пока нет задач для обсуждения."
                }
            
            # Используем TaskSelectorAgent для анализа
            analysis = await self.task_selector.analyze_user_intent(
                user_message=message,
                tasks=tasks,
                conversation_history=conversation_history
            )
            
            # Адаптируем анализ для вечернего контекста
            if analysis.get('action') in ['view', 'delete', 'update']:
                # В вечернем трекере основной фокус на обсуждении прогресса
                analysis['action'] = 'discuss_progress'
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing task context in evening tracker: {e}")
            return {
                "action": "error",
                "selected_tasks": [],
                "suggested_response": "Не удалось проанализировать упоминание задачи."
            }
    
    async def discuss_task_progress(self, user_id: int, message: str, selected_tasks: List[Dict], 
                                   conversation_history: List[Dict] = None) -> str:
        """Обсуждение прогресса по конкретным задачам"""
        try:
            if not selected_tasks:
                return "Не удалось определить о какой задаче идет речь. Можете уточнить?"
            
            if len(selected_tasks) == 1:
                # Обсуждаем конкретную задачу
                task = selected_tasks[0]
                
                context_info = ""
                if conversation_history:
                    context_info = "\n".join([
                        f"{msg.get('role', 'user')}: {msg.get('content', '')}" 
                        for msg in conversation_history[-3:]  # Последние 3 сообщения
                    ])
                
                discussion_prompt = f"""
                Пользователь обсуждает прогресс по задаче в рамках вечернего трекера.
                
                ЗАДАЧА:
                Название: {task['title']}
                Описание: {task.get('description', 'Не указано')}
                Статус: {task.get('status', 'pending')}
                Приоритет: {task.get('priority', 'medium')}
                
                СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ: {message}
                
                КОНТЕКСТ РАЗГОВОРА:
                {context_info}
                
                Ответь как заботливый AI-ментор, который помогает подвести итоги дня.
                Фокусируйся на:
                - Поддержке и поощрении любого прогресса
                - Понимании трудностей и препятствий
                - Практических советах для завтрашнего дня
                - Эмоциональной поддержке
                
                Будь теплым, понимающим и конструктивным.
                """
                
                prompt = ChatPromptTemplate.from_messages([
                    ("system", self.system_prompt),
                    ("human", discussion_prompt)
                ])
                
                chain = prompt | self.llm | StrOutputParser()
                response = await chain.ainvoke({})
                
                # Добавляем информацию о задаче в начало
                priority_emoji = {'urgent': '🔥', 'high': '⚡', 'medium': '📋', 'low': '📝'}.get(task.get('priority', 'medium'), '📋')
                status_emoji = {'pending': '⏳', 'in_progress': '🔄', 'completed': '✅', 'cancelled': '❌'}.get(task.get('status', 'pending'), '⏳')
                
                return f"📋 Обсуждаем: {priority_emoji} **{task['title']}** {status_emoji}\n\n{response}"
                
            else:
                # Несколько задач - просим уточнить
                task_list = []
                for i, task in enumerate(selected_tasks[:5], 1):
                    priority_emoji = {'urgent': '🔥', 'high': '⚡', 'medium': '📋', 'low': '📝'}.get(task.get('priority', 'medium'), '📋')
                    task_list.append(f"{i}. {priority_emoji} {task['title']}")
                
                return f"🤔 Вы упоминаете несколько задач:\n\n" + \
                       "\n".join(task_list) + \
                       f"\n\nО какой именно задаче хотите поговорить?"
                       
        except Exception as e:
            logger.error(f"Error discussing task progress: {e}")
            return "Извините, произошла ошибка при обсуждении задачи."


class TaskSelectorAgent(BaseAgent):
    """AI-агент для определения задач из контекста пользователя"""
    
    def __init__(self, api_key: str, model: str = "gpt-4.1"):
        super().__init__(api_key, model)
        self.system_prompt = """
        Ты - AI-агент для анализа намерений пользователя относительно задач.

        Твоя задача: на основе сообщения пользователя и списка его задач определить:
        1. Какие задачи имеет в виду пользователь
        2. Какое действие он хочет выполнить (удалить, изменить, просмотреть)
        3. Уровень уверенности в выборе

        ВХОДНЫЕ ДАННЫЕ:
        - Сообщение пользователя
        - Список задач с ID, названием, описанием, статусом, приоритетом
        - История последних сообщений для контекста

        ВЫХОДНЫЕ ДАННЫЕ (JSON):
        {{
          "action": "delete|update|view|create",
          "selected_tasks": [
            {{
              "task_id": "uuid",
              "title": "название задачи", 
              "confidence": 0.95,
              "reasoning": "почему выбрана эта задача"
            }}
          ],
          "requires_confirmation": true/false,
          "suggested_response": "что ответить пользователю"
        }}

        ПРАВИЛА АНАЛИЗА:
        1. Если пользователь говорит "эту задачу", "её", "последнюю" - анализируй контекст
        2. Если упоминает часть названия - ищи по частичному совпадению
        3. Если несколько задач подходят - предложи уточнение
        4. Всегда требуй подтверждение для удаления
        5. Учитывай морфологию русского языка
        6. ВАЖНО: Если пользователь говорит "да", "подтверждаю", "согласен" - это подтверждение действия
        7. При подтверждении попытайся найти задачу из недавнего контекста разговора

        ПРИМЕРЫ:
        Пользователь: "удали задачу про стратегию"
        Задачи: ["Стратегия банка", "Стратегия маркетинга", "Купить молоко"]
        → Найти задачи со словом "стратегия", запросить уточнение

        Пользователь: "удали её" (после обсуждения конкретной задачи)
        → Найти последнюю обсуждаемую задачу из контекста
        """

    async def analyze_user_intent(self, user_message: str, tasks: List[Dict], 
                                 conversation_history: List[Dict] = None) -> Dict:
        """Анализ намерения пользователя относительно задач"""
        try:
            # Подготавливаем данные для анализа
            tasks_info = []
            for task in tasks:
                tasks_info.append({
                    "task_id": task['id'],
                    "title": task['title'],
                    "description": task.get('description', ''),
                    "status": task['status'], 
                    "priority": task['priority']
                })

            context_info = ""
            if conversation_history:
                context_info = "\n".join([
                    f"{msg.get('role', 'user')}: {msg.get('content', '')}" 
                    for msg in conversation_history[-5:]  # Последние 5 сообщений
                ])

            # Экранируем JSON чтобы избежать конфликта с переменными LangChain
            tasks_json = json.dumps(tasks_info, ensure_ascii=False, indent=2).replace('{', '{{').replace('}', '}}')
            
            analysis_prompt = f"""
            СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ: {user_message}

            СПИСОК ЗАДАЧ:
            {tasks_json}

            КОНТЕКСТ РАЗГОВОРА:
            {context_info}

            Проанализируй намерение пользователя и верни JSON с результатом анализа.
            """

            # Создаем промпт
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                ("human", analysis_prompt)
            ])

            # Используем JsonOutputParser для получения структурированного ответа
            parser = JsonOutputParser()
            chain = prompt | self.llm | parser

            result = await chain.ainvoke({})
            return result

        except Exception as e:
            logger.error(f"Error in TaskSelectorAgent: {e}")
            return {
                "action": "unknown",
                "selected_tasks": [],
                "requires_confirmation": True,
                "suggested_response": f"Не удалось проанализировать запрос: {str(e)}"
            }


class AIMentorAgent(BaseAgent):
    """AI-агент ментора с долгосрочной памятью"""
    
    def __init__(self, api_key: str, model: str = "gpt-4.1"):
        super().__init__(api_key, model)
        self.task_selector = TaskSelectorAgent(api_key, model)  # Добавляем умный селектор задач
        self.system_prompt = """
        Ты - AI-ментор для поддержки продуктивности и снижения стресса.
        
        Твои компетенции:
        - Управление стрессом и тревожностью
        - Планирование и организация времени
        - Борьба с прокрастинацией
        - Поддержка мотивации
        - Баланс работы и жизни
        
        У тебя есть доступ к долгосрочной памяти пользователя:
        - История задач и достижений
        - Дневные саммари за последние 30 дней
        - Уровень тревожности и цели пользователя
        - Паттерны продуктивности
        
        Используй эту информацию для персонализированных советов.
        Всегда отвечай на русском языке с пониманием и поддержкой.
        """
    
    async def chat_with_mentor(self, user_id: int, message: str, context: Dict = None) -> str:
        """Чат с AI-ментором"""
        try:
            # Получаем контекст пользователя
            if not context:
                context = await self._get_user_context(user_id)
            
            context_str = self._format_context(context)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt + f"\n\nКонтекст пользователя:\n{context_str}"),
                ("human", "{message}")
            ])
            
            chain = prompt | self.llm | StrOutputParser()
            response = await chain.ainvoke({"message": message})
            
            return response
        except Exception as e:
            logger.error(f"Error in AI Mentor: {e}")
            return "Извините, произошла ошибка при общении с ментором."
    
    async def _get_user_context(self, user_id: int) -> Dict:
        """Получение контекста пользователя"""
        try:
            # Получаем задачи
            tasks = self.db.get_tasks(user_id)
            analytics = self.db.get_task_analytics(user_id)
            
            # Сильная защита от None
            total_tasks = analytics.get('total_tasks', 0)
            if total_tasks is None or not isinstance(total_tasks, (int, float)):
                total_tasks = 0
                
            completion_rate = analytics.get('completion_rate', 0)
            if completion_rate is None or not isinstance(completion_rate, (int, float)):
                completion_rate = 0
            
            return {
                "total_tasks": int(total_tasks),
                "completion_rate": float(completion_rate),
                "recent_tasks": tasks[:5] if tasks else []
            }
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return {}
    
    def _format_context(self, context: Dict) -> str:
        """Форматирование контекста для промпта"""
        if not context:
            return "Новый пользователь, контекст отсутствует"
        
        formatted = f"Всего задач: {context.get('total_tasks', 0)}\n"
        formatted += f"Процент завершения: {context.get('completion_rate', 0):.1f}%\n"
        
        if context.get('recent_tasks'):
            formatted += "Недавние задачи:\n"
            for task in context['recent_tasks']:
                formatted += f"- {task['title']} ({task['status']})\n"
        
        return formatted
    
    async def analyze_task_mention(self, user_id: int, message: str, conversation_history: List[Dict] = None) -> Dict:
        """Анализ упоминания задач в общении с AI-ментором"""
        try:
            # Получаем все задачи пользователя
            tasks = self.db.get_tasks(user_id)
            
            if not tasks:
                return {
                    "action": "no_tasks",
                    "selected_tasks": [],
                    "suggested_response": "У вас пока нет задач. Хотите создать первую задачу?"
                }
            
            # Используем TaskSelectorAgent для анализа
            analysis = await self.task_selector.analyze_user_intent(
                user_message=message,
                tasks=tasks,
                conversation_history=conversation_history
            )
            
            # Адаптируем анализ для контекста ментора
            if analysis.get('action') in ['view', 'delete', 'update']:
                # В менторе основной фокус на консультировании и поддержке
                analysis['action'] = 'provide_guidance'
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing task mention in AI mentor: {e}")
            return {
                "action": "error",
                "selected_tasks": [],
                "suggested_response": "Не удалось проанализировать упоминание задачи."
            }
    
    async def provide_task_guidance(self, user_id: int, message: str, selected_tasks: List[Dict], 
                                   conversation_history: List[Dict] = None) -> str:
        """Предоставление консультации по конкретным задачам"""
        try:
            if not selected_tasks:
                return "Я не совсем понял о какой задаче вы говорите. Можете описать подробнее?"
            
            if len(selected_tasks) == 1:
                # Консультируем по конкретной задаче
                task = selected_tasks[0]
                
                # Получаем контекст пользователя для более персонализированного совета
                user_context = await self._get_user_context(user_id)
                
                context_info = ""
                if conversation_history:
                    context_info = "\n".join([
                        f"{msg.get('role', 'user')}: {msg.get('content', '')}" 
                        for msg in conversation_history[-3:]  # Последние 3 сообщения
                    ])
                
                guidance_prompt = f"""
                Пользователь обращается к AI-ментору за советом по конкретной задаче.
                
                ЗАДАЧА:
                Название: {task['title']}
                Описание: {task.get('description', 'Не указано')}
                Статус: {task.get('status', 'pending')}
                Приоритет: {task.get('priority', 'medium')}
                
                ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
                {self._format_context(user_context)}
                
                СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ: {message}
                
                КОНТЕКСТ РАЗГОВОРА:
                {context_info}
                
                Как AI-ментор, дай практический и мотивирующий совет:
                - Если задача не начата - помоги с планированием первых шагов
                - Если в процессе - поддержи и предложи оптимизацию
                - Если есть проблемы - помоги найти решения
                - Если завершена - поздравь и помоги извлечь уроки
                
                Фокусируйся на:
                - Практических советах по выполнению
                - Мотивации и преодолении прокрастинации  
                - Управлении стрессом и тревожностью
                - Планировании времени и приоритизации
                - Разбиении сложных задач на простые шаги
                
                Будь поддерживающим, практичным и вдохновляющим.
                """
                
                prompt = ChatPromptTemplate.from_messages([
                    ("system", self.system_prompt),
                    ("human", guidance_prompt)
                ])
                
                chain = prompt | self.llm | StrOutputParser()
                response = await chain.ainvoke({})
                
                # Добавляем информацию о задаче в начало
                priority_emoji = {'urgent': '🔥', 'high': '⚡', 'medium': '📋', 'low': '📝'}.get(task.get('priority', 'medium'), '📋')
                status_emoji = {'pending': '⏳', 'in_progress': '🔄', 'completed': '✅', 'cancelled': '❌'}.get(task.get('status', 'pending'), '⏳')
                
                return f"🧠 Консультируем по задаче: {priority_emoji} **{task['title']}** {status_emoji}\n\n{response}"
                
            else:
                # Несколько задач - предлагаем комплексную консультацию
                task_list = []
                for i, task in enumerate(selected_tasks[:5], 1):
                    priority_emoji = {'urgent': '🔥', 'high': '⚡', 'medium': '📋', 'low': '📝'}.get(task.get('priority', 'medium'), '📋')
                    status_emoji = {'pending': '⏳', 'in_progress': '🔄', 'completed': '✅', 'cancelled': '❌'}.get(task.get('status', 'pending'), '⏳')
                    task_list.append(f"{i}. {priority_emoji} {status_emoji} {task['title']}")
                
                # Получаем общий контекст пользователя
                user_context = await self._get_user_context(user_id)
                
                multiple_tasks_prompt = f"""
                Пользователь упоминает несколько задач и просит совета.
                
                ЗАДАЧИ:
                {chr(10).join(task_list)}
                
                ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
                {self._format_context(user_context)}
                
                СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ: {message}
                
                Дай комплексный совет как AI-ментор:
                - Помоги расставить приоритеты между задачами
                - Предложи стратегию работы с несколькими задачами
                - Дай советы по управлению временем
                - Помоги избежать перегрузки и выгорания
                
                Или предложи пользователю выбрать одну задачу для более детального обсуждения.
                """
                
                prompt = ChatPromptTemplate.from_messages([
                    ("system", self.system_prompt),
                    ("human", multiple_tasks_prompt)
                ])
                
                chain = prompt | self.llm | StrOutputParser()
                response = await chain.ainvoke({})
                
                return f"🧠 Консультируем по нескольким задачам:\n\n{response}"
                       
        except Exception as e:
            logger.error(f"Error providing task guidance: {e}")
            return "Извините, произошла ошибка при анализе задачи. Давайте попробуем обсудить это по-другому."


class OrchestratorAgent(BaseAgent):
    """AI-агент оркестратор с LLM роутингом"""
    
    def __init__(self, api_key: str, model: str = "gpt-4.1"):
        super().__init__(api_key, model)
        
        # Инициализируем все агенты
        self.welcome_agent = WelcomeAgent(api_key, model)
        self.task_agent = TaskManagementAgent(api_key, model)
        self.notification_agent = NotificationAgent(api_key, model)
        self.evening_agent = EveningTrackerAgent(api_key, model)
        self.mentor_agent = AIMentorAgent(api_key, model)
        self.task_selector = TaskSelectorAgent(api_key, model)  # Добавляем агент выбора задач
        
        self.system_prompt = """
        Ты - AI-оркестратор трекера продуктивности. Анализируй запросы пользователей 
        и определяй, какой агент должен их обработать.

        Доступные агенты:
        1. WELCOME - приветственный модуль, онбординг (6 шагов)
        2. TASK_MANAGEMENT - управление задачами (создание, редактирование, аналитика)
        3. NOTIFICATIONS - настройка уведомлений и часовых поясов
        4. EVENING_TRACKER - вечерние сессии рефлексии и обзора дня
        5. AI_MENTOR - общение с AI-ментором, советы по продуктивности

        ВАЖНЫЕ ПРАВИЛА РОУТИНГА:
        - "создать/добавить/сделать задачу" → TASK_MANAGEMENT
        - "показать/список/какие задачи" → TASK_MANAGEMENT
        - "удалить/изменить задачу" → TASK_MANAGEMENT
        - "сколько задач/статистика" → TASK_MANAGEMENT
        - "как справиться/советы/помощь" → AI_MENTOR
        - "уведомления/настройки" → NOTIFICATIONS
        - "вечерний трекер" → EVENING_TRACKER

        Анализируй намерение пользователя и выбери ОДИН агент.
        Верни JSON с полями: {{"agent": "название_агента", "confidence": 0.95, "reasoning": "обоснование"}}
        """
    
    async def route_request(self, user_id: int, message: str, user_state: Dict = None) -> Dict[str, Any]:
        """LLM роутинг запроса к подходящему агенту"""
        try:
            # Проверяем, если это подтверждение удаления
            if self._is_deletion_confirmation(message):
                # Извлекаем task_id из сообщения если есть
                task_id = self._extract_task_id_from_message(message)
                if task_id:
                    # Прямое удаление с подтверждением
                    response = await self.task_agent.process_message(user_id, message, {"task_id": task_id})
                    return {
                        "agent": "TASK_MANAGEMENT",
                        "confidence": 1.0,
                        "reasoning": "Подтверждение удаления задачи",
                        "response": response
                    }
                else:
                    # Попробуем найти задачу через LLM анализ
                    logger.info("Подтверждение без task_id, пытаемся найти задачу через LLM")
                    context = {"conversation_history": []}  # TODO: получать реальную историю
                    response = await self.task_agent.process_message(user_id, message, context)
                    return {
                        "agent": "TASK_MANAGEMENT", 
                        "confidence": 0.7,
                        "reasoning": "Подтверждение удаления через LLM анализ",
                        "response": response
                    }
            
            # Получаем состояние пользователя для контекста
            if not user_state:
                user_state = await self._get_user_state(user_id)
            
            state_context = self._format_user_state(user_state)
            
            # LLM роутинг
            routing_prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt + f"\n\nКонтекст пользователя:\n{state_context}"),
                ("human", "{message}")
            ])
            
            chain = routing_prompt | self.llm | JsonOutputParser()
            routing_result = await chain.ainvoke({"message": message})
            
            agent_name = routing_result.get("agent", "AI_MENTOR")
            confidence = routing_result.get("confidence", 0.5)
            reasoning = routing_result.get("reasoning", "")
            
            logger.info(f"Routing: {agent_name} (confidence: {confidence}) - {reasoning}")
            
            # Вызываем соответствующего агента
            response = await self._delegate_to_agent(agent_name, user_id, message, user_state)
            
            return {
                "agent": agent_name,
                "confidence": confidence,
                "reasoning": reasoning,
                "response": response
            }
            
        except Exception as e:
            logger.error(f"Error in orchestrator routing: {e}")
            # Fallback к AI-ментору
            response = await self.mentor_agent.chat_with_mentor(user_id, message)
            return {
                "agent": "AI_MENTOR",
                "confidence": 0.1,
                "reasoning": "Fallback после ошибки роутинга",
                "response": response
            }
    
    async def _delegate_to_agent(self, agent_name: str, user_id: int, message: str, user_state: Dict) -> str:
        """Делегирование запроса конкретному агенту"""
        try:
            if agent_name == "WELCOME":
                current_step = user_state.get('welcome_step', 'greeting')
                result = await self.welcome_agent.process_welcome_step(user_id, current_step, message)
                return result.get('response', 'Ошибка в приветственном модуле')
                
            elif agent_name == "TASK_MANAGEMENT":
                # Передаем историю разговора для контекста
                context = {"conversation_history": []}  # TODO: получать реальную историю
                return await self.task_agent.process_message(user_id, message, context)
                
            elif agent_name == "NOTIFICATIONS":
                return await self.notification_agent.process_notification_request(user_id, message)
                
            elif agent_name == "EVENING_TRACKER":
                session_state = user_state.get('evening_state', 'starting')
                return await self.evening_agent.process_evening_message(user_id, message, session_state)
                
            elif agent_name == "AI_MENTOR":
                return await self.mentor_agent.chat_with_mentor(user_id, message, user_state)
                
            else:
                # Fallback к AI-ментору
                return await self.mentor_agent.chat_with_mentor(user_id, message, user_state)
                
        except Exception as e:
            logger.error(f"Error delegating to {agent_name}: {e}")
            return "Извините, произошла ошибка при обработке запроса."
    
    async def _get_user_state(self, user_id: int) -> Dict:
        """Получение текущего состояния пользователя"""
        try:
            # Здесь должна быть логика получения состояния из базы/файлов
            # Пока что возвращаем базовое состояние
            analytics = self.db.get_task_analytics(user_id)
            logger.info(f"FIXED_VERSION: Raw analytics for user {user_id}: {analytics}")
            
            # Очень сильная защита от None и других неожиданных типов
            total_tasks = analytics.get('total_tasks', 0)
            if total_tasks is None or not isinstance(total_tasks, (int, float)):
                total_tasks = 0
                
            completed_tasks = analytics.get('completed_tasks', 0)
            if completed_tasks is None or not isinstance(completed_tasks, (int, float)):
                completed_tasks = 0
            
            logger.debug(f"Processed values - total_tasks: {total_tasks} (type: {type(total_tasks)}), completed_tasks: {completed_tasks} (type: {type(completed_tasks)})")
            
            active_tasks = int(total_tasks) - int(completed_tasks)
            logger.debug(f"Calculated active_tasks: {active_tasks}")
            
            return {
                "welcome_completed": True,  # Нужно получать из tracker_data.yaml
                "total_tasks": total_tasks,
                "active_tasks": active_tasks,
                "completion_rate": analytics.get('completion_rate', 0) or 0,
                "evening_state": "starting",  # Нужно получать из текущей сессии
                "welcome_step": "completed"
            }
        except Exception as e:
            logger.error(f"Error getting user state: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {}
    
    def _format_user_state(self, user_state: Dict) -> str:
        """Форматирование состояния пользователя для промпта"""
        if not user_state:
            return "Новый пользователь"
        
        formatted = f"Приветственный модуль: {'завершен' if user_state.get('welcome_completed') else 'не завершен'}\n"
        formatted += f"Всего задач: {user_state.get('total_tasks', 0)}\n"
        formatted += f"Активных задач: {user_state.get('active_tasks', 0)}\n"
        formatted += f"Процент завершения: {user_state.get('completion_rate', 0):.1f}%\n"
        
        return formatted
    
    def _is_deletion_confirmation(self, message: str) -> bool:
        """Проверяет, является ли сообщение подтверждением удаления"""
        message_lower = message.lower().strip()
        
        confirmation_phrases = [
            'да', 'yes', 'подтверждаю', 'удаляю', 'удалить',
            'подтверждаю удаление', 'согласен', 'хорошо',
            'ok', 'ок', 'давай', 'удали'
        ]
        
        # Проверяем, содержит ли сообщение ID задачи и подтверждающую фразу
        has_confirmation = any(phrase in message_lower for phrase in confirmation_phrases)
        has_task_id = len([part for part in message_lower.split() if len(part) > 20 and '-' in part]) > 0
        
        return has_confirmation and (has_task_id or len(message_lower.split()) <= 3)
    
    def _extract_task_id_from_message(self, message: str) -> str:
        """Извлекает task_id из сообщения пользователя"""
        import re
        
        # Ищем UUID в сообщении (формат: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        matches = re.findall(uuid_pattern, message.lower())
        
        return matches[0] if matches else None


# Функция инициализации
def initialize_enhanced_agents(api_key: str, model: str = "gpt-4.1") -> OrchestratorAgent:
    """Инициализация улучшенной системы агентов"""
    try:
        orchestrator = OrchestratorAgent(api_key, model)
        logger.info("Enhanced AI agents system initialized successfully")
        return orchestrator
    except Exception as e:
        logger.error(f"Error initializing enhanced agents: {e}")
        raise