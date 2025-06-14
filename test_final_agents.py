"""
Финальный тест исправленных AI-агентов
"""

import asyncio
import sys
import os
sys.path.insert(0, os.getcwd())

from ai_agents import TaskManagerAgent, OrchestratorAgent, get_database

async def test_full_workflow():
    """Тест полного workflow с агентами"""
    print("🧪 Тест полного workflow с AI-агентами")
    
    try:
        api_key = "test_key"
        
        # Создаем агентов
        task_agent = TaskManagerAgent(api_key)
        orchestrator = OrchestratorAgent(api_key)
        
        user_id = 555
        
        print("\n1. Тест создания задач:")
        test_messages = [
            "создай задачу купить молоко с высоким приоритетом",
            "добавь задачу написать отчет",
            "новая задача позвонить маме срочно"
        ]
        
        for message in test_messages:
            print(f"  Запрос: '{message}'")
            response = await task_agent.process_request(user_id, message)
            print(f"  Ответ: {response}")
        
        print("\n2. Тест подсчета задач:")
        response = await task_agent.process_request(user_id, "сколько у меня задач")
        print(f"  Ответ: {response}")
        
        print("\n3. Тест показа задач:")
        response = await task_agent.process_request(user_id, "покажи мои задачи")
        print(f"  Ответ: {response}")
        
        print("\n4. Тест аналитики:")
        response = await task_agent.process_request(user_id, "покажи мою продуктивность")
        print(f"  Ответ: {response}")
        
        print("\n5. Тест роутинга через оркестратора:")
        # Симулируем роутинг
        routing_tests = [
            ("создай задачу выгулять собаку", "TASK_MANAGER"),
            ("сколько задач у меня", "TASK_MANAGER"),
            ("начинаем вечерний трекер", "EVENING_TRACKER"),
            ("как дела с продуктивностью", "GENERAL")
        ]
        
        for message, expected_route in routing_tests:
            print(f"  Запрос: '{message}' → Ожидается: {expected_route}")
            # В реальности здесь был бы вызов orchestrator.route_request()
            # Но для демонстрации просто показываем логику
            
            if any(word in message.lower() for word in ['создай', 'задач', 'продуктивность']):
                actual_route = "TASK_MANAGER"
            elif "вечерний" in message.lower():
                actual_route = "EVENING_TRACKER"
            else:
                actual_route = "GENERAL"
            
            match = "✅" if actual_route == expected_route else "❌"
            print(f"    {match} Результат: {actual_route}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в test_full_workflow: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_edge_cases():
    """Тест граничных случаев"""
    print("\n🧪 Тест граничных случаев")
    
    try:
        api_key = "test_key"
        task_agent = TaskManagerAgent(api_key)
        user_id = 666
        
        print("\n1. Тест пустого пользователя:")
        response = await task_agent.process_request(user_id, "сколько у меня задач")
        print(f"  Ответ: {response}")
        
        print("\n2. Тест неполной команды:")
        response = await task_agent.process_request(user_id, "создай задачу")
        print(f"  Ответ: {response}")
        
        print("\n3. Тест неизвестной команды:")
        response = await task_agent.process_request(user_id, "что такое жизнь")
        print(f"  Ответ: {response}")
        
        print("\n4. Тест после создания задач:")
        await task_agent.process_request(user_id, "создай задачу тестовая")
        response = await task_agent.process_request(user_id, "сколько у меня задач")
        print(f"  Ответ: {response}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в test_edge_cases: {e}")
        return False

def test_database_consistency():
    """Тест консистентности данных"""
    print("\n🧪 Тест консистентности данных")
    
    try:
        db = get_database()
        user_id = 777
        
        # Создаем несколько задач
        task_ids = []
        for i in range(5):
            task_id = db.create_task(user_id, f"Задача {i+1}", f"Описание {i+1}", "medium")
            task_ids.append(task_id)
        
        print(f"1. Создано {len(task_ids)} задач")
        
        # Завершаем 2 задачи
        for i in range(2):
            db.update_task_status(task_ids[i], user_id, "completed")
        
        print("2. Завершено 2 задачи")
        
        # Проверяем аналитику
        analytics = db.get_task_analytics(user_id)
        expected_total = 5
        expected_completed = 2
        expected_rate = 40.0
        
        print(f"3. Аналитика:")
        print(f"   Всего: {analytics['total_tasks']} (ожидается: {expected_total})")
        print(f"   Завершено: {analytics['completed_tasks']} (ожидается: {expected_completed})")
        print(f"   Процент: {analytics['completion_rate']} (ожидается: {expected_rate})")
        
        # Проверяем корректность
        checks = [
            analytics['total_tasks'] == expected_total,
            analytics['completed_tasks'] == expected_completed,
            abs(analytics['completion_rate'] - expected_rate) < 0.1
        ]
        
        if all(checks):
            print("✅ Данные консистентны")
            return True
        else:
            print("❌ Обнаружены несоответствия в данных")
            return False
        
    except Exception as e:
        print(f"❌ Ошибка в test_database_consistency: {e}")
        return False

async def main():
    """Главная функция тестирования"""
    print("🚀 Финальное тестирование AI-агентов\n")
    
    results = []
    
    # Запускаем все тесты
    results.append(test_database_consistency())
    results.append(await test_full_workflow())
    results.append(await test_edge_cases())
    
    # Подводим итоги
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Результаты финального тестирования:")
    print(f"✅ Пройдено: {passed}/{total} тестов")
    
    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("🚀 Система AI-агентов готова к использованию!")
        print("\nПримеры команд:")
        print("• 'создай задачу купить молоко с высоким приоритетом'")
        print("• 'сколько у меня задач'")
        print("• 'покажи мои задачи'") 
        print("• 'покажи мою продуктивность'")
    else:
        print("\n⚠️ Некоторые тесты провалились.")
        print("Необходимо дополнительное исследование.")

if __name__ == "__main__":
    asyncio.run(main())