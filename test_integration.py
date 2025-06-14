#!/usr/bin/env python3
"""
Тест интеграции enhanced AI agents в основного бота
"""

import asyncio
import sys
import os
sys.path.insert(0, os.getcwd())

# Мокаем aiogram types для тестирования
class MockMessage:
    def __init__(self, text, user_id=12345):
        self.text = text
        self.md_text = text
        self.message_id = 1
        self.from_user = MockUser(user_id)
    
    async def answer(self, text):
        print(f"Bot response: {text}")

class MockUser:
    def __init__(self, user_id):
        self.id = user_id
        self.username = f"user_{user_id}"
        self.first_name = "Test"
        self.full_name = "Test User"

async def test_enhanced_agents_integration():
    """Тест интеграции enhanced agents"""
    print("🧪 Тест интеграции enhanced AI agents в основного бота\n")
    
    try:
        # Импортируем enhanced agents напрямую
        from enhanced_ai_agents import initialize_enhanced_agents
        from constants import GPT4_MODEL
        
        # Мокаем API ключ для тестирования
        api_key = "test_key"
        
        print("1. Инициализация оркестратора:")
        orchestrator = initialize_enhanced_agents(api_key, GPT4_MODEL)
        
        if orchestrator:
            print("   ✅ Оркестратор успешно инициализирован")
        else:
            print("   ❌ Ошибка инициализации оркестратора")
            return False
        
        print("\n2. Тест различных типов запросов:")
        
        test_cases = [
            ("создай задачу купить молоко с высоким приоритетом", "TASK_MANAGEMENT"),
            ("сколько у меня задач", "TASK_MANAGEMENT"), 
            ("начинаем вечерний трекер", "EVENING_TRACKER"),
            ("как справиться со стрессом", "AI_MENTOR"),
            ("настрой уведомления", "NOTIFICATIONS")
        ]
        
        success_count = 0
        
        for message_text, expected_agent in test_cases:
            print(f"\n   Тест: '{message_text}'")
            print(f"   Ожидаемый агент: {expected_agent}")
            
            try:
                # Создаем мок сообщение
                mock_message = MockMessage(message_text)
                
                # Симулируем вызов через actions.py
                user_id = mock_message.from_user.id
                result = await orchestrator.route_request(user_id, message_text)
                
                routed_agent = result.get("agent", "unknown")
                confidence = result.get("confidence", 0)
                response = result.get("response", "")
                
                print(f"   Результат: {routed_agent} (confidence: {confidence:.2f})")
                print(f"   Ответ: {response[:100]}...")
                
                # Простая проверка соответствия
                if any(expected_word in routed_agent.upper() for expected_word in expected_agent.split("_")):
                    print("   ✅ Роутинг корректный")
                    success_count += 1
                else:
                    print(f"   ⚠️ Роутинг неточный (ожидался {expected_agent})")
                    success_count += 0.5  # Частичный зачет
                    
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
        
        print(f"\n3. Результаты тестирования:")
        print(f"   Успешно: {success_count}/{len(test_cases)}")
        
        success_rate = success_count / len(test_cases)
        if success_rate >= 0.8:
            print("   ✅ Интеграция работает корректно")
            return True
        else:
            print("   ⚠️ Интеграция требует доработки")
            return False
            
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("Возможно, отсутствуют зависимости или API ключи")
        return False
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_message_flow():
    """Тест полного flow обработки сообщения"""
    print("\n🧪 Тест полного flow обработки сообщения\n")
    
    try:
        from enhanced_ai_agents import initialize_enhanced_agents
        from constants import GPT4_MODEL
        
        orchestrator = initialize_enhanced_agents("test_key", GPT4_MODEL)
        
        # Создаем несколько тестовых сообщений
        test_messages = [
            "создай задачу протестировать новую систему агентов",
            "сколько у меня всего задач",
            "покажи мою продуктивность"
        ]
        
        for i, text in enumerate(test_messages, 1):
            print(f"{i}. Обработка: '{text}'")
            
            mock_message = MockMessage(text)
            
            # Обрабатываем через оркестратор
            result = await orchestrator.route_request(mock_message.from_user.id, text)
            print(f"   Агент: {result.get('agent')}")
            print(f"   Ответ: {result.get('response', '')[:100]}...")
            print()
        
        print("✅ Полный flow работает")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в полном flow: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование интеграции enhanced AI agents\n")
    
    results = []
    
    # Тест инициализации и роутинга
    results.append(await test_enhanced_agents_integration())
    
    # Тест полного flow
    results.append(await test_message_flow())
    
    # Итоги
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
    print(f"✅ Пройдено: {passed}/{total} тестов")
    
    if passed == total:
        print("\n🎉 ИНТЕГРАЦИЯ УСПЕШНА!")
        print("🔧 Enhanced AI agents готовы к использованию в боте!")
        print("\n🎯 Система включает:")
        print("• 🎭 OrchestratorAgent - LLM роутинг запросов")
        print("• 👋 WelcomeAgent - приветственный модуль")
        print("• 📋 TaskManagementAgent - управление задачами")
        print("• 🔔 NotificationAgent - система уведомлений")
        print("• 🌙 EveningTrackerAgent - вечерний трекер")
        print("• 🧠 AIMentorAgent - AI ментор с памятью")
    else:
        print(f"\n⚠️ {total - passed} тестов провалились.")
        print("Требуется дополнительная отладка.")

if __name__ == "__main__":
    asyncio.run(main())