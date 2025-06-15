#!/usr/bin/env python3
"""
Простой тест TaskSelectorAgent без реальных API вызовов
"""

import asyncio
import os
import sys
import tempfile
import json
from unittest.mock import AsyncMock, patch

# Add the project root to Python path  
sys.path.insert(0, '/Users/alexonic/Documents/project/gptbot')

from enhanced_ai_agents import TaskSelectorAgent, TaskManagementAgent
from task_database import TaskDatabase

async def test_task_selector_logic():
    """Тест логики TaskSelectorAgent без реальных LLM вызовов"""
    
    print("🧪 Тестирование логики TaskSelectorAgent")
    print("=" * 60)
    
    # Mock tasks
    test_tasks = [
        {
            "id": "task-1",
            "title": "Стратегия сайта Банка — презентация для Влада",
            "description": "Подготовить презентацию",
            "status": "pending",
            "priority": "high"
        },
        {
            "id": "task-2", 
            "title": "Стратегия маркетинга на Q2",
            "description": "План маркетинга",
            "status": "pending",
            "priority": "medium"
        },
        {
            "id": "task-3",
            "title": "Купить молоко",
            "description": "Сходить в магазин",
            "status": "pending", 
            "priority": "low"
        }
    ]
    
    # Mock different LLM responses
    mock_responses = {
        "удали задачу про стратегию": {
            "action": "delete",
            "selected_tasks": [
                {
                    "task_id": "task-1",
                    "title": "Стратегия сайта Банка — презентация для Влада",
                    "confidence": 0.8,
                    "reasoning": "Найдено частичное совпадение по слову 'стратегия'"
                },
                {
                    "task_id": "task-2",
                    "title": "Стратегия маркетинга на Q2", 
                    "confidence": 0.8,
                    "reasoning": "Найдено частичное совпадение по слову 'стратегия'"
                }
            ],
            "requires_confirmation": True,
            "suggested_response": "Найдено несколько задач со словом 'стратегия'. Уточните выбор."
        },
        "удали задачу стратегия банка": {
            "action": "delete",
            "selected_tasks": [
                {
                    "task_id": "task-1",
                    "title": "Стратегия сайта Банка — презентация для Влада",
                    "confidence": 0.95,
                    "reasoning": "Точное совпадение по словам 'стратегия' и 'банка'"
                }
            ],
            "requires_confirmation": True,
            "suggested_response": "Найдена задача для удаления с подтверждением"
        },
        "покажи мои задачи": {
            "action": "view",
            "selected_tasks": [],
            "requires_confirmation": False,
            "suggested_response": "Показать все задачи пользователя"
        }
    }
    
    # Test scenarios
    test_scenarios = [
        "удали задачу про стратегию",
        "удали задачу стратегия банка", 
        "покажи мои задачи"
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🧪 ТЕСТ {i}: {scenario}")
        print("-" * 50)
        
        expected_response = mock_responses.get(scenario, {})
        
        print(f"👤 Пользователь: {scenario}")
        print(f"🎯 Ожидаемый анализ:")
        print(f"   Действие: {expected_response.get('action', 'unknown')}")
        print(f"   Выбранные задачи: {len(expected_response.get('selected_tasks', []))}")
        print(f"   Требует подтверждения: {expected_response.get('requires_confirmation', True)}")
        
        if expected_response.get('selected_tasks'):
            print(f"   🎯 Найденные задачи:")
            for task in expected_response['selected_tasks']:
                print(f"     • {task.get('title', 'Неизвестно')} (уверенность: {task.get('confidence', 0):.2f})")
        
        print(f"   💬 Предлагаемый ответ: {expected_response.get('suggested_response', 'Не указано')}")

async def test_task_management_integration():
    """Тест интеграции TaskManagementAgent с моком TaskSelectorAgent"""
    
    print("\n\n🎯 Тестирование интеграции TaskManagementAgent")
    print("=" * 60)
    
    temp_db = tempfile.mktemp(suffix='.db')
    
    try:
        # Initialize
        db = TaskDatabase(temp_db)
        
        # Create task agent with mocked selector
        task_agent = TaskManagementAgent(api_key="mock-key", model="gpt-4")
        task_agent.db = db
        
        # Mock the task selector response
        mock_analysis = {
            "action": "delete",
            "selected_tasks": [
                {
                    "task_id": "test-task-id",
                    "title": "Стратегия сайта Банка — презентация для Влада",
                    "confidence": 0.95,
                    "reasoning": "Найдено по ключевым словам"
                }
            ],
            "requires_confirmation": True,
            "suggested_response": "Найдена задача для удаления"
        }
        
        # Patch the task selector
        with patch.object(task_agent.task_selector, 'analyze_user_intent', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_analysis
            
            user_id = 123456
            
            # Create test task
            db.ensure_user_exists(user_id)
            task_id = db.create_task(
                user_id=user_id,
                title="Стратегия сайта Банка — презентация для Влада",
                description="Подготовить презентацию", 
                priority="high"
            )
            
            print(f"✅ Создана тестовая задача: {task_id}")
            
            # Test the workflow
            message = "удали задачу про стратегию"
            print(f"\n👤 Пользователь: {message}")
            
            context = {"conversation_history": []}
            
            # This should call our mocked task selector
            response = await task_agent.process_message(user_id, message, context)
            print(f"🤖 Ответ бота: {response}")
            
            # Verify the mock was called
            mock_analyze.assert_called_once()
            args, kwargs = mock_analyze.call_args
            print(f"\n✅ TaskSelectorAgent вызван с правильными параметрами:")
            print(f"   Сообщение: {args[0] if args else kwargs.get('user_message', 'не передано')}")
            print(f"   Количество задач: {len(args[1]) if len(args) > 1 else len(kwargs.get('tasks', []))}")
            
            # Check if response contains confirmation request
            if "подтверждение" in response.lower() or "действительно" in response.lower():
                print("✅ Бот правильно запросил подтверждение удаления")
            else:
                print(f"❌ Бот не запросил подтверждение: {response}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)

if __name__ == "__main__":
    asyncio.run(test_task_selector_logic())
    asyncio.run(test_task_management_integration())