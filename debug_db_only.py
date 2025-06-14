#!/usr/bin/env python3
"""
Отладка только базы данных для пользователя 602126
"""

import sys
import os
sys.path.insert(0, os.getcwd())

def debug_database_602126():
    """Отладка базы данных для пользователя 602126"""
    print("🔍 Отладка базы данных для пользователя 602126")
    
    try:
        from task_database import get_database
        
        db = get_database()
        user_id = 602126
        
        print(f"\n1. Проверка задач пользователя {user_id}:")
        tasks = db.get_tasks(user_id)
        print(f"   Задачи: {tasks}")
        print(f"   Количество задач: {len(tasks)}")
        
        print(f"\n2. Прямой SQL запрос для аналитики:")
        with db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_tasks,
                    COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) as completed_tasks,
                    COALESCE(SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END), 0) as in_progress_tasks,
                    COALESCE(SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END), 0) as pending_tasks
                FROM tasks 
                WHERE user_id = ?
            """, (user_id,))
            
            raw_result = cursor.fetchone()
            print(f"   Raw SQL result: {raw_result}")
            print(f"   Raw SQL result type: {type(raw_result)}")
            
            stats = dict(raw_result)
            print(f"   Converted to dict: {stats}")
            
            for key, value in stats.items():
                print(f"   {key}: {value} (type: {type(value)})")
        
        print(f"\n3. Тест get_task_analytics:")
        analytics = db.get_task_analytics(user_id)
        print(f"   Analytics result: {analytics}")
        
        for key, value in analytics.items():
            print(f"   {key}: {value} (type: {type(value)})")
        
        print(f"\n4. Тест вычислений:")
        total_tasks = analytics.get('total_tasks', 0) or 0
        completed_tasks = analytics.get('completed_tasks', 0) or 0
        
        print(f"   total_tasks: {total_tasks} (type: {type(total_tasks)})")
        print(f"   completed_tasks: {completed_tasks} (type: {type(completed_tasks)})")
        
        if total_tasks is None:
            print("   ❌ total_tasks is None!")
        if completed_tasks is None:
            print("   ❌ completed_tasks is None!")
            
        try:
            active_tasks = total_tasks - completed_tasks
            print(f"   ✅ active_tasks calculation successful: {active_tasks}")
        except Exception as calc_error:
            print(f"   ❌ active_tasks calculation failed: {calc_error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_database_602126()