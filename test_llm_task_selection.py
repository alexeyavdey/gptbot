#!/usr/bin/env python3
"""
Тест нового алгоритма удаления задач с TaskSelectorAgent
"""

import asyncio
import os
import sys
import tempfile
import json

# Add the project root to Python path  
sys.path.insert(0, '/Users/alexonic/Documents/project/gptbot')

from enhanced_ai_agents import TaskSelectorAgent, TaskManagementAgent
from task_database import TaskDatabase

async def test_task_selector_agent():
    """Тест TaskSelectorAgent для анализа намерений"""
    
    print("🧪 Тестирование TaskSelectorAgent")
    print("=" * 60)
    
    temp_db = tempfile.mktemp(suffix='.db')
    
    try:
        # Initialize
        db = TaskDatabase(temp_db)
        api_key = os.getenv('API_KEY') or 'test-key'
        selector = TaskSelectorAgent(api_key=api_key, model="gpt-4")
        
        user_id = 123456
        
        # Create test tasks
        db.ensure_user_exists(user_id)
        
        test_tasks = [
            {"title": "Стратегия сайта Банка — презентация для Влада", "description": "Подготовить презентацию", "priority": "high", "status": "pending"},
            {"title": "Стратегия маркетинга на Q2", "description": "План маркетинга", "priority": "medium", "status": "pending"},
            {"title": "Купить молоко", "description": "Сходить в магазин", "priority": "low", "status": "pending"},
            {"title": "Встреча с клиентом", "description": "Обсудить проект", "priority": "high", "status": "in_progress"}
        ]
        
        tasks_with_ids = []
        for task_data in test_tasks:
            task_id = db.create_task(
                user_id=user_id,
                title=task_data["title"],
                description=task_data["description"], 
                priority=task_data["priority"]
            )
            task_data['id'] = task_id
            tasks_with_ids.append(task_data)
            print(f"   ✅ Создана: {task_data['title']}")
        
        print(f"\n📊 Всего задач: {len(tasks_with_ids)}")
        
        # Test scenarios
        test_scenarios = [
            {
                "name": "Удаление задачи по частичному названию",
                "message": "удали задачу про стратегию",
                "conversation_history": []
            },
            {
                "name": "Удаление конкретной задачи",
                "message": "удали задачу стратегия банка",
                "conversation_history": []
            },
            {
                "name": "Удаление с контекстом",
                "message": "давай её удалим",
                "conversation_history": [
                    {"role": "user", "content": "покажи задачу про презентацию"},
                    {"role": "assistant", "content": "Стратегия сайта Банка — презентация для Влада"}
                ]
            },
            {
                "name": "Просмотр задач",
                "message": "покажи мои задачи",
                "conversation_history": []
            },
            {
                "name": "Создание задачи",
                "message": "создай задачу написать отчет",
                "conversation_history": []
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n" + "="*60)
            print(f"ТЕСТ {i}: {scenario['name']}")
            print("="*60)
            print(f"👤 Пользователь: {scenario['message']}")
            
            # Analyze intent
            result = await selector.analyze_user_intent(
                user_message=scenario['message'],
                tasks=tasks_with_ids,
                conversation_history=scenario['conversation_history']
            )
            
            print(f"🤖 Анализ намерения:")
            print(f"   Действие: {result.get('action', 'unknown')}")
            print(f"   Выбранные задачи: {len(result.get('selected_tasks', []))}")
            print(f"   Требует подтверждения: {result.get('requires_confirmation', True)}")
            
            if result.get('selected_tasks'):
                print(f"   🎯 Найденные задачи:")
                for task in result['selected_tasks']:
                    print(f"     • {task.get('title', 'Неизвестно')} (уверенность: {task.get('confidence', 0):.2f})")
                    print(f"       Обоснование: {task.get('reasoning', 'Не указано')}")
            
            if result.get('suggested_response'):
                print(f"   💬 Предлагаемый ответ: {result['suggested_response'][:100]}...")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)

async def test_full_integration():
    """Тест полной интеграции TaskManagementAgent с TaskSelectorAgent"""
    
    print("\n\n🎯 Тестирование полной интеграции")
    print("=" * 60)
    
    temp_db = tempfile.mktemp(suffix='.db')
    
    try:
        # Initialize
        db = TaskDatabase(temp_db)
        api_key = os.getenv('API_KEY') or 'test-key'
        task_agent = TaskManagementAgent(api_key=api_key, model="gpt-4")
        task_agent.db = db  # Set database
        
        user_id = 123456
        
        # Create test task
        db.ensure_user_exists(user_id)
        task_id = db.create_task(
            user_id=user_id,
            title="Стратегия сайта Банка — презентация для Влада",
            description="Подготовить презентацию для Влада", 
            priority="high"
        )
        
        print(f"✅ Создана тестовая задача: {task_id}")
        
        # Test deletion workflow
        print("\n📋 СЦЕНАРИЙ: Удаление задачи через LLM анализ")
        print("-" * 60)
        
        # Step 1: User asks to delete task
        message1 = "удали задачу про стратегию"
        print(f"👤 Пользователь: {message1}")
        
        context = {
            "conversation_history": []
        }
        
        response1 = await task_agent.process_message(user_id, message1, context)
        print(f"🤖 Бот: {response1}")
        
        # Check if it requires confirmation
        if "подтверждение" in response1.lower() or "действительно" in response1.lower():
            print("\n✅ LLM правильно определил задачу и запросил подтверждение")
            
            # Extract task_id from response
            import re
            uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
            task_ids = re.findall(uuid_pattern, response1.lower())
            
            if task_ids:
                extracted_task_id = task_ids[0]
                print(f"🔍 Извлечен task_id: {extracted_task_id}")
                
                # Step 2: User confirms
                message2 = "да, подтверждаю"
                print(f"\n👤 Пользователь: {message2}")
                
                context2 = {
                    "task_id": extracted_task_id,
                    "conversation_history": [
                        {"role": "user", "content": message1},
                        {"role": "assistant", "content": response1}
                    ]
                }
                
                response2 = await task_agent.process_message(user_id, message2, context2)
                print(f"🤖 Бот: {response2}")
                
                # Check final state
                final_tasks = db.get_tasks(user_id)
                
                if len(final_tasks) == 0:
                    print("\n🎉 УСПЕХ! Новый алгоритм с LLM анализом работает!")
                    print("✅ TaskSelectorAgent правильно определил намерение")
                    print("✅ TaskManagementAgent выполнил удаление с подтверждением")
                else:
                    print("\n❌ Ошибка: задача не была удалена")
            else:
                print("❌ Не удалось извлечь task_id из ответа")
        else:
            print("❌ LLM не запросил подтверждение удаления")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)

if __name__ == "__main__":
    asyncio.run(test_task_selector_agent())
    asyncio.run(test_full_integration())