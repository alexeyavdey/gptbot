#!/usr/bin/env python3
"""
Отладка реальной ошибки с конкретным пользователем
"""

import sys
import os
sys.path.insert(0, os.getcwd())

async def debug_user_602126():
    """Отладка для пользователя 602126"""
    print("🔍 Отладка ошибки для пользователя 602126")
    
    try:
        from enhanced_ai_agents import initialize_enhanced_agents
        from constants import GPT4_MODEL
        import env
        
        print("\n1. Инициализация оркестратора:")
        # Используем реальный API ключ если есть
        api_key = getattr(env, 'API_KEY', 'test_key')
        orchestrator = initialize_enhanced_agents(api_key, GPT4_MODEL)
        print("   ✅ Оркестратор инициализирован")
        
        user_id = 602126
        message = "у меня есть задачи?"
        
        print(f"\n2. Тест аналитики напрямую для пользователя {user_id}:")
        analytics = orchestrator.db.get_task_analytics(user_id)
        print(f"   Raw analytics: {analytics}")
        
        print(f"\n3. Тест получения состояния для пользователя {user_id}:")
        user_state = await orchestrator._get_user_state(user_id)
        print(f"   User state: {user_state}")
        
        print(f"\n4. Полный тест роутинга:")
        result = await orchestrator.route_request(user_id, message)
        print(f"   Результат роутинга: {result}")
        
        print("\n✅ Все тесты пройдены без ошибок!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_user_602126())