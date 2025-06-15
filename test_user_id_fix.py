#!/usr/bin/env python3
"""
Тест исправления проблемы с user_id
"""

import asyncio
import os
import sys
import tempfile
import json

# Add the project root to Python path  
sys.path.insert(0, '/Users/alexonic/Documents/project/gptbot')

from enhanced_ai_agents import TaskManagementAgent, OrchestratorAgent
from task_database import TaskDatabase

async def test_user_id_handling():
    """Тест правильной передачи user_id через всю систему"""
    
    print("🧪 Тестирование передачи user_id")
    print("=" * 60)
    
    temp_db = tempfile.mktemp(suffix='.db')
    
    try:
        # Initialize
        db = TaskDatabase(temp_db)
        orchestrator = OrchestratorAgent(api_key="test-key", model="gpt-4")
        
        # Real Telegram user ID
        real_user_id = 602216
        
        print(f"🆔 Тестовый user_id: {real_user_id} (тип: {type(real_user_id)})")
        
        # Test 1: Direct database operations
        print("\n📊 ТЕСТ 1: Прямые операции с базой")
        print("-" * 40)
        
        success = db.ensure_user_exists(real_user_id)
        print(f"✅ ensure_user_exists: {success}")
        
        task_id = db.create_task(
            user_id=real_user_id,
            title="Тестовая задача",
            description="Проверка user_id", 
            priority="medium"
        )
        print(f"✅ Создана задача: {task_id}")
        
        tasks = db.get_tasks(real_user_id)
        print(f"📋 Найдено задач: {len(tasks)}")
        if tasks:
            print(f"   Первая задача user_id: {tasks[0]['user_id']} (тип: {type(tasks[0]['user_id'])})")
        
        # Test 2: TaskManagementAgent direct call
        print("\n📊 ТЕСТ 2: TaskManagementAgent напрямую")
        print("-" * 40)
        
        task_agent = TaskManagementAgent(api_key="test-key", model="gpt-4")
        
        # Test the _create_task method directly
        create_params = json.dumps({
            "user_id": real_user_id,
            "title": "Прямой вызов агента",
            "description": "Тест прямого вызова",
            "priority": "high"
        })
        
        result = task_agent._create_task(create_params)
        print(f"🔧 Результат _create_task: {result[:100]}...")
        
        # Test get_tasks
        get_params = json.dumps({"user_id": real_user_id})
        result = task_agent._get_tasks(get_params)
        print(f"📋 Результат _get_tasks: {result[:100]}...")
        
        # Test 3: Check what LangChain might be doing
        print("\n📊 ТЕСТ 3: Симуляция LangChain вызова")
        print("-" * 40)
        
        # Simulate what LangChain might pass to _create_task
        possible_bad_params = [
            '{"user_id": "user_1", "title": "Bad test"}',  # String user_id
            '{"user_id": "602216", "title": "String ID test"}',  # String number
            '{"title": "No user_id test"}',  # Missing user_id
        ]
        
        for bad_params in possible_bad_params:
            print(f"🧪 Тестируем плохие параметры: {bad_params}")
            try:
                result = task_agent._create_task(bad_params)
                print(f"   Результат: {result[:80]}...")
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
        
        # Test 4: Check orchestrator flow (without real LLM)
        print("\n📊 ТЕСТ 4: Проверка потока через оркестратор")
        print("-" * 40)
        
        # Check user state retrieval 
        user_state = await orchestrator._get_user_state(real_user_id)
        print(f"👤 User state для {real_user_id}: {user_state}")
        
        # Final verification
        print("\n📊 ФИНАЛЬНАЯ ПРОВЕРКА")
        print("-" * 40)
        
        final_tasks = db.get_tasks(real_user_id)
        print(f"📋 Итоговое количество задач для user {real_user_id}: {len(final_tasks)}")
        
        for i, task in enumerate(final_tasks, 1):
            print(f"   {i}. {task['title']} (user_id: {task['user_id']}, тип: {type(task['user_id'])})")
            
        # Check for wrong user_id
        wrong_tasks = db.get_tasks(1)  # user_1 would be stored as 1
        print(f"📋 Задач для неправильного user_id=1: {len(wrong_tasks)}")
        
        if wrong_tasks:
            print("⚠️  ОБНАРУЖЕНА ПРОБЛЕМА: Есть задачи с неправильным user_id!")
            for task in wrong_tasks:
                print(f"   - {task['title']} (user_id: {task['user_id']})")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)

if __name__ == "__main__":
    asyncio.run(test_user_id_handling())