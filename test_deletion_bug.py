#!/usr/bin/env python3
"""
Test script to reproduce the task deletion bug from the dialog.
Dialog shows task deletion failing with error message.
"""

import asyncio
import os
import sys
import tempfile
import json
from unittest.mock import AsyncMock, patch

# Add the project root to Python path  
sys.path.insert(0, '/Users/alexonic/Documents/project/gptbot')

from enhanced_ai_agents import initialize_enhanced_agents, TaskManagementAgent
from task_database import TaskDatabase

async def test_task_deletion_fix():
    """Test the fixed task deletion functionality"""
    
    print("🧪 Testing Fixed Task Deletion")
    print("=" * 50)
    
    # Create temporary database for testing
    temp_db = tempfile.mktemp(suffix='.db')
    
    try:
        # Initialize database 
        db = TaskDatabase(temp_db)
        
        # Initialize task management agent directly
        api_key = os.getenv('API_KEY') or 'test-key'
        task_agent = TaskManagementAgent(api_key=api_key, model="gpt-4")
        task_agent.db = db  # Set the database
        
        user_id = 123456  # Test user ID
        
        print("1. Creating task manually in database...")
        
        # Create task directly in database
        db.ensure_user_exists(user_id)
        task_id = db.create_task(
            user_id=user_id,
            title="Стратегия сайта Банка — презентация для Влада",
            description="Сделать презентацию для Влада", 
            priority="high"
        )
        
        print(f"Created task with ID: {task_id}")
        
        # Verify task was created
        tasks = db.get_tasks(user_id)
        print(f"Tasks in database: {len(tasks)}")
        if tasks:
            task = tasks[0]
            print(f"Task ID: {task['id']}, Title: {task['title']}")
        
        print("\n2. Testing deletion by title (THIS IS THE BUG FIX)...")
        
        # Test deletion by title (this is where the bug was)
        delete_params = json.dumps({
            "user_id": user_id,
            "task_title": "стратегия"  # Should match partial title
        })
        
        delete_result = task_agent._delete_task(delete_params)
        print(f"Delete result: {delete_result}")
        
        # Parse the JSON result
        try:
            delete_data = json.loads(delete_result)
            print(f"Delete data: {delete_data}")
        except:
            print(f"Delete result is not JSON: {delete_result}")
            delete_data = {"success": "удалена" in delete_result.lower()}
        
        # Check if task was actually deleted
        tasks_after = db.get_tasks(user_id)
        print(f"Tasks after deletion: {len(tasks_after)}")
        
        # Analyze the result
        if len(tasks_after) == 0:
            print("✅ BUG FIXED: Task deletion by title now works!")
        else:
            print("❌ Bug still exists - task was not deleted")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        if os.path.exists(temp_db):
            os.remove(temp_db)

async def analyze_deletion_code():
    """Analyze the delete_task implementation"""
    print("\n🔍 Analyzing delete_task implementation...")
    
    # Read the enhanced_ai_agents.py file to check delete logic
    try:
        with open('/Users/alexonic/Documents/project/gptbot/enhanced_ai_agents.py', 'r') as f:
            content = f.read()
            
        # Look for delete_task function
        if 'def delete_task(' in content:
            print("✅ Found delete_task function definition")
            
            # Extract the function for analysis
            lines = content.split('\n')
            in_delete_func = False
            func_lines = []
            indent_level = None
            
            for line in lines:
                if 'def delete_task(' in line:
                    in_delete_func = True
                    indent_level = len(line) - len(line.lstrip())
                    func_lines.append(line)
                elif in_delete_func:
                    if line.strip() == '' or len(line) - len(line.lstrip()) > indent_level:
                        func_lines.append(line)
                    else:
                        break
                        
            print("delete_task function:")
            for line in func_lines[:20]:  # Show first 20 lines
                print(line)
                
        else:
            print("❌ delete_task function not found!")
            
    except Exception as e:
        print(f"❌ Error reading file: {e}")

if __name__ == "__main__":
    asyncio.run(test_task_deletion_fix())
    asyncio.run(analyze_deletion_code())