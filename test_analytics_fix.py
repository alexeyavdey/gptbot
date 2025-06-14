#!/usr/bin/env python3
"""
Быстрый тест исправления аналитики
"""

import asyncio
import sys
import os
sys.path.insert(0, os.getcwd())

async def test_analytics_fix():
    """Тест исправленной аналитики"""
    print("🧪 Тест исправления аналитики")
    
    try:
        from enhanced_ai_agents import TaskManagementAgent
        from constants import GPT4_MODEL
        
        api_key = env.API_KEY or "your-openai-api-key-here"
        test_user_id = 999888779
        
        agent = TaskManagementAgent(api_key, GPT4_MODEL)
        
        # Создаем тестовую задачу
        await agent.process_task_request(test_user_id, "создай задачу тестовая аналитика")
        
        # Тестируем аналитику
        print("Тест аналитики:")
        result = await agent.process_task_request(test_user_id, "покажи мою продуктивность")
        print(f"Результат: {result}")
        
        # Очистка
        tasks = agent.db.get_tasks(test_user_id)
        for task in tasks:
            agent.db.delete_task(task['id'], test_user_id)
        
        print("✅ Тест аналитики завершен")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_analytics_fix())