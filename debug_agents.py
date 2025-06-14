"""
Отладка проблем с AI-агентами
"""

import asyncio
import sys
import os
sys.path.insert(0, os.getcwd())

from ai_agents import TaskManagerAgent, OrchestratorAgent, get_database

async def debug_task_manager():
    """Отладка TaskManagerAgent"""
    print("🔍 Отладка TaskManagerAgent...")
    
    try:
        api_key = "test_key"
        agent = TaskManagerAgent(api_key)
        user_id = 12345
        
        print(f"Tools: {len(agent.tools)}")
        for tool in agent.tools:
            print(f"  - {tool.name}: {tool.description}")
        
        # Тестируем прямой вызов tools
        print("\n🧪 Тест прямого вызова create_task:")
        import json
        params = json.dumps({
            "user_id": user_id,
            "title": "Тестовая задача",
            "description": "Описание",
            "priority": "high"
        })
        
        result = agent._create_task(params)
        print(f"Результат: {result}")
        
        print("\n🧪 Тест прямого вызова get_tasks:")
        params = json.dumps({"user_id": user_id})
        result = agent._get_tasks(params)
        print(f"Результат: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в debug_task_manager: {e}")
        import traceback
        traceback.print_exc()
        return False

async def debug_orchestrator():
    """Отладка OrchestratorAgent"""
    print("\n🔍 Отладка OrchestratorAgent...")
    
    try:
        api_key = "test_key"
        orchestrator = OrchestratorAgent(api_key)
        user_id = 12345
        
        print("Агенты в оркестраторе:")
        print(f"  - TaskManager: {type(orchestrator.task_manager)}")
        print(f"  - EveningTracker: {type(orchestrator.evening_tracker)}")
        
        # Тест роутинга без реального API вызова
        print("\n🧪 Тест роутинга (симуляция):")
        
        test_messages = [
            "создай задачу купить молоко",
            "сколько у меня задач",
            "покажи мою продуктивность",
            "начинаем вечерний трекер"
        ]
        
        for message in test_messages:
            print(f"Сообщение: '{message}'")
            # Симулируем логику роутинга
            if any(word in message.lower() for word in ['создай', 'задач', 'продуктивность']):
                route = "TASK_MANAGER"
            elif any(word in message.lower() for word in ['вечерний', 'трекер']):
                route = "EVENING_TRACKER"
            else:
                route = "GENERAL"
            print(f"  → Роутинг: {route}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в debug_orchestrator: {e}")
        import traceback
        traceback.print_exc()
        return False

def debug_database():
    """Отладка базы данных"""
    print("\n🔍 Отладка базы данных...")
    
    try:
        db = get_database()
        user_id = 99999
        
        # Тест полного цикла
        print("1. Создание пользователя...")
        db.ensure_user_exists(user_id)
        
        print("2. Создание задач...")
        task_ids = []
        for i, (title, priority) in enumerate([
            ("Задача 1", "high"),
            ("Задача 2", "medium"),
            ("Задача 3", "low")
        ]):
            task_id = db.create_task(user_id, title, f"Описание {i+1}", priority)
            task_ids.append(task_id)
            print(f"   Создана: {title} - {task_id[:8]}...")
        
        print("3. Получение задач...")
        tasks = db.get_tasks(user_id)
        print(f"   Всего задач: {len(tasks)}")
        
        print("4. Обновление статуса...")
        success = db.update_task_status(task_ids[0], user_id, "completed")
        print(f"   Статус обновлен: {success}")
        
        print("5. Аналитика...")
        analytics = db.get_task_analytics(user_id)
        print(f"   Всего: {analytics['total_tasks']}")
        print(f"   Завершено: {analytics['completed_tasks']}")
        print(f"   Процент: {analytics['completion_rate']}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в debug_database: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Основная функция отладки"""
    print("🚀 Отладка системы AI-агентов\n")
    
    results = []
    
    # Отладка компонентов
    results.append(debug_database())
    results.append(await debug_task_manager())
    results.append(await debug_orchestrator())
    
    # Итоги
    passed = sum(results)
    total = len(results)
    print(f"\n📊 Результаты отладки: {passed}/{total}")
    
    if passed == total:
        print("✅ Все компоненты работают корректно!")
    else:
        print("⚠️ Обнаружены проблемы, требующие исправления.")

if __name__ == "__main__":
    asyncio.run(main())