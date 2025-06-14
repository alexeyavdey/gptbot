"""
SQLite база данных для хранения задач трекера
"""

import sqlite3
import json
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager

try:
    from .logger import create_logger
except ImportError:
    import logging
    def create_logger(name):
        return logging.getLogger(name)

logger = create_logger(__name__)

# Путь к базе данных
DB_PATH = Path(__file__).parent / "tracker.db"

class TaskDatabase:
    """Менеджер базы данных для задач трекера"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self.init_database()
    
    def init_database(self):
        """Инициализация структуры базы данных"""
        with self.get_connection() as conn:
            # Таблица пользователей трекера
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracker_users (
                    user_id INTEGER PRIMARY KEY,
                    step TEXT DEFAULT 'greeting',
                    completed BOOLEAN DEFAULT 0,
                    started_at INTEGER,
                    anxiety_level REAL,
                    anxiety_answers TEXT, -- JSON array
                    goals TEXT, -- JSON array
                    notifications TEXT, -- JSON object
                    met_ai_mentor BOOLEAN DEFAULT 0,
                    ai_mentor_history TEXT, -- JSON array
                    timezone TEXT DEFAULT 'UTC',
                    notification_time TEXT DEFAULT '09:00',
                    current_view TEXT DEFAULT 'main',
                    evening_tracking_enabled BOOLEAN DEFAULT 1,
                    evening_tracking_time TEXT DEFAULT '21:00',
                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # Таблица задач
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    priority TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'pending',
                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    updated_at INTEGER DEFAULT (strftime('%s', 'now')),
                    due_date INTEGER,
                    completed_at INTEGER,
                    FOREIGN KEY (user_id) REFERENCES tracker_users (user_id)
                )
            """)
            
            # Таблица вечерних сессий
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evening_sessions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL, -- YYYY-MM-DD
                    state TEXT DEFAULT 'starting',
                    started_at INTEGER DEFAULT (strftime('%s', 'now')),
                    completed_at INTEGER,
                    task_reviews TEXT, -- JSON array
                    current_task_index INTEGER DEFAULT 0,
                    gratitude_answer TEXT DEFAULT '',
                    summary TEXT DEFAULT '',
                    ai_conversation TEXT, -- JSON array
                    FOREIGN KEY (user_id) REFERENCES tracker_users (user_id),
                    UNIQUE(user_id, date)
                )
            """)
            
            # Таблица дневных саммари
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL, -- YYYY-MM-DD
                    tasks_reviewed INTEGER DEFAULT 0,
                    tasks_with_progress INTEGER DEFAULT 0,
                    tasks_needing_help INTEGER DEFAULT 0,
                    gratitude_theme TEXT DEFAULT '',
                    productivity_level TEXT DEFAULT 'medium',
                    summary_text TEXT DEFAULT '',
                    key_insights TEXT, -- JSON array
                    mood_indicators TEXT, -- JSON array
                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    FOREIGN KEY (user_id) REFERENCES tracker_users (user_id),
                    UNIQUE(user_id, date)
                )
            """)
            
            # Индексы для оптимизации
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_evening_sessions_user_date ON evening_sessions(user_id, date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_summaries_user_date ON daily_summaries(user_id, date)")
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для подключения к БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Доступ к колонкам по именам
        try:
            yield conn
        finally:
            conn.close()
    
    # === ОПЕРАЦИИ С ЗАДАЧАМИ ===
    
    def create_task(self, user_id: int, title: str, description: str = '', 
                   priority: str = 'medium', due_date: int = None) -> str:
        """Создание новой задачи"""
        try:
            task_id = str(uuid.uuid4())
            current_time = int(datetime.now().timestamp())
            
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO tasks (id, user_id, title, description, priority, due_date, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (task_id, user_id, title, description, priority, due_date, current_time, current_time))
                conn.commit()
            
            logger.info(f"Task created: {task_id} for user {user_id}")
            return task_id
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            raise
    
    def get_tasks(self, user_id: int, status: str = None) -> List[Dict]:
        """Получение задач пользователя"""
        try:
            with self.get_connection() as conn:
                if status:
                    cursor = conn.execute("""
                        SELECT * FROM tasks 
                        WHERE user_id = ? AND status = ? 
                        ORDER BY created_at DESC
                    """, (user_id, status))
                else:
                    cursor = conn.execute("""
                        SELECT * FROM tasks 
                        WHERE user_id = ? 
                        ORDER BY created_at DESC
                    """, (user_id,))
                
                tasks = []
                for row in cursor.fetchall():
                    tasks.append(dict(row))
                
                logger.info(f"Retrieved {len(tasks)} tasks for user {user_id}")
                return tasks
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            return []
    
    def update_task_status(self, task_id: str, user_id: int, new_status: str) -> bool:
        """Обновление статуса задачи"""
        try:
            current_time = int(datetime.now().timestamp())
            completed_at = current_time if new_status == 'completed' else None
            
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    UPDATE tasks 
                    SET status = ?, updated_at = ?, completed_at = ?
                    WHERE id = ? AND user_id = ?
                """, (new_status, current_time, completed_at, task_id, user_id))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"Task {task_id} status updated to {new_status}")
                    return True
                else:
                    logger.warning(f"Task {task_id} not found for user {user_id}")
                    return False
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            return False
    
    def update_task_priority(self, task_id: str, user_id: int, new_priority: str) -> bool:
        """Обновление приоритета задачи"""
        try:
            current_time = int(datetime.now().timestamp())
            
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    UPDATE tasks 
                    SET priority = ?, updated_at = ?
                    WHERE id = ? AND user_id = ?
                """, (new_priority, current_time, task_id, user_id))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"Task {task_id} priority updated to {new_priority}")
                    return True
                else:
                    logger.warning(f"Task {task_id} not found for user {user_id}")
                    return False
        except Exception as e:
            logger.error(f"Error updating task priority: {e}")
            return False
    
    def delete_task(self, task_id: str, user_id: int) -> bool:
        """Удаление задачи"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    DELETE FROM tasks 
                    WHERE id = ? AND user_id = ?
                """, (task_id, user_id))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"Task {task_id} deleted")
                    return True
                else:
                    logger.warning(f"Task {task_id} not found for user {user_id}")
                    return False
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            return False
    
    def get_task_analytics(self, user_id: int) -> Dict:
        """Получение аналитики по задачам"""
        try:
            with self.get_connection() as conn:
                # Общая статистика
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_tasks,
                        COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) as completed_tasks,
                        COALESCE(SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END), 0) as in_progress_tasks,
                        COALESCE(SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END), 0) as pending_tasks
                    FROM tasks 
                    WHERE user_id = ?
                """, (user_id,))
                
                stats = dict(cursor.fetchone())
                logger.debug(f"Raw stats from database for user {user_id}: {stats}")
                
                # Статистика по приоритетам
                cursor = conn.execute("""
                    SELECT priority, COUNT(*) as count
                    FROM tasks 
                    WHERE user_id = ?
                    GROUP BY priority
                """, (user_id,))
                
                priority_stats = {}
                for row in cursor.fetchall():
                    priority_stats[row['priority']] = row['count']
                
                # Вычисляем процент завершения
                total = stats.get('total_tasks', 0) or 0
                completed = stats.get('completed_tasks', 0) or 0
                completion_rate = (completed / total * 100) if total > 0 else 0
                
                analytics = {
                    **stats,
                    'completion_rate': round(completion_rate, 2),
                    'priority_distribution': priority_stats
                }
                
                logger.info(f"Analytics calculated for user {user_id}")
                return analytics
        except Exception as e:
            logger.error(f"Error getting task analytics: {e}")
            return {}
    
    # === ОПЕРАЦИИ С ПОЛЬЗОВАТЕЛЯМИ ===
    
    def ensure_user_exists(self, user_id: int) -> bool:
        """Создание пользователя если не существует"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT user_id FROM tracker_users WHERE user_id = ?", (user_id,))
                if cursor.fetchone() is None:
                    current_time = int(datetime.now().timestamp())
                    conn.execute("""
                        INSERT INTO tracker_users (user_id, started_at, created_at, updated_at)
                        VALUES (?, ?, ?, ?)
                    """, (user_id, current_time, current_time, current_time))
                    conn.commit()
                    logger.info(f"Created new tracker user: {user_id}")
                return True
        except Exception as e:
            logger.error(f"Error ensuring user exists: {e}")
            return False
    
    def get_user_data(self, user_id: int) -> Optional[Dict]:
        """Получение данных пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM tracker_users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Error getting user data: {e}")
            return None
    
    def update_user_data(self, user_id: int, **kwargs) -> bool:
        """Обновление данных пользователя"""
        try:
            if not kwargs:
                return True
                
            # Добавляем updated_at
            kwargs['updated_at'] = int(datetime.now().timestamp())
            
            fields = ', '.join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values()) + [user_id]
            
            with self.get_connection() as conn:
                conn.execute(f"""
                    UPDATE tracker_users 
                    SET {fields}
                    WHERE user_id = ?
                """, values)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating user data: {e}")
            return False

# Глобальный экземпляр базы данных
db = TaskDatabase()

def get_database() -> TaskDatabase:
    """Получение экземпляра базы данных"""
    return db