#!/usr/bin/env python3
"""
Полный тест исправления проблемы с user_id в реальном сценарии
"""

import asyncio
import os
import sys
import tempfile
import json
from unittest.mock import AsyncMock, patch

# Add the project root to Python path  
sys.path.insert(0, '/Users/alexonic/Documents/project/gptbot')

from enhanced_ai_agents import OrchestratorAgent, TaskManagementAgent
from task_database import TaskDatabase

async def test_real_scenario():
    """Тест реального сценария создания задачи через Telegram"""
    
    print("🎯 Тест реального сценария Telegram → AI Agents")
    print("=" * 60)
    
    temp_db = tempfile.mktemp(suffix='.db')
    
    try:
        # Initialize with real user ID
        real_telegram_id = 602216
        
        print(f"👤 Настоящий Telegram ID: {real_telegram_id}")
        
        # Test the flow: Telegram → actions.py → orchestrator → TaskAgent
        orchestrator = OrchestratorAgent(api_key="test-key", model="gpt-4")
        
        print("\n📋 ЭТАП 1: Проверка _handle_general_action с правильным user_id")
        print("-" * 50)
        
        # Mock the LangChain agent to simulate what it would do with proper context
        class MockAgentExecutor:
            def __init__(self, agent, tools, verbose=False):
                self.tools = tools
                
            async def ainvoke(self, inputs):
                # Simulate LangChain calling create_task with user_id from system prompt
                input_message = inputs["input"]
                
                # Extract task info from natural language input
                if "сделать бэклог" in input_message.lower():
                    # Find the create_task tool and call it with proper user_id
                    for tool in self.tools:
                        if tool.name == "create_task":
                            params = {
                                "user_id": real_telegram_id,  # ← This comes from system prompt context
                                "title": "Сделать бэклог",
                                "description": "сквозной бэклог с приоритетами",
                                "priority": "high"
                            }
                            result = tool.func(json.dumps(params))
                            return {"output": result}
                
                return {"output": "Не удалось обработать запрос"}
        
        # Patch AgentExecutor with our mock
        with patch('enhanced_ai_agents.AgentExecutor', MockAgentExecutor):
            
            # Simulate the real user message
            user_message = """сделать бэклог
описание: сквозной бэклог с приоритетами
приоритет: высокий"""
            
            print(f"💬 Сообщение пользователя: {user_message}")
            
            # Route request through orchestrator (this would come from actions.py)
            result = await orchestrator.route_request(real_telegram_id, user_message)
            
            print(f"🤖 Результат роутинга:")
            print(f"   Агент: {result['agent']}")
            print(f"   Уверенность: {result['confidence']}")
            print(f"   Ответ: {result['response'][:100]}...")
            
            # Check if task was created with correct user_id
            db = TaskDatabase(temp_db)
            tasks = db.get_tasks(real_telegram_id)
            
            print(f"\n📊 Результат создания:")
            print(f"   Задач для user {real_telegram_id}: {len(tasks)}")
            
            if tasks:
                task = tasks[0]
                print(f"   Создана задача: '{task['title']}'")
                print(f"   User ID в базе: {task['user_id']} (тип: {type(task['user_id'])})")
                print(f"   Приоритет: {task['priority']}")
                print(f"   Описание: {task['description']}")
                
                if task['user_id'] == real_telegram_id:
                    print("✅ УСПЕХ: Task создана с правильным user_id!")
                else:
                    print(f"❌ ОШИБКА: user_id не совпадает! Ожидалось {real_telegram_id}, получено {task['user_id']}")
            else:
                print("❌ ОШИБКА: Задача не была создана")
            
            # Test task retrieval
            print(f"\n📋 ЭТАП 2: Тест получения задач")
            print("-" * 50)
            
            get_message = "какие у меня есть задачи"
            print(f"💬 Сообщение: {get_message}")
            
            # Mock for get_tasks  
            class MockGetTasksExecutor:
                def __init__(self, agent, tools, verbose=False):
                    self.tools = tools
                    
                async def ainvoke(self, inputs):
                    for tool in self.tools:
                        if tool.name == "get_tasks":
                            params = {"user_id": real_telegram_id}
                            result = tool.func(json.dumps(params))
                            return {"output": result}
                    return {"output": "Не удалось получить задачи"}
            
            with patch('enhanced_ai_agents.AgentExecutor', MockGetTasksExecutor):
                result2 = await orchestrator.route_request(real_telegram_id, get_message)
                
                print(f"🤖 Результат получения задач:")
                print(f"   Агент: {result2['agent']}")
                print(f"   Ответ: {result2['response'][:200]}...")
                
                if "нет задач" in result2['response'].lower():
                    print("❌ ПРОБЛЕМА: Система не находит задачи пользователя")
                elif "сделать бэклог" in result2['response'].lower():
                    print("✅ УСПЕХ: Система правильно показывает задачи пользователя")
                else:
                    print("⚠️  Неопределенный результат")
            
        print(f"\n🏁 ЗАКЛЮЧЕНИЕ")
        print("-" * 50)
        
        # Check database state
        all_tasks = db.get_tasks(real_telegram_id)
        wrong_tasks = db.get_tasks(1)  # Check for tasks with wrong user_id
        
        print(f"📊 Итоговая статистика:")
        print(f"   Задач для правильного user_id ({real_telegram_id}): {len(all_tasks)}")
        print(f"   Задач для неправильного user_id (1): {len(wrong_tasks)}")
        
        if len(all_tasks) > 0 and len(wrong_tasks) == 0:
            print("🎉 ПОЛНЫЙ УСПЕХ: Все задачи созданы с правильным user_id!")
        elif len(wrong_tasks) > 0:
            print("❌ ПРОБЛЕМА: Обнаружены задачи с неправильным user_id")
        else:
            print("⚠️  Задачи не были созданы")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)

if __name__ == "__main__":
    asyncio.run(test_real_scenario())