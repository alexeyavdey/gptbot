#!/usr/bin/env python3
"""
Тест точного сценария из диалога с новым интерактивным алгоритмом удаления
"""

import asyncio
import os
import sys
import tempfile
import json
import re

# Add the project root to Python path  
sys.path.insert(0, '/Users/alexonic/Documents/project/gptbot')

from enhanced_ai_agents import TaskManagementAgent
from task_database import TaskDatabase

async def test_original_dialog_scenario():
    """Воспроизводим точный сценарий из диалога с новым алгоритмом"""
    
    print("🎭 Тестирование оригинального диалога с новым алгоритмом")
    print("=" * 70)
    
    temp_db = tempfile.mktemp(suffix='.db')
    
    try:
        # Initialize
        db = TaskDatabase(temp_db)
        api_key = os.getenv('API_KEY') or 'test-key'
        task_agent = TaskManagementAgent(api_key=api_key, model="gpt-4")
        task_agent.db = db
        
        user_id = 123456
        
        print("📝 ДИАЛОГ СИМУЛЯЦИЯ:")
        print("-" * 70)
        
        # Шаг 1: Пользователь просит добавить задачу
        print("👤 Alexey Avdey: добавь задачу")
        print("🤖 SberMarkBot: Пожалуйста, уточните детали задачи...")
        
        # Шаг 2: Создаем задачу (как будто агент это обработал)
        db.ensure_user_exists(user_id)
        task_id = db.create_task(
            user_id=user_id,
            title="Стратегия сайта Банка — презентация для Влада",
            description="Сделать презентацию для Влада", 
            priority="high"
        )
        
        print("👤 Alexey Avdey: Стратегия сайта Банка, сделать презентацию для Влада, высокий приоритет, дедлайн 1 июля 2025")
        print("🤖 SberMarkBot: Задача 'Стратегия сайта Банка — презентация для Влада' с высоким приоритетом успешно создана.")
        
        # Шаг 3: Подсчет задач
        tasks = db.get_tasks(user_id)
        print(f"👤 Alexey Avdey: сколько у меня задач")
        print(f"🤖 SberMarkBot: У вас сейчас {len(tasks)} задача:")
        for i, task in enumerate(tasks, 1):
            print(f"   {i}. {task['title']}")
        
        print("\n" + "="*70)
        print("🔥 КРИТИЧЕСКИЙ МОМЕНТ - УДАЛЕНИЕ ЗАДАЧИ")
        print("="*70)
        
        # Шаг 4: ПЕРВАЯ попытка удаления (неточная)
        print("👤 Alexey Avdey: давай ее удалим")
        
        delete_params1 = json.dumps({
            "user_id": user_id,
            "search_text": "задачу"  # Очень общий запрос
        })
        
        result1 = task_agent._delete_task(delete_params1)
        print(f"🤖 SberMarkBot: {result1}")
        
        print("\n" + "-"*70)
        
        # Шаг 5: ВТОРАЯ попытка удаления (более точная)
        print("👤 Alexey Avdey: удалим задачу про стратегию")
        
        delete_params2 = json.dumps({
            "user_id": user_id,
            "search_text": "стратегию"
        })
        
        result2 = task_agent._delete_task(delete_params2)
        print(f"🤖 SberMarkBot: {result2}")
        
        # Извлекаем task_id из ответа
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        task_ids = re.findall(uuid_pattern, result2.lower())
        
        if task_ids:
            extracted_task_id = task_ids[0]
            
            print("\n" + "-"*70)
            print("✅ МОМЕНТ ИСТИНЫ - ПОДТВЕРЖДЕНИЕ")
            print("-"*70)
            
            # Шаг 6: Подтверждение удаления
            print("👤 Alexey Avdey: да, подтверждаю")
            
            delete_params3 = json.dumps({
                "user_id": user_id,
                "task_id": extracted_task_id
            })
            
            result3 = task_agent._delete_task(delete_params3)
            print(f"🤖 SberMarkBot: {result3}")
            
            # Проверяем итоговое состояние
            final_tasks = db.get_tasks(user_id)
            
            print("\n" + "="*70)
            print("📊 ИТОГОВЫЙ РЕЗУЛЬТАТ")
            print("="*70)
            
            if len(final_tasks) == 0:
                print("✅ УСПЕХ! Задача успешно удалена!")
                print("✅ Новый алгоритм решает проблему из диалога")
                print("✅ Теперь удаление происходит безопасно с подтверждением")
            else:
                print("❌ Ошибка: задача не была удалена")
                print(f"Осталось задач: {len(final_tasks)}")
                
            print(f"\n📈 Преимущества нового алгоритма:")
            print("   • Поиск задач по частичному совпадению")
            print("   • Показ всех найденных вариантов") 
            print("   • Обязательное подтверждение удаления")
            print("   • Отображение деталей задачи перед удалением")
            print("   • Защита от случайного удаления")
            
        else:
            print("❌ Не удалось извлечь ID задачи для подтверждения")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)

if __name__ == "__main__":
    asyncio.run(test_original_dialog_scenario())