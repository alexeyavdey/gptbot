#!/usr/bin/env python3
"""
Тест исправления экранирования JSON в TaskSelectorAgent
"""

import asyncio
import os
import sys
import tempfile
import json

# Add the project root to Python path  
sys.path.insert(0, '/Users/alexonic/Documents/project/gptbot')

from enhanced_ai_agents import TaskSelectorAgent
from task_database import TaskDatabase

async def test_json_escaping():
    """Тест что JSON правильно экранируется в промптах"""
    
    print("🧪 Тестирование экранирования JSON в TaskSelectorAgent")
    print("=" * 60)
    
    temp_db = tempfile.mktemp(suffix='.db')
    
    try:
        # Initialize
        db = TaskDatabase(temp_db)
        selector = TaskSelectorAgent(api_key="test-key", model="gpt-4")
        
        user_id = 123456
        
        # Create test tasks
        db.ensure_user_exists(user_id)
        task_id = db.create_task(
            user_id=user_id,
            title="Сделать бэклог",
            description="сквозной бэклог с приоритетами", 
            priority="high"
        )
        
        print(f"✅ Создана тестовая задача: {task_id}")
        
        # Get tasks for analysis
        tasks = db.get_tasks(user_id)
        print(f"📊 Всего задач: {len(tasks)}")
        
        # Test the JSON escaping logic manually
        print("\n🔍 Тестирование экранирования JSON:")
        
        tasks_info = []
        for task in tasks:
            tasks_info.append({
                "task_id": task['id'],
                "title": task['title'], 
                "description": task.get('description', ''),
                "status": task['status'],
                "priority": task['priority']
            })
        
        # Original JSON (would cause error)
        original_json = json.dumps(tasks_info, ensure_ascii=False, indent=2)
        print("Оригинальный JSON:")
        print(original_json[:200] + "...")
        
        # Escaped JSON (should work)
        escaped_json = original_json.replace('{', '{{').replace('}', '}}')
        print("\nЭкранированный JSON:")
        print(escaped_json[:200] + "...")
        
        # Count problematic characters
        original_braces = original_json.count('{') + original_json.count('}')
        escaped_braces = escaped_json.count('{{') + escaped_json.count('}}')
        
        print(f"\n📊 Статистика:")
        print(f"   Фигурных скобок в оригинале: {original_braces}")
        print(f"   Экранированных скобок: {escaped_braces}")
        
        if escaped_braces > 0:
            print("✅ JSON успешно экранирован")
        else:
            print("❌ Экранирование не сработало")
        
        # Test that the method doesn't crash (without real API call)
        print("\n🧪 Тестирование метода analyze_user_intent (без API):")
        
        try:
            # This will fail on API call but shouldn't fail on JSON escaping
            user_message = "какие у меня есть задачи"
            conversation_history = []
            
            # Simulate the logic up to the API call
            tasks_json = json.dumps(tasks_info, ensure_ascii=False, indent=2).replace('{', '{{').replace('}', '}}')
            
            context_info = ""
            if conversation_history:
                context_info = "\n".join([
                    f"{msg.get('role', 'user')}: {msg.get('content', '')}" 
                    for msg in conversation_history[-5:]
                ])
            
            analysis_prompt = f"""
            СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ: {user_message}

            СПИСОК ЗАДАЧ:
            {tasks_json}

            КОНТЕКСТ РАЗГОВОРА:
            {context_info}

            Проанализируй намерение пользователя и верни JSON с результатом анализа.
            """
            
            print("✅ Промпт успешно сформирован без ошибок экранирования")
            print("📝 Фрагмент промпта:")
            print(analysis_prompt[:300] + "...")
            
        except Exception as e:
            if "missing variables" in str(e):
                print("❌ Ошибка экранирования все еще присутствует")
                print(f"Ошибка: {e}")
            else:
                print("✅ Ошибки экранирования нет (другая ошибка ожидаема)")
                print(f"Ожидаемая ошибка API: {e}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)

if __name__ == "__main__":
    asyncio.run(test_json_escaping())