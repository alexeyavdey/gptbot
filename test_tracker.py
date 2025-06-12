import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
import yaml
import sys
from pathlib import Path

# Добавляем текущую директорию в Python path
sys.path.insert(0, str(Path(__file__).parent))

# Мокаем логгер перед импортом
with patch('tracker.create_logger') as mock_logger:
    mock_logger.return_value = MagicMock()
    
    # Тестируем функции трекера
    from tracker import (
        TrackerUserData, TrackerTask, TaskStatus, TaskPriority,
        create_task, get_task_by_id, update_task_status, 
        update_task_priority, delete_task, get_tasks_by_status,
        get_tasks_sorted, format_task_text,
        save_user_data, get_user_data
    )

class TestTrackerFunctions(unittest.TestCase):
    def setUp(self):
        """Настройка для каждого теста"""
        # Создаем временный файл для тестов
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        self.temp_file.close()
        
        # Патчим путь к файлу данных
        self.patcher = patch('tracker.TRACKER_STORAGE', Path(self.temp_file.name))
        self.patcher.start()
        
        # Создаем тестового пользователя
        self.user_data = TrackerUserData(123)
        self.user_data.completed = True  # Пропускаем welcome module
    
    def tearDown(self):
        """Очистка после каждого теста"""
        self.patcher.stop()
        try:
            os.unlink(self.temp_file.name)
        except:
            pass
    
    def test_create_task(self):
        """Тест создания задачи"""
        task = create_task(self.user_data, "Тестовая задача", "Описание", TaskPriority.HIGH)
        
        self.assertEqual(task.title, "Тестовая задача")
        self.assertEqual(task.description, "Описание")
        self.assertEqual(task.priority, TaskPriority.HIGH)
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertEqual(len(self.user_data.tasks), 1)
        self.assertIsNotNone(task.id)
        self.assertIsNotNone(task.created_at)
    
    def test_get_task_by_id(self):
        """Тест поиска задачи по ID"""
        task = create_task(self.user_data, "Тестовая задача")
        
        found_task = get_task_by_id(self.user_data, task.id)
        self.assertEqual(found_task.title, "Тестовая задача")
        
        not_found = get_task_by_id(self.user_data, "non-existent-id")
        self.assertIsNone(not_found)
    
    def test_update_task_status(self):
        """Тест обновления статуса задачи"""
        task = create_task(self.user_data, "Тестовая задача")
        
        # Тест изменения статуса на "в работе"
        result = update_task_status(self.user_data, task.id, TaskStatus.IN_PROGRESS)
        self.assertTrue(result)
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)
        
        # Тест завершения задачи
        result = update_task_status(self.user_data, task.id, TaskStatus.COMPLETED)
        self.assertTrue(result)
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(task.completed_at)
        
        # Тест несуществующей задачи
        result = update_task_status(self.user_data, "non-existent", TaskStatus.COMPLETED)
        self.assertFalse(result)
    
    def test_update_task_priority(self):
        """Тест обновления приоритета задачи"""
        task = create_task(self.user_data, "Тестовая задача")
        original_priority = task.priority
        
        result = update_task_priority(self.user_data, task.id, TaskPriority.URGENT)
        self.assertTrue(result)
        self.assertEqual(task.priority, TaskPriority.URGENT)
        self.assertNotEqual(task.priority, original_priority)
        
        # Тест несуществующей задачи
        result = update_task_priority(self.user_data, "non-existent", TaskPriority.HIGH)
        self.assertFalse(result)
    
    def test_delete_task(self):
        """Тест удаления задачи"""
        task = create_task(self.user_data, "Тестовая задача")
        task_id = task.id
        
        self.assertEqual(len(self.user_data.tasks), 1)
        
        result = delete_task(self.user_data, task_id)
        self.assertTrue(result)
        self.assertEqual(len(self.user_data.tasks), 0)
        
        # Тест повторного удаления
        result = delete_task(self.user_data, task_id)
        self.assertFalse(result)
    
    def test_get_tasks_by_status(self):
        """Тест фильтрации задач по статусу"""
        task1 = create_task(self.user_data, "Задача 1")
        task2 = create_task(self.user_data, "Задача 2")
        task3 = create_task(self.user_data, "Задача 3")
        
        # Изменяем статусы
        update_task_status(self.user_data, task2.id, TaskStatus.IN_PROGRESS)
        update_task_status(self.user_data, task3.id, TaskStatus.COMPLETED)
        
        pending_tasks = get_tasks_by_status(self.user_data, TaskStatus.PENDING)
        in_progress_tasks = get_tasks_by_status(self.user_data, TaskStatus.IN_PROGRESS)
        completed_tasks = get_tasks_by_status(self.user_data, TaskStatus.COMPLETED)
        
        self.assertEqual(len(pending_tasks), 1)
        self.assertEqual(len(in_progress_tasks), 1)
        self.assertEqual(len(completed_tasks), 1)
        self.assertEqual(pending_tasks[0].title, "Задача 1")
        self.assertEqual(in_progress_tasks[0].title, "Задача 2")
        self.assertEqual(completed_tasks[0].title, "Задача 3")
    
    def test_get_tasks_sorted(self):
        """Тест сортировки задач"""
        task1 = create_task(self.user_data, "Низкий приоритет", "", TaskPriority.LOW)
        task2 = create_task(self.user_data, "Высокий приоритет", "", TaskPriority.HIGH)
        task3 = create_task(self.user_data, "Срочная задача", "", TaskPriority.URGENT)
        
        # Сортировка по приоритету
        sorted_tasks = get_tasks_sorted(self.user_data, "priority")
        self.assertEqual(sorted_tasks[0].title, "Срочная задача")
        self.assertEqual(sorted_tasks[1].title, "Высокий приоритет")
        self.assertEqual(sorted_tasks[2].title, "Низкий приоритет")
        
        # Сортировка по дате создания (по умолчанию)
        sorted_by_date = get_tasks_sorted(self.user_data, "created_at")
        self.assertEqual(len(sorted_by_date), 3)
    
    def test_format_task_text(self):
        """Тест форматирования текста задачи"""
        task = create_task(self.user_data, "Тестовая задача", "Описание задачи", TaskPriority.HIGH)
        
        # Краткий формат
        short_text = format_task_text(task, show_details=False)
        self.assertIn("Тестовая задача", short_text)
        self.assertIn("⏳", short_text)  # Emoji для pending статуса
        
        # Подробный формат
        detailed_text = format_task_text(task, show_details=True)
        self.assertIn("Тестовая задача", detailed_text)
        self.assertIn("Описание задачи", detailed_text)
        self.assertIn("🟠 Высокий", detailed_text)  # Приоритет
        self.assertIn("Создана:", detailed_text)
    
    def test_data_persistence(self):
        """Тест сохранения и загрузки данных"""
        # Создаем задачи
        task1 = create_task(self.user_data, "Задача 1", "Описание 1", TaskPriority.HIGH)
        task2 = create_task(self.user_data, "Задача 2", "Описание 2", TaskPriority.LOW)
        update_task_status(self.user_data, task1.id, TaskStatus.IN_PROGRESS)
        
        # Сохраняем данные
        save_user_data(self.user_data)
        
        # Загружаем данные в новый объект
        loaded_user_data = get_user_data(123)
        
        self.assertEqual(len(loaded_user_data.tasks), 2)
        self.assertEqual(loaded_user_data.tasks[0].title, "Задача 1")
        self.assertEqual(loaded_user_data.tasks[0].status, TaskStatus.IN_PROGRESS)
        self.assertEqual(loaded_user_data.tasks[0].priority, TaskPriority.HIGH)
        self.assertEqual(loaded_user_data.tasks[1].title, "Задача 2")
        self.assertEqual(loaded_user_data.tasks[1].priority, TaskPriority.LOW)

if __name__ == '__main__':
    unittest.main()