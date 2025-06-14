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
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.llm = ChatOpenAI(
            api_key=api_key,
            model=model,
            temperature=0.3
        )
        self.db = get_database()
        self.name = self.__class__.__name__
        logger.info(f"Initialized {self.name}")


class WelcomeAgent(BaseAgent):
    """AI-агент для приветственного модуля (6-step onboarding)"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
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
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        super().__init__(api_key, model)
        self.tools = self._create_tools()
        self.system_prompt = """
        Ты - AI-агент для управления задачами в трекере продуктивности.
        
        Твои возможности:
        - Создание, редактирование и удаление задач
        - Управление приоритетами и статусами задач
        - Фильтрация задач по различным критериям
        - Предоставление аналитики и статистики
        - Помощь в планировании и приоритизации
        
        ВАЖНО: Используй доступные инструменты для выполнения операций с задачами.
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
                description="Удалить задачу. Параметры: user_id, task_id",
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
            
            return json.dumps({
                "success": True,
                "task_id": task_id,
                "message": f"Задача '{title}' создана с приоритетом {priority}"
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def _get_tasks(self, params: str) -> str:
        """Получение списка задач"""
        try:
            data = json.loads(params)
            user_id = data['user_id']
            status = data.get('status')
            
            self.db.ensure_user_exists(user_id)
            tasks = self.db.get_tasks(user_id, status)
            
            return json.dumps({"success": True, "tasks": tasks})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
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
        """Удаление задачи"""
        try:
            data = json.loads(params)
            user_id = data['user_id']
            task_id = data['task_id']
            
            success = self.db.delete_task(task_id, user_id)
            
            return json.dumps({
                "success": success,
                "message": "Задача удалена" if success else "Ошибка удаления"
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def _get_analytics(self, params: str) -> str:
        """Получение аналитики"""
        try:
            data = json.loads(params)
            user_id = data['user_id']
            
            self.db.ensure_user_exists(user_id)
            analytics = self.db.get_task_analytics(user_id)
            
            return json.dumps({"success": True, "analytics": analytics})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
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
            # Создаем агента с tools
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt + f"\n\nИдентификатор пользователя: {user_id}"),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}")
            ])
            
            agent = create_openai_tools_agent(self.llm, self.tools, prompt)
            agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=False)
            
            result = await agent_executor.ainvoke({"input": message})
            return result.get("output", "Не удалось обработать запрос")
            
        except Exception as e:
            logger.error(f"Error in TaskManagementAgent: {e}")
            return "Извините, произошла ошибка при обработке запроса по задачам."


class NotificationAgent(BaseAgent):
    """AI-агент для управления уведомлениями (Phase 3 функциональность)"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
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
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        super().__init__(api_key, model)
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


class AIMentorAgent(BaseAgent):
    """AI-агент ментора с долгосрочной памятью"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        super().__init__(api_key, model)
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


class OrchestratorAgent(BaseAgent):
    """AI-агент оркестратор с LLM роутингом"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        super().__init__(api_key, model)
        
        # Инициализируем все агенты
        self.welcome_agent = WelcomeAgent(api_key, model)
        self.task_agent = TaskManagementAgent(api_key, model)
        self.notification_agent = NotificationAgent(api_key, model)
        self.evening_agent = EveningTrackerAgent(api_key, model)
        self.mentor_agent = AIMentorAgent(api_key, model)
        
        self.system_prompt = """
        Ты - AI-оркестратор трекера продуктивности. Анализируй запросы пользователей 
        и определяй, какой агент должен их обработать.

        Доступные агенты:
        1. WELCOME - приветственный модуль, онбординг (6 шагов)
        2. TASK_MANAGEMENT - управление задачами (создание, редактирование, аналитика)
        3. NOTIFICATIONS - настройка уведомлений и часовых поясов
        4. EVENING_TRACKER - вечерние сессии рефлексии и обзора дня
        5. AI_MENTOR - общение с AI-ментором, советы по продуктивности

        Анализируй намерение пользователя и выбери ОДИН агент.
        Верни JSON с полями: {{"agent": "название_агента", "confidence": 0.95, "reasoning": "обоснование"}}
        """
    
    async def route_request(self, user_id: int, message: str, user_state: Dict = None) -> Dict[str, Any]:
        """LLM роутинг запроса к подходящему агенту"""
        try:
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
                return await self.task_agent.process_task_request(user_id, message)
                
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


# Функция инициализации
def initialize_enhanced_agents(api_key: str, model: str = "gpt-4") -> OrchestratorAgent:
    """Инициализация улучшенной системы агентов"""
    try:
        orchestrator = OrchestratorAgent(api_key, model)
        logger.info("Enhanced AI agents system initialized successfully")
        return orchestrator
    except Exception as e:
        logger.error(f"Error initializing enhanced agents: {e}")
        raise