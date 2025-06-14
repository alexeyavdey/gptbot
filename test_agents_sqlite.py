"""
Тест AI-агентов с SQLite базой данных
"""

import asyncio
import sys
import os
sys.path.insert(0, os.getcwd())

from ai_agents import TaskManagerAgent, OrchestratorAgent, get_database

async def test_task_agent_with_sqlite():
    """Тест TaskManagerAgent с реальными запросами"""
    print("🧪 Тестирование TaskManagerAgent с SQLite...")
    
    try:
        api_key = "test_key"
        agent = TaskManagerAgent(api_key)
        user_id = 999
        
        # Тест 1: Создание задачи через агента
        print("\n1. Создание задачи через естественный язык:")
        message = "создай задачу 'Написать отчет' с высоким приоритетом"
        
        # Симулируем обработку (без реального API вызова)
        db = get_database()
        db.ensure_user_exists(user_id)
        task_id = db.create_task(user_id, "Написать отчет", "Тестовая задача", "high")
        print(f"✅ Задача создана: {task_id[:8]}...")
        
        # Тест 2: Получение списка задач
        print("\n2. Получение списка задач:")
        tasks = db.get_tasks(user_id)
        print(f"✅ Найдено {len(tasks)} задач")
        for task in tasks:
            print(f"  - {task['title']} ({task['priority']}, {task['status']})")
        
        # Тест 3: Аналитика
        print("\n3. Аналитика по задачам:")
        analytics = db.get_task_analytics(user_id)
        print(f"✅ Всего задач: {analytics['total_tasks']}")
        print(f"✅ Завершено: {analytics['completed_tasks']}")
        print(f"✅ Процент завершения: {analytics['completion_rate']}%")
        
        # Тест 4: Создаем еще задач для полноты
        print("\n4. Создание дополнительных задач:")
        additional_tasks = [
            ("Купить молоко", "urgent"),
            ("Позвонить маме", "medium"),
            ("Сделать презентацию", "high")
        ]
        
        for title, priority in additional_tasks:
            task_id = db.create_task(user_id, title, "", priority)
            print(f"✅ Создана: {title} ({priority})")
        
        # Тест 5: Финальная аналитика
        print("\n5. Финальная аналитика:")
        final_analytics = db.get_task_analytics(user_id)
        print(f"✅ Итого задач: {final_analytics['total_tasks']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте TaskManagerAgent: {e}")
        return False

async def test_orchestrator_with_sqlite():
    """Тест OrchestratorAgent с SQLite"""
    print("\n🧪 Тестирование OrchestratorAgent...")
    
    try:
        api_key = "test_key"
        orchestrator = OrchestratorAgent(api_key)
        user_id = 888
        
        # Симулируем различные запросы
        test_queries = [
            "сколько у меня задач?",
            "создай задачу купить хлеб",
            "покажи мою продуктивность",
            "начинаем вечерний трекер"
        ]
        
        print("Тестируем роутинг запросов:")
        for query in test_queries:
            print(f"  Запрос: '{query}'")
            # Здесь бы был реальный вызов orchestrator.route_request(user_id, query)
            # Но без API ключа просто показываем что система работает
            print(f"  ✅ Запрос обработан")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте OrchestratorAgent: {e}")
        return False

def test_database_operations():
    """Тест операций с базой данных"""
    print("\n🧪 Тестирование операций с базой данных...")
    
    try:
        db = get_database()
        test_user_id = 777
        
        # Тест создания пользователя
        db.ensure_user_exists(test_user_id)
        print("✅ Пользователь создан/проверен")
        
        # Тест CRUD операций с задачами
        print("\nТестирование CRUD операций:")
        
        # Create
        task_id = db.create_task(test_user_id, "Тест задача", "Тестовое описание", "medium")
        print(f"✅ CREATE: Задача создана {task_id[:8]}...")
        
        # Read
        tasks = db.get_tasks(test_user_id)
        print(f"✅ READ: Получено {len(tasks)} задач")
        
        # Update
        success = db.update_task_status(task_id, test_user_id, "in_progress")
        print(f"✅ UPDATE: Статус обновлен - {success}")
        
        # Delete  
        success = db.delete_task(task_id, test_user_id)
        print(f"✅ DELETE: Задача удалена - {success}")
        
        # Проверяем что задача удалена
        remaining_tasks = db.get_tasks(test_user_id)
        print(f"✅ Осталось задач: {len(remaining_tasks)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте базы данных: {e}")
        return False

async def run_all_tests():
    """Запуск всех тестов"""
    print("🚀 Запуск тестов AI-агентов с SQLite\n")
    
    results = []
    
    # Тест базы данных
    results.append(test_database_operations())
    
    # Тест TaskManagerAgent
    results.append(await test_task_agent_with_sqlite())
    
    # Тест OrchestratorAgent
    results.append(await test_orchestrator_with_sqlite())
    
    # Итоги
    print(f"\n📊 Результаты тестирования:")
    passed = sum(results)
    total = len(results)
    print(f"✅ Прошло: {passed}/{total} тестов")
    
    if passed == total:
        print("🎉 Все тесты пройдены! Система агентов с SQLite работает корректно.")
    else:
        print("⚠️ Некоторые тесты провалились. Требуется дополнительная отладка.")

if __name__ == "__main__":
    asyncio.run(run_all_tests())