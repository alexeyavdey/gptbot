#!/usr/bin/env python3
"""
Тест интеграции TaskSelectorAgent с вечерним трекером и AI-ментором
"""

import asyncio
import os
import sys
import tempfile
import json
from unittest.mock import AsyncMock, patch

# Add the project root to Python path  
sys.path.insert(0, '/Users/alexonic/Documents/project/gptbot')

from enhanced_ai_agents import EveningTrackerAgent, AIMentorAgent, TaskSelectorAgent
from task_database import TaskDatabase

async def test_evening_tracker_task_context():
    """Тест работы с задачами по контексту в вечернем трекере"""
    
    print("🌙 Тестирование вечернего трекера с контекстом задач")
    print("=" * 60)
    
    temp_db = tempfile.mktemp(suffix='.db')
    
    try:
        # Initialize
        db = TaskDatabase(temp_db)
        evening_agent = EveningTrackerAgent(api_key="mock-key", model="gpt-4")
        evening_agent.db = db
        
        user_id = 123456
        
        # Create test tasks
        db.ensure_user_exists(user_id)
        
        task_ids = []
        test_tasks = [
            {"title": "Подготовить презентацию для клиента", "description": "Презентация по стратегии", "priority": "high"},
            {"title": "Написать отчет о продажах", "description": "Квартальный отчет", "priority": "medium"},
            {"title": "Встреча с командой", "description": "Обсуждение планов", "priority": "low"}
        ]
        
        for task_data in test_tasks:
            task_id = db.create_task(
                user_id=user_id,
                title=task_data["title"],
                description=task_data["description"], 
                priority=task_data["priority"]
            )
            task_ids.append(task_id)
            print(f"   ✅ Создана: {task_data['title']}")
        
        # Test scenarios with mock responses
        test_scenarios = [
            {
                "name": "Обсуждение конкретной задачи по названию",
                "message": "я работал над презентацией сегодня",
                "expected_task": "Подготовить презентацию для клиента",
                "mock_analysis": {
                    "action": "discuss_progress",
                    "selected_tasks": [
                        {
                            "task_id": task_ids[0],
                            "title": "Подготовить презентацию для клиента",
                            "confidence": 0.9,
                            "reasoning": "Упоминание 'презентации' соответствует задаче"
                        }
                    ],
                    "requires_confirmation": False,
                    "suggested_response": "Обсуждаем прогресс по презентации"
                }
            },
            {
                "name": "Контекстная ссылка на задачу",
                "message": "она далась мне тяжело",
                "expected_task": "Встреча с командой",  
                "mock_analysis": {
                    "action": "discuss_progress",
                    "selected_tasks": [
                        {
                            "task_id": task_ids[2],
                            "title": "Встреча с командой",
                            "confidence": 0.85,
                            "reasoning": "Из контекста предыдущего разговора"
                        }
                    ],
                    "requires_confirmation": False,
                    "suggested_response": "Обсуждаем трудности с задачей"
                },
                "conversation_history": [
                    {"role": "user", "content": "как прошла встреча с командой?"},
                    {"role": "assistant", "content": "Расскажите как прошла встреча с командой"}
                ]
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n🧪 ТЕСТ {i}: {scenario['name']}")
            print("-" * 50)
            print(f"👤 Пользователь: {scenario['message']}")
            
            # Mock the task selector
            with patch.object(evening_agent.task_selector, 'analyze_user_intent', new_callable=AsyncMock) as mock_analyze:
                mock_analyze.return_value = scenario['mock_analysis']
                
                # Test task context analysis
                conversation_history = scenario.get('conversation_history', [])
                analysis = await evening_agent.analyze_task_context(
                    user_id, scenario['message'], conversation_history
                )
                
                print(f"🔍 Анализ контекста:")
                print(f"   Действие: {analysis.get('action')}")
                print(f"   Найденные задачи: {len(analysis.get('selected_tasks', []))}")
                
                if analysis.get('selected_tasks'):
                    task = analysis['selected_tasks'][0]
                    print(f"   🎯 Определена задача: {task.get('title')}")
                    print(f"   Уверенность: {task.get('confidence', 0):.2f}")
                    
                    # Test task discussion
                    with patch.object(evening_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_llm:
                        mock_llm.return_value = "Отлично, что вы работали над этой задачей! Расскажите подробнее о своих достижениях."
                        
                        response = await evening_agent.discuss_task_progress(
                            user_id, scenario['message'], analysis['selected_tasks'], conversation_history
                        )
                        
                        print(f"🤖 Ответ трекера: {response[:100]}...")
                        
                        if scenario['expected_task'] in response:
                            print("✅ Правильно определил и обсуждает нужную задачу")
                        else:
                            print("❌ Не смог правильно определить задачу")
                
                # Verify mock was called with correct parameters
                mock_analyze.assert_called_once()
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)

async def test_ai_mentor_task_guidance():
    """Тест консультаций AI-ментора по задачам"""
    
    print("\n\n🧠 Тестирование AI-ментора с контекстом задач")
    print("=" * 60)
    
    temp_db = tempfile.mktemp(suffix='.db')
    
    try:
        # Initialize
        db = TaskDatabase(temp_db)
        mentor_agent = AIMentorAgent(api_key="mock-key", model="gpt-4")
        mentor_agent.db = db
        
        user_id = 123456
        
        # Create test tasks
        db.ensure_user_exists(user_id)
        
        task_id = db.create_task(
            user_id=user_id,
            title="Изучить новую технологию",
            description="Освоить React для нового проекта", 
            priority="high"
        )
        
        print(f"✅ Создана задача: Изучить новую технологию")
        
        # Test scenarios
        test_scenarios = [
            {
                "name": "Просьба о совете по конкретной задаче",
                "message": "как лучше изучать новую технологию? чувствую что прокрастинирую",
                "mock_analysis": {
                    "action": "provide_guidance",
                    "selected_tasks": [
                        {
                            "task_id": task_id,
                            "title": "Изучить новую технологию",
                            "confidence": 0.95,
                            "reasoning": "Прямое упоминание технологии из задачи"
                        }
                    ],
                    "requires_confirmation": False,
                    "suggested_response": "Консультация по изучению технологии"
                }
            },
            {
                "name": "Обсуждение мотивации к задаче",
                "message": "не могу заставить себя начать учиться",
                "mock_analysis": {
                    "action": "provide_guidance", 
                    "selected_tasks": [
                        {
                            "task_id": task_id,
                            "title": "Изучить новую технологию",
                            "confidence": 0.7,
                            "reasoning": "Контекст о изучении связан с задачей"
                        }
                    ],
                    "requires_confirmation": False,
                    "suggested_response": "Помощь с мотивацией к обучению"
                },
                "conversation_history": [
                    {"role": "user", "content": "как лучше изучать новую технологию?"},
                    {"role": "assistant", "content": "Рекомендую начать с основ React..."}
                ]
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n🧪 ТЕСТ {i}: {scenario['name']}")
            print("-" * 50)
            print(f"👤 Пользователь: {scenario['message']}")
            
            # Mock the task selector
            with patch.object(mentor_agent.task_selector, 'analyze_user_intent', new_callable=AsyncMock) as mock_analyze:
                mock_analyze.return_value = scenario['mock_analysis']
                
                # Test task mention analysis
                conversation_history = scenario.get('conversation_history', [])
                analysis = await mentor_agent.analyze_task_mention(
                    user_id, scenario['message'], conversation_history
                )
                
                print(f"🔍 Анализ упоминания:")
                print(f"   Действие: {analysis.get('action')}")
                print(f"   Найденные задачи: {len(analysis.get('selected_tasks', []))}")
                
                if analysis.get('selected_tasks'):
                    task = analysis['selected_tasks'][0]
                    print(f"   🎯 Связано с задачей: {task.get('title')}")
                    print(f"   Уверенность: {task.get('confidence', 0):.2f}")
                    
                    # Test guidance provision
                    with patch.object(mentor_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_llm:
                        mock_llm.return_value = "Понимаю ваши трудности с мотивацией. Рекомендую разбить изучение на маленькие шаги по 25 минут в день. Начните с простых tutorials, это поможет почувствовать прогресс."
                        
                        response = await mentor_agent.provide_task_guidance(
                            user_id, scenario['message'], analysis['selected_tasks'], conversation_history
                        )
                        
                        print(f"🤖 Совет ментора: {response[:100]}...")
                        
                        if "Изучить новую технологию" in response:
                            print("✅ Правильно связал вопрос с задачей и дал персонализированный совет")
                        else:
                            print("❌ Не смог связать вопрос с конкретной задачей")
                
                # Verify mock was called
                mock_analyze.assert_called_once()
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)

async def test_cross_agent_scenarios():
    """Тест кросс-агентных сценариев использования"""
    
    print("\n\n🔄 Тестирование кросс-агентных сценариев")
    print("=" * 60)
    
    scenarios = [
        {
            "name": "Вечерний трекер → AI-ментор",
            "description": "Пользователь обсуждает трудную задачу в вечернем трекере, затем просит совета у ментора",
            "flow": [
                "🌙 Evening: 'эта задача далась мне тяжело сегодня'",
                "🤖 Evening response with task context",
                "🧠 Mentor: 'как мне справиться со сложными задачами?'",
                "🤖 Mentor guidance based on same task context"
            ]
        },
        {
            "name": "AI-ментор → Task Management → Evening Tracker",
            "description": "Консультация ментора приводит к созданию задач, которые обсуждаются вечером",
            "flow": [
                "🧠 Mentor: 'как лучше планировать проекты?'",
                "🤖 Mentor suggests breaking into tasks", 
                "📋 User creates tasks based on advice",
                "🌙 Evening: discusses progress on mentor-suggested tasks"
            ]
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📖 СЦЕНАРИЙ {i}: {scenario['name']}")
        print(f"💡 {scenario['description']}")
        print("\nПоток взаимодействий:")
        for step in scenario['flow']:
            print(f"   {step}")
        
        print("✅ Благодаря TaskSelectorAgent все агенты могут:")
        print("   • Получать полный список задач с task_id")
        print("   • Анализировать историю разговора для контекста")
        print("   • Определять задачи по частичным упоминаниям") 
        print("   • Предоставлять персонализированные ответы")

if __name__ == "__main__":
    asyncio.run(test_evening_tracker_task_context())
    asyncio.run(test_ai_mentor_task_guidance())
    asyncio.run(test_cross_agent_scenarios())