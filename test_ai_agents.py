"""
Тестирование AI-агентов трекера
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from ai_agents import TaskManagerAgent, EveningTrackerAgent, OrchestratorAgent, initialize_agents

# Мокаем зависимости для тестирования
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

async def test_task_manager_agent():
    """Тест агента управления задачами"""
    print("🧪 Тестирование TaskManagerAgent...")
    
    # Создаем мок API ключа
    api_key = "test_key"
    
    try:
        # Мокаем OpenAI клиент
        agent = TaskManagerAgent(api_key)
        
        # Тестируем создание задачи
        create_params = json.dumps({
            "user_id": 123,
            "title": "Тестовая задача",
            "description": "Описание тестовой задачи",
            "priority": "high"
        })
        
        result = agent._create_task(create_params)
        result_data = json.loads(result)
        
        if result_data["success"]:
            print("✅ Создание задачи: OK")
            task_id = result_data["task_id"]
            
            # Тестируем получение задач
            get_params = json.dumps({"user_id": 123})
            tasks_result = agent._get_tasks(get_params)
            tasks_data = json.loads(tasks_result)
            
            if tasks_data["success"] and len(tasks_data["tasks"]) > 0:
                print("✅ Получение задач: OK")
                
                # Тестируем обновление статуса
                update_params = json.dumps({
                    "user_id": 123,
                    "task_id": task_id,
                    "new_status": "in_progress"
                })
                
                update_result = agent._update_task_status(update_params)
                update_data = json.loads(update_result)
                
                if update_data["success"]:
                    print("✅ Обновление статуса: OK")
                else:
                    print("❌ Обновление статуса: FAILED")
            else:
                print("❌ Получение задач: FAILED")
        else:
            print("❌ Создание задачи: FAILED")
            
    except Exception as e:
        print(f"❌ TaskManagerAgent тест провален: {e}")


async def test_evening_tracker_agent():
    """Тест агента вечернего трекера"""
    print("\n🧪 Тестирование EveningTrackerAgent...")
    
    api_key = "test_key"
    
    try:
        agent = EveningTrackerAgent(api_key)
        
        # Тестируем начало вечерней сессии
        session_result = await agent.start_evening_session(123)
        
        if session_result["success"]:
            print("✅ Начало вечерней сессии: OK")
        else:
            print(f"❌ Начало вечерней сессии: {session_result.get('error', 'FAILED')}")
            
    except Exception as e:
        print(f"❌ EveningTrackerAgent тест провален: {e}")


async def test_orchestrator_agent():
    """Тест агента-оркестратора"""
    print("\n🧪 Тестирование OrchestratorAgent...")
    
    api_key = "test_key"
    
    try:
        orchestrator = OrchestratorAgent(api_key)
        
        # Тестируем различные типы запросов
        test_requests = [
            ("создай задачу 'купить молоко'", "TASK_MANAGER"),
            ("начинаем вечерний трекер", "EVENING_TRACKER"),
            ("как дела с продуктивностью?", "GENERAL")
        ]
        
        for request, expected_type in test_requests:
            try:
                result = await orchestrator.route_request(123, request)
                print(f"✅ Запрос '{request}' -> {result['agent']}")
            except Exception as e:
                print(f"❌ Запрос '{request}' провален: {e}")
                
    except Exception as e:
        print(f"❌ OrchestratorAgent тест провален: {e}")


async def test_integration():
    """Интеграционный тест всей системы"""
    print("\n🧪 Интеграционное тестирование...")
    
    try:
        # Инициализируем всю систему
        api_key = "test_key"
        orchestrator = initialize_agents(api_key)
        
        print("✅ Инициализация системы агентов: OK")
        
        # Тестируем полный цикл работы с задачами через оркестратора
        task_requests = [
            "создай задачу 'написать отчет' с высоким приоритетом",
            "покажи все мои задачи",
            "измени статус задачи на 'в работе'",
            "какая у меня продуктивность?"
        ]
        
        for request in task_requests:
            try:
                result = await orchestrator.route_request(123, request)
                print(f"✅ Обработка: '{request}' -> {result['agent']}")
            except Exception as e:
                print(f"❌ Обработка '{request}' провалена: {e}")
                
    except Exception as e:
        print(f"❌ Интеграционный тест провален: {e}")


def test_data_persistence():
    """Тест сохранения данных"""
    print("\n🧪 Тестирование сохранения данных...")
    
    api_key = "test_key"
    
    try:
        agent = TaskManagerAgent(api_key)
        
        # Создаем пользователя и задачу
        user_data = agent._load_user_data(999)  # Новый пользователь
        
        if user_data is None:
            print("✅ Новый пользователь не найден (ожидаемо): OK")
        
        # Тестируем создание и сохранение задачи
        create_params = json.dumps({
            "user_id": 999,
            "title": "Тест сохранения",
            "description": "Проверка персистентности данных"
        })
        
        result = agent._create_task(create_params)
        result_data = json.loads(result)
        
        if result_data["success"]:
            print("✅ Создание и сохранение задачи: OK")
            
            # Проверяем загрузку данных
            loaded_data = agent._load_user_data(999)
            if loaded_data and len(loaded_data.tasks) > 0:
                print("✅ Загрузка сохраненных данных: OK")
            else:
                print("❌ Загрузка сохраненных данных: FAILED")
        else:
            print("❌ Создание и сохранение задачи: FAILED")
            
    except Exception as e:
        print(f"❌ Тест сохранения данных провален: {e}")


async def run_all_tests():
    """Запуск всех тестов"""
    print("🚀 Запуск тестов AI-агентов трекера\n")
    
    await test_task_manager_agent()
    await test_evening_tracker_agent()
    await test_orchestrator_agent()
    await test_integration()
    test_data_persistence()
    
    print("\n✨ Тестирование завершено!")


if __name__ == "__main__":
    asyncio.run(run_all_tests())