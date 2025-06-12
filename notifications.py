import asyncio
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import pytz
from .logger import create_logger
from .tracker import (
    get_user_data, get_tasks_by_status, TaskStatus, TaskPriority,
    PRIORITY_DESCRIPTIONS, STATUS_DESCRIPTIONS, format_task_text
)

logger = create_logger(__name__)

class NotificationManager:
    """Менеджер уведомлений для трекера задач"""
    
    def __init__(self, bot_instance=None):
        self.bot = bot_instance
        self.running = False
        self.scheduler_thread = None
        self.notification_handlers: Dict[str, Callable] = {}
        
        # Регистрируем стандартные обработчики уведомлений
        self.register_handler("daily_digest", self._send_daily_digest)
        self.register_handler("deadline_reminder", self._send_deadline_reminder)
        self.register_handler("new_task_notification", self._send_new_task_notification)
    
    def register_handler(self, notification_type: str, handler: Callable):
        """Регистрирует обработчик для типа уведомлений"""
        self.notification_handlers[notification_type] = handler
        logger.info(f"Registered notification handler: {notification_type}")
    
    def start_scheduler(self):
        """Запускает планировщик уведомлений в отдельном потоке"""
        if self.running:
            logger.warning("Notification scheduler already running")
            return
        
        self.running = True
        
        # Настраиваем расписание
        self._setup_schedule()
        
        # Запускаем планировщик в отдельном потоке
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Notification scheduler started")
    
    def stop_scheduler(self):
        """Останавливает планировщик уведомлений"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        schedule.clear()
        logger.info("Notification scheduler stopped")
    
    def _setup_schedule(self):
        """Настраивает расписание уведомлений"""
        # Ежедневный дайджест в 9:00
        schedule.every().day.at("09:00").do(self._schedule_daily_digest)
        
        # Проверка дедлайнов каждые 2 часа
        schedule.every(2).hours.do(self._schedule_deadline_reminders)
        
        # Очистка старых уведомлений раз в день в 23:59
        schedule.every().day.at("23:59").do(self._cleanup_old_notifications)
        
        logger.info("Notification schedule configured")
    
    def _run_scheduler(self):
        """Основной цикл планировщика"""
        logger.info("Notification scheduler thread started")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Проверяем каждую минуту
            except Exception as e:
                logger.error(f"Error in notification scheduler: {e}")
                time.sleep(60)
        
        logger.info("Notification scheduler thread stopped")
    
    def _schedule_daily_digest(self):
        """Планирует отправку ежедневного дайджеста"""
        if not self.bot:
            return
        
        asyncio.create_task(self._send_daily_digest_to_all_users())
    
    def _schedule_deadline_reminders(self):
        """Планирует проверку и отправку напоминаний о дедлайнах"""
        if not self.bot:
            return
        
        asyncio.create_task(self._send_deadline_reminders_to_all_users())
    
    async def _send_daily_digest_to_all_users(self):
        """Отправляет ежедневный дайджест всем пользователям"""
        try:
            from .tracker import load_tracker_data
            
            all_data = load_tracker_data()
            
            for user_id_str, user_data_dict in all_data.items():
                try:
                    user_id = int(user_id_str)
                    
                    # Проверяем, включены ли уведомления
                    notifications = user_data_dict.get('notifications', {})
                    if not notifications.get('enabled', True) or not notifications.get('daily_digest', False):
                        continue
                    
                    user_data = get_user_data(user_id)
                    if not user_data.completed:  # Пользователь не завершил welcome module
                        continue
                    
                    await self._send_daily_digest(user_id, user_data)
                    
                except Exception as e:
                    logger.error(f"Error sending daily digest to user {user_id_str}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in daily digest broadcast: {e}")
    
    async def _send_deadline_reminders_to_all_users(self):
        """Отправляет напоминания о дедлайнах всем пользователям"""
        try:
            from .tracker import load_tracker_data
            
            all_data = load_tracker_data()
            
            for user_id_str, user_data_dict in all_data.items():
                try:
                    user_id = int(user_id_str)
                    
                    # Проверяем, включены ли уведомления
                    notifications = user_data_dict.get('notifications', {})
                    if not notifications.get('enabled', True) or not notifications.get('deadline_reminders', False):
                        continue
                    
                    user_data = get_user_data(user_id)
                    if not user_data.completed:
                        continue
                    
                    await self._send_deadline_reminder(user_id, user_data)
                    
                except Exception as e:
                    logger.error(f"Error sending deadline reminder to user {user_id_str}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in deadline reminders broadcast: {e}")
    
    async def _send_daily_digest(self, user_id: int, user_data=None):
        """Отправляет ежедневный дайджест конкретному пользователю"""
        if not self.bot:
            return
        
        try:
            if not user_data:
                user_data = get_user_data(user_id)
            
            # Получаем статистику задач
            pending_tasks = get_tasks_by_status(user_data, TaskStatus.PENDING)
            in_progress_tasks = get_tasks_by_status(user_data, TaskStatus.IN_PROGRESS)
            completed_today_tasks = self._get_tasks_completed_today(user_data)
            
            # Получаем высокоприоритетные задачи
            urgent_tasks = [task for task in pending_tasks + in_progress_tasks 
                          if task.priority in [TaskPriority.HIGH, TaskPriority.URGENT]]
            
            # Формируем сообщение
            text = "🌅 **Доброе утро! Ваш ежедневный дайджест**\n\n"
            
            # Статистика
            text += f"📊 **Статистика на сегодня:**\n"
            text += f"• ⏳ Ожидают выполнения: {len(pending_tasks)}\n"
            text += f"• 🔄 В работе: {len(in_progress_tasks)}\n"
            text += f"• ✅ Завершено вчера: {len(completed_today_tasks)}\n\n"
            
            # Приоритетные задачи
            if urgent_tasks:
                text += f"🚨 **Важные задачи на сегодня:**\n"
                for i, task in enumerate(urgent_tasks[:3], 1):
                    text += f"{i}. {format_task_text(task)}\n"
                
                if len(urgent_tasks) > 3:
                    text += f"... и еще {len(urgent_tasks) - 3} важных задач\n"
                text += "\n"
            
            # Мотивационное сообщение
            if completed_today_tasks:
                text += f"🎉 Отличная работа! Вчера вы завершили {len(completed_today_tasks)} задач!\n\n"
            
            # Совет дня
            text += f"💡 **Совет дня:** "
            if len(urgent_tasks) > 3:
                text += "У вас много важных задач. Попробуйте технику Pomodoro для лучшей концентрации."
            elif not pending_tasks and not in_progress_tasks:
                text += "Отличная работа! Самое время запланировать новые цели или отдохнуть."
            else:
                text += "Начните день с самой важной задачи - это даст заряд энергии на весь день!"
            
            # Отправляем уведомление
            await self.bot.send_message(user_id, text, parse_mode="Markdown")
            logger.info(f"Daily digest sent to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending daily digest to user {user_id}: {e}")
    
    async def _send_deadline_reminder(self, user_id: int, user_data=None):
        """Отправляет напоминание о приближающихся дедлайнах"""
        if not self.bot:
            return
        
        try:
            if not user_data:
                user_data = get_user_data(user_id)
            
            # Получаем задачи с дедлайнами в ближайшие 24 часа
            upcoming_deadlines = self._get_upcoming_deadlines(user_data, hours=24)
            
            if not upcoming_deadlines:
                return
            
            text = "⏰ **Напоминание о дедлайнах**\n\n"
            text += f"У вас есть {len(upcoming_deadlines)} задач с приближающимися дедлайнами:\n\n"
            
            for i, (task, hours_left) in enumerate(upcoming_deadlines[:5], 1):
                if hours_left < 1:
                    time_text = "менее часа"
                elif hours_left < 24:
                    time_text = f"через {int(hours_left)} ч."
                else:
                    time_text = f"через {int(hours_left/24)} дн."
                
                text += f"{i}. {format_task_text(task)} (⏰ {time_text})\n"
            
            if len(upcoming_deadlines) > 5:
                text += f"\n... и еще {len(upcoming_deadlines) - 5} задач"
            
            text += f"\n\n💪 Не забывайте: лучше завершить заранее, чем в последний момент!"
            
            await self.bot.send_message(user_id, text, parse_mode="Markdown")
            logger.info(f"Deadline reminder sent to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending deadline reminder to user {user_id}: {e}")
    
    async def _send_new_task_notification(self, user_id: int, task_title: str):
        """Отправляет уведомление о новой задаче"""
        if not self.bot:
            return
        
        try:
            user_data = get_user_data(user_id)
            
            # Проверяем, включены ли уведомления
            if not user_data.notifications.get('enabled', True):
                return
            if not user_data.notifications.get('new_task_notifications', False):
                return
            
            text = f"📝 **Новая задача создана**\n\n{task_title}\n\nУдачи в выполнении!"
            
            await self.bot.send_message(user_id, text, parse_mode="Markdown")
            logger.info(f"New task notification sent to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending new task notification to user {user_id}: {e}")
    
    def _get_tasks_completed_today(self, user_data) -> List:
        """Получает задачи, завершенные за последние 24 часа"""
        now = int(time.time())
        yesterday = now - 24 * 60 * 60
        
        completed_today = []
        for task in user_data.tasks:
            if (task.status == TaskStatus.COMPLETED and 
                task.completed_at and 
                task.completed_at >= yesterday):
                completed_today.append(task)
        
        return completed_today
    
    def _get_upcoming_deadlines(self, user_data, hours: int = 24) -> List:
        """Получает задачи с дедлайнами в ближайшие N часов"""
        now = int(time.time())
        deadline_threshold = now + hours * 60 * 60
        
        upcoming = []
        for task in user_data.tasks:
            if (task.due_date and 
                task.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS] and
                task.due_date <= deadline_threshold):
                hours_left = (task.due_date - now) / 3600
                upcoming.append((task, hours_left))
        
        # Сортируем по приближающемуся дедлайну
        upcoming.sort(key=lambda x: x[1])
        return upcoming
    
    def _cleanup_old_notifications(self):
        """Очищает старые данные уведомлений"""
        logger.info("Cleaning up old notification data")
        # Здесь можно добавить логику очистки старых данных
    
    async def notify_new_task(self, user_id: int, task_title: str):
        """Публичный метод для уведомления о новой задаче"""
        await self._send_new_task_notification(user_id, task_title)
    
    async def send_manual_digest(self, user_id: int):
        """Отправляет дайджест вручную"""
        user_data = get_user_data(user_id)
        await self._send_daily_digest(user_id, user_data)

# Глобальный экземпляр менеджера уведомлений
notification_manager = NotificationManager()

def get_notification_manager() -> NotificationManager:
    """Возвращает глобальный экземпляр менеджера уведомлений"""
    return notification_manager

def init_notifications(bot_instance):
    """Инициализирует систему уведомлений"""
    global notification_manager
    notification_manager.bot = bot_instance
    notification_manager.start_scheduler()
    logger.info("Notification system initialized")

def stop_notifications():
    """Останавливает систему уведомлений"""
    global notification_manager
    notification_manager.stop_scheduler()
    logger.info("Notification system stopped")