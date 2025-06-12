#!/usr/bin/env python3
"""
Простой тест для основных функций трекера задач
"""

import uuid
import time

# Базовые классы для тестирования
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

class TrackerTask:
    def __init__(self, title: str, description: str = "", priority: str = TaskPriority.MEDIUM):
        self.id = str(uuid.uuid4())
        self.title = title
        self.description = description
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = int(time.time())
        self.updated_at = int(time.time())
        self.due_date = None
        self.completed_at = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'due_date': self.due_date,
            'completed_at': self.completed_at
        }

class TrackerUserData:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.tasks = []

# Функции для тестирования
def create_task(user_data: TrackerUserData, title: str, description: str = "", priority: str = TaskPriority.MEDIUM):
    task = TrackerTask(title, description, priority)
    user_data.tasks.append(task)
    return task

def get_task_by_id(user_data: TrackerUserData, task_id: str):
    for task in user_data.tasks:
        if task.id == task_id:
            return task
    return None

def update_task_status(user_data: TrackerUserData, task_id: str, new_status: str):
    task = get_task_by_id(user_data, task_id)
    if task:
        task.status = new_status
        task.updated_at = int(time.time())
        if new_status == TaskStatus.COMPLETED:
            task.completed_at = int(time.time())
        return True
    return False

def get_tasks_by_status(user_data: TrackerUserData, status: str):
    return [task for task in user_data.tasks if task.status == status]

def test_tracker_functions():
    """Основной тест функций трекера"""
    print("🧪 Начинаем тестирование функций трекера...")
    
    # Создаем тестового пользователя
    user_data = TrackerUserData(123)
    
    # Тест 1: Создание задачи
    print("\n1. Тестируем создание задачи...")
    task1 = create_task(user_data, "Тестовая задача 1", "Описание задачи", TaskPriority.HIGH)
    assert task1.title == "Тестовая задача 1"
    assert task1.priority == TaskPriority.HIGH
    assert task1.status == TaskStatus.PENDING
    assert len(user_data.tasks) == 1
    print("✅ Создание задачи работает корректно")
    
    # Тест 2: Поиск задачи по ID
    print("\n2. Тестируем поиск задачи по ID...")
    found_task = get_task_by_id(user_data, task1.id)
    assert found_task is not None
    assert found_task.title == "Тестовая задача 1"
    
    not_found = get_task_by_id(user_data, "несуществующий-id")
    assert not_found is None
    print("✅ Поиск задач работает корректно")
    
    # Тест 3: Обновление статуса
    print("\n3. Тестируем обновление статуса...")
    result = update_task_status(user_data, task1.id, TaskStatus.IN_PROGRESS)
    assert result == True
    assert task1.status == TaskStatus.IN_PROGRESS
    
    result = update_task_status(user_data, task1.id, TaskStatus.COMPLETED)
    assert result == True
    assert task1.status == TaskStatus.COMPLETED
    assert task1.completed_at is not None
    print("✅ Обновление статуса работает корректно")
    
    # Тест 4: Создание нескольких задач
    print("\n4. Тестируем создание нескольких задач...")
    task2 = create_task(user_data, "Задача 2", "", TaskPriority.LOW)
    task3 = create_task(user_data, "Задача 3", "", TaskPriority.URGENT)
    
    assert len(user_data.tasks) == 3
    print("✅ Создание нескольких задач работает корректно")
    
    # Тест 5: Фильтрация по статусу
    print("\n5. Тестируем фильтрацию по статусу...")
    update_task_status(user_data, task2.id, TaskStatus.IN_PROGRESS)
    
    pending_tasks = get_tasks_by_status(user_data, TaskStatus.PENDING)
    in_progress_tasks = get_tasks_by_status(user_data, TaskStatus.IN_PROGRESS)
    completed_tasks = get_tasks_by_status(user_data, TaskStatus.COMPLETED)
    
    assert len(pending_tasks) == 1  # task3
    assert len(in_progress_tasks) == 1  # task2
    assert len(completed_tasks) == 1  # task1
    print("✅ Фильтрация по статусу работает корректно")
    
    # Тест 6: Сериализация данных
    print("\n6. Тестируем сериализацию данных...")
    task_dict = task1.to_dict()
    assert 'id' in task_dict
    assert 'title' in task_dict
    assert task_dict['title'] == "Тестовая задача 1"
    assert task_dict['status'] == TaskStatus.COMPLETED
    print("✅ Сериализация данных работает корректно")
    
    print("\n🎉 Все тесты прошли успешно!")
    print(f"📊 Статистика:")
    print(f"   • Всего задач: {len(user_data.tasks)}")
    print(f"   • В ожидании: {len(pending_tasks)}")
    print(f"   • В работе: {len(in_progress_tasks)}")
    print(f"   • Завершены: {len(completed_tasks)}")

if __name__ == "__main__":
    test_tracker_functions()