#!/usr/bin/env python3
"""
Тест исправления ошибки удаления задач
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

async def test_deletion_confirmation_flow():
    """Тест полного потока удаления с подтверждением"""
    
    print("🧪 Тестирование исправления ошибки удаления")
    print("=" * 60)
    
    temp_db = tempfile.mktemp(suffix='.db')
    
    try:
        # Initialize
        db = TaskDatabase(temp_db)
        orchestrator = OrchestratorAgent(api_key="mock-key", model="gpt-4")
        
        user_id = 123456
        
        # Create test task
        db.ensure_user_exists(user_id)
        task_id = db.create_task(
            user_id=user_id,
            title="Стратегия сайта Банка — презентация для Влада",
            description="Подготовить презентацию", 
            priority="high"
        )
        
        print(f"✅ Создана задача: {task_id}")
        
        # Mock the task selector to simulate finding the task
        mock_analysis_step1 = {
            "action": "delete",
            "selected_tasks": [
                {
                    "task_id": task_id,
                    "title": "Стратегия сайта Банка — презентация для Влада",
                    "confidence": 0.95,
                    "reasoning": "Точное совпадение по названию"
                }
            ],
            "requires_confirmation": True,
            "suggested_response": "Найдена задача для удаления с подтверждением"
        }
        
        mock_analysis_step2 = {
            "action": "delete", 
            "selected_tasks": [
                {
                    "task_id": task_id,
                    "title": "Стратегия сайта Банка — презентация для Влада",
                    "confidence": 1.0,
                    "reasoning": "Подтверждение удаления из контекста"
                }
            ],
            "requires_confirmation": False,  # Уже подтверждено
            "suggested_response": "Выполняем удаление"
        }
        
        print("\n📋 ЭТАП 1: Запрос удаления")
        print("-" * 40)
        
        # Patch the task selector
        with patch.object(orchestrator.task_agent.task_selector, 'analyze_user_intent', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_analysis_step1
            
            # Step 1: Request deletion
            message1 = "удали задачу Стратегия сайта Банка — презентация для Влада (в процессе)"
            print(f"👤 Пользователь: {message1}")
            
            result1 = await orchestrator.route_request(user_id, message1)
            print(f"🤖 Бот: {result1['response'][:100]}...")
            
            print(f"🔍 Результат роутинга:")
            print(f"   Агент: {result1['agent']}")
            print(f"   Уверенность: {result1['confidence']}")
            
            # Verify tasks still exist
            tasks_after_step1 = db.get_tasks(user_id)
            print(f"📊 Задач после запроса: {len(tasks_after_step1)}")
            
            if "подтверждение" in result1['response'].lower():
                print("✅ Система правильно запросила подтверждение")
            else:
                print("❌ Система не запросила подтверждение")
        
        print("\n📋 ЭТАП 2: Подтверждение удаления")
        print("-" * 40)
        
        # Step 2: Confirm deletion
        with patch.object(orchestrator.task_agent.task_selector, 'analyze_user_intent', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_analysis_step2
            
            message2 = "да"
            print(f"👤 Пользователь: {message2}")
            
            # Check if it's detected as confirmation
            is_confirmation = orchestrator._is_deletion_confirmation(message2)
            print(f"🔍 Обнаружено как подтверждение: {is_confirmation}")
            
            # Extract task_id (should be None for simple "да")
            extracted_id = orchestrator._extract_task_id_from_message(message2)
            print(f"🔍 Извлечен task_id: {extracted_id}")
            
            result2 = await orchestrator.route_request(user_id, message2)
            print(f"🤖 Бот: {result2['response'][:100]}...")
            
            print(f"🔍 Результат роутинга:")
            print(f"   Агент: {result2['agent']}")
            print(f"   Уверенность: {result2['confidence']}")
            print(f"   Логика: {result2['reasoning']}")
            
            # Check final state
            tasks_after_step2 = db.get_tasks(user_id)
            print(f"📊 Задач после подтверждения: {len(tasks_after_step2)}")
            
            if len(tasks_after_step2) == 0:
                print("🎉 УСПЕХ! Задача успешно удалена после подтверждения")
            elif "удалена" in result2['response'].lower():
                print("✅ Система сообщила об удалении (проверим базу)")
                if len(tasks_after_step2) == 0:
                    print("🎉 ПОДТВЕРЖДЕНО: Задача действительно удалена")
                else:
                    print("❌ Задача НЕ удалена, несмотря на сообщение")
            else:
                print("❌ Задача не была удалена")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)

if __name__ == "__main__":
    asyncio.run(test_deletion_confirmation_flow())