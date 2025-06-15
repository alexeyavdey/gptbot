#!/usr/bin/env python3
"""
Тест нового интерактивного алгоритма удаления задач
"""

import asyncio
import os
import sys
import tempfile
import json

# Add the project root to Python path  
sys.path.insert(0, '/Users/alexonic/Documents/project/gptbot')

from enhanced_ai_agents import TaskManagementAgent
from task_database import TaskDatabase

async def test_interactive_deletion_algorithm():
    """Тест нового интерактивного алгоритма удаления"""
    
    print("🧪 Тестирование интерактивного алгоритма удаления")
    print("=" * 60)
    
    # Create temporary database for testing
    temp_db = tempfile.mktemp(suffix='.db')
    
    try:
        # Initialize database 
        db = TaskDatabase(temp_db)
        
        # Initialize task management agent directly
        api_key = os.getenv('API_KEY') or 'test-key'
        task_agent = TaskManagementAgent(api_key=api_key, model="gpt-4")
        task_agent.db = db  # Set the database
        
        user_id = 123456  # Test user ID
        
        print("1. Создаем несколько тестовых задач...")
        
        # Create multiple test tasks
        db.ensure_user_exists(user_id)
        
        tasks_data = [
            {"title": "Стратегия сайта Банка — презентация для Влада", "description": "Подготовить презентацию", "priority": "high"},
            {"title": "Стратегия маркетинга на Q2", "description": "План маркетинга", "priority": "medium"},
            {"title": "Купить молоко", "description": "Сходить в магазин", "priority": "low"},
            {"title": "Стратегия развития продукта", "description": "Дорожная карта", "priority": "high"}
        ]
        
        created_tasks = []
        for task_data in tasks_data:
            task_id = db.create_task(
                user_id=user_id,
                title=task_data["title"],
                description=task_data["description"], 
                priority=task_data["priority"]
            )
            created_tasks.append(task_id)
            print(f"   ✅ Создана: {task_data['title']}")
        
        # Verify tasks were created
        tasks = db.get_tasks(user_id)
        print(f"\n📊 Всего задач в базе: {len(tasks)}")
        
        print("\n" + "="*60)
        print("2. ЭТАП 1 - Запрос удаления по поисковому тексту")
        print("="*60)
        
        # Simulate user asking to delete task with search text
        delete_params = json.dumps({
            "user_id": user_id,
            "search_text": "стратегия"  # Should find multiple tasks
        })
        
        step1_result = task_agent._delete_task(delete_params)
        print("👤 Пользователь: 'удали задачу про стратегию'")
        print(f"🤖 Бот:\n{step1_result}")
        
        print("\n" + "="*60)
        print("3. ЭТАП 2 - Более точный поиск")
        print("="*60)
        
        # User narrows down the search
        delete_params2 = json.dumps({
            "user_id": user_id,
            "search_text": "стратегия банка"  # Should find one specific task
        })
        
        step2_result = task_agent._delete_task(delete_params2)
        print("👤 Пользователь: 'удали задачу стратегия банка'")
        print(f"🤖 Бот:\n{step2_result}")
        
        # Extract task ID from the response for confirmation
        import re
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        task_ids = re.findall(uuid_pattern, step2_result.lower())
        
        if task_ids:
            task_id_to_delete = task_ids[0]
            print(f"\n🔍 Извлечен ID задачи для удаления: {task_id_to_delete}")
            
            print("\n" + "="*60)
            print("4. ЭТАП 3 - Подтверждение удаления")
            print("="*60)
            
            # User confirms deletion
            confirm_params = json.dumps({
                "user_id": user_id,
                "task_id": task_id_to_delete
            })
            
            step3_result = task_agent._delete_task(confirm_params)
            print("👤 Пользователь: 'да, подтверждаю удаление'")
            print(f"🤖 Бот:\n{step3_result}")
            
            # Check final state
            final_tasks = db.get_tasks(user_id)
            print(f"\n📊 Задач после удаления: {len(final_tasks)}")
            
            if len(final_tasks) == len(tasks) - 1:
                print("✅ УСПЕХ: Интерактивный алгоритм удаления работает!")
                print("✅ Задача удалена после подтверждения")
                
                print("\n📋 Оставшиеся задачи:")
                for task in final_tasks:
                    print(f"   • {task['title']}")
            else:
                print("❌ Ошибка: Неожиданное количество задач после удаления")
        else:
            print("❌ Не удалось извлечь ID задачи из ответа бота")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        if os.path.exists(temp_db):
            os.remove(temp_db)

async def test_single_task_deletion():
    """Тест удаления единственной найденной задачи"""
    
    print("\n\n🧪 Тестирование удаления единственной найденной задачи")
    print("=" * 60)
    
    temp_db = tempfile.mktemp(suffix='.db')
    
    try:
        db = TaskDatabase(temp_db)
        api_key = os.getenv('API_KEY') or 'test-key'
        task_agent = TaskManagementAgent(api_key=api_key, model="gpt-4")
        task_agent.db = db
        
        user_id = 123456
        
        # Create one unique task
        db.ensure_user_exists(user_id)
        task_id = db.create_task(
            user_id=user_id,
            title="Уникальная задача про молоко",
            description="Сходить в магазин", 
            priority="low"
        )
        
        print("✅ Создана уникальная задача")
        
        # Search for this unique task
        delete_params = json.dumps({
            "user_id": user_id,
            "search_text": "молоко"
        })
        
        result = task_agent._delete_task(delete_params)
        print("👤 Пользователь: 'удали задачу про молоко'")
        print(f"🤖 Бот:\n{result}")
        
        # Check if it shows confirmation request (not immediate deletion)
        if "подтверждение" in result.lower() or "действительно" in result.lower():
            print("✅ УСПЕХ: Бот запрашивает подтверждение для единственной задачи")
        else:
            print("❌ Ошибка: Бот не запросил подтверждение")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)

if __name__ == "__main__":
    asyncio.run(test_interactive_deletion_algorithm())
    asyncio.run(test_single_task_deletion())