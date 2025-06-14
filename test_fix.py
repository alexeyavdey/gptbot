#!/usr/bin/env python3
"""
Тест исправления ошибки с None значениями в аналитике
"""

import sys
import os
sys.path.insert(0, os.getcwd())

async def test_database_analytics():
    """Тест аналитики для пользователя без задач"""
    print("🧪 Тест исправления ошибки с None значениями")
    
    try:
        from task_database import get_database
        
        db = get_database()
        test_user_id = 999999  # Пользователь без задач
        
        print("\n1. Тест аналитики для пользователя без задач:")
        analytics = db.get_task_analytics(test_user_id)
        print(f"   Аналитика: {analytics}")
        
        # Проверяем, что все значения не None
        required_fields = ['total_tasks', 'completed_tasks', 'in_progress_tasks', 'pending_tasks', 'completion_rate']
        
        for field in required_fields:
            value = analytics.get(field)
            if value is None:
                print(f"   ❌ Поле {field} равно None")
                return False
            else:
                print(f"   ✅ {field}: {value}")
        
        print("\n2. Тест получения состояния пользователя:")
        from enhanced_ai_agents import OrchestratorAgent
        
        orchestrator = OrchestratorAgent("test_key")
        user_state = await orchestrator._get_user_state(test_user_id)
        print(f"   Состояние пользователя: {user_state}")
        
        # Проверяем вычисления
        active_tasks = user_state.get('active_tasks', 0)
        if isinstance(active_tasks, int):
            print(f"   ✅ active_tasks корректно вычислены: {active_tasks}")
        else:
            print(f"   ❌ active_tasks некорректны: {active_tasks}")
            return False
        
        print("\n3. Тест контекста AI ментора:")
        context = await orchestrator.mentor_agent._get_user_context(test_user_id)
        print(f"   Контекст AI ментора: {context}")
        
        print("\n✅ Все тесты пройдены! Ошибка с None значениями исправлена.")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_database_analytics())