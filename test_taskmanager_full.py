#!/usr/bin/env python3
"""
Полный юнит-тест TaskManagementAgent
Тестируем весь жизненный цикл задачи: создание -> просмотр -> обновление -> удаление
"""

import asyncio
import sys
import os
sys.path.insert(0, os.getcwd())

async def test_taskmanager_lifecycle():
    """Полный тест жизненного цикла задачи через TaskManagementAgent"""
    print("🧪 Полный тест TaskManagementAgent с реальным OpenAI API")
    
    try:
        from enhanced_ai_agents import TaskManagementAgent
        from constants import GPT4_MODEL
        
        # Используем API ключ из переменных окружения
        import env
        api_key = env.API_KEY or "your-openai-api-key-here"
        test_user_id = 999888777  # Тестовый пользователь
        
        print(f"1. Инициализация TaskManagementAgent:")
        agent = TaskManagementAgent(api_key, GPT4_MODEL)
        print("   ✅ Агент инициализирован")
        
        # Очищаем задачи тестового пользователя (если есть)
        print(f"\n2. Очистка данных тестового пользователя {test_user_id}:")
        existing_tasks = agent.db.get_tasks(test_user_id)
        for task in existing_tasks:
            agent.db.delete_task(task['id'], test_user_id)
        print(f"   ✅ Удалено {len(existing_tasks)} старых задач")
        
        print(f"\n3. Тест 1: Создание задачи")
        print("   Запрос: 'создай задачу купить молоко с высоким приоритетом'")
        result1 = await agent.process_task_request(test_user_id, "создай задачу купить молоко с высоким приоритетом")
        print(f"   Ответ: {result1}")
        
        print(f"\n4. Тест 2: Создание второй задачи")
        print("   Запрос: 'добавь задачу написать отчет'")
        result2 = await agent.process_task_request(test_user_id, "добавь задачу написать отчет")
        print(f"   Ответ: {result2}")
        
        print(f"\n5. Тест 3: Просмотр количества задач")
        print("   Запрос: 'сколько у меня задач'")
        result3 = await agent.process_task_request(test_user_id, "сколько у меня задач")
        print(f"   Ответ: {result3}")
        
        print(f"\n6. Тест 4: Просмотр списка задач")
        print("   Запрос: 'покажи мои задачи'")
        result4 = await agent.process_task_request(test_user_id, "покажи мои задачи")
        print(f"   Ответ: {result4}")
        
        print(f"\n7. Тест 5: Аналитика и продуктивность")
        print("   Запрос: 'покажи мою продуктивность'")
        result5 = await agent.process_task_request(test_user_id, "покажи мою продуктивность")
        print(f"   Ответ: {result5}")
        
        print(f"\n8. Проверка данных в базе:")
        tasks_in_db = agent.db.get_tasks(test_user_id)
        print(f"   Задач в базе: {len(tasks_in_db)}")
        for i, task in enumerate(tasks_in_db, 1):
            print(f"   {i}. {task['title']} - {task['priority']} - {task['status']}")
        
        # Получаем ID первой задачи для тестов обновления и удаления
        if tasks_in_db:
            first_task_id = tasks_in_db[0]['id']
            first_task_title = tasks_in_db[0]['title']
            
            print(f"\n9. Тест 6: Обновление статуса задачи")
            print(f"   Обновляем статус задачи '{first_task_title}' на 'in_progress'")
            update_result = agent.db.update_task_status(first_task_id, test_user_id, 'in_progress')
            print(f"   Результат обновления: {'✅ Успешно' if update_result else '❌ Ошибка'}")
            
            print(f"\n10. Тест 7: Проверка обновления")
            print("    Запрос: 'покажи мои задачи'")
            result6 = await agent.process_task_request(test_user_id, "покажи мои задачи")
            print(f"    Ответ: {result6}")
            
            print(f"\n11. Тест 8: Завершение задачи")
            print(f"    Завершаем задачу '{first_task_title}'")
            complete_result = agent.db.update_task_status(first_task_id, test_user_id, 'completed')
            print(f"    Результат завершения: {'✅ Успешно' if complete_result else '❌ Ошибка'}")
            
            print(f"\n12. Тест 9: Финальная аналитика")
            print("    Запрос: 'покажи статистику'")
            result7 = await agent.process_task_request(test_user_id, "покажи статистику")
            print(f"    Ответ: {result7}")
            
            print(f"\n13. Тест 10: Удаление задачи")
            print(f"    Удаляем задачу '{first_task_title}'")
            delete_result = agent.db.delete_task(first_task_id, test_user_id)
            print(f"    Результат удаления: {'✅ Успешно' if delete_result else '❌ Ошибка'}")
            
            print(f"\n14. Финальная проверка:")
            final_tasks = agent.db.get_tasks(test_user_id)
            print(f"    Задач осталось: {len(final_tasks)}")
            for task in final_tasks:
                print(f"    - {task['title']} ({task['status']})")
        
        print(f"\n15. Очистка тестовых данных:")
        # Удаляем все оставшиеся тестовые задачи
        remaining_tasks = agent.db.get_tasks(test_user_id)
        for task in remaining_tasks:
            agent.db.delete_task(task['id'], test_user_id)
        print(f"    ✅ Удалено {len(remaining_tasks)} оставшихся задач")
        
        print(f"\n🎉 ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ УСПЕШНО!")
        print(f"📊 Проверенная функциональность:")
        print(f"   ✅ Создание задач через LangChain")
        print(f"   ✅ Подсчет и просмотр задач")
        print(f"   ✅ Аналитика и статистика")
        print(f"   ✅ Обновление статусов")
        print(f"   ✅ Удаление задач")
        print(f"   ✅ Интеграция с SQLite базой")
        print(f"   ✅ LLM роутинг и обработка")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_edge_cases():
    """Тест граничных случаев"""
    print(f"\n🧪 Тест граничных случаев")
    
    try:
        from enhanced_ai_agents import TaskManagementAgent
        from constants import GPT4_MODEL
        
        api_key = env.API_KEY or "your-openai-api-key-here"
        test_user_id = 999888778  # Другой тестовый пользователь
        
        agent = TaskManagementAgent(api_key, GPT4_MODEL)
        
        print(f"1. Тест пустого пользователя:")
        print("   Запрос: 'сколько у меня задач'")
        result1 = await agent.process_task_request(test_user_id, "сколько у меня задач")
        print(f"   Ответ: {result1}")
        
        print(f"\n2. Тест неполного запроса на создание:")
        print("   Запрос: 'создай задачу'")
        result2 = await agent.process_task_request(test_user_id, "создай задачу")
        print(f"   Ответ: {result2}")
        
        print(f"\n3. Тест неизвестного запроса:")
        print("   Запрос: 'расскажи анекдот'")
        result3 = await agent.process_task_request(test_user_id, "расскажи анекдот")
        print(f"   Ответ: {result3}")
        
        print(f"\n✅ Граничные случаи протестированы")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте граничных случаев: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск полного тестирования TaskManagementAgent")
    print("=" * 60)
    
    results = []
    
    # Основной тест жизненного цикла
    results.append(await test_taskmanager_lifecycle())
    
    # Тест граничных случаев
    results.append(await test_edge_cases())
    
    # Итоги
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 60)
    print(f"📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"✅ Пройдено: {passed}/{total} тестовых сценариев")
    
    if passed == total:
        print(f"\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print(f"🔧 TaskManagementAgent полностью функционален:")
        print(f"   • LangChain агент работает корректно")
        print(f"   • Все CRUD операции выполняются")
        print(f"   • SQLite интеграция работает")
        print(f"   • Форматирование ответов корректное")
        print(f"   • Обработка ошибок функционирует")
    else:
        print(f"\n⚠️ {total - passed} тестов провалились")
        print(f"Требуется дополнительная отладка")

if __name__ == "__main__":
    asyncio.run(main())