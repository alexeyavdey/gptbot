#!/usr/bin/env python3
"""
Simple test for notification system functions
"""

import unittest
from unittest.mock import MagicMock, patch
import time
from datetime import datetime, timedelta
import pytz

# Mock the logger before import
with patch('notifications.create_logger') as mock_logger:
    mock_logger.return_value = MagicMock()
    
    from notifications import NotificationManager

class TestNotificationSystem(unittest.TestCase):
    """Test notification system functionality"""
    
    def setUp(self):
        """Setup for each test"""
        self.mock_bot = MagicMock()
        self.notification_manager = NotificationManager(self.mock_bot)
        
        # Mock user data
        self.mock_user_data = MagicMock()
        self.mock_user_data.user_id = 123
        self.mock_user_data.timezone = "Europe/Moscow"
        self.mock_user_data.notifications = {
            'enabled': True,
            'daily_digest': True,
            'deadline_reminders': True,
            'new_task_notifications': True
        }
        self.mock_user_data.tasks = []
        self.mock_user_data.completed = True
    
    def test_notification_manager_init(self):
        """Test NotificationManager initialization"""
        manager = NotificationManager()
        self.assertIsNotNone(manager)
        self.assertFalse(manager.running)
        self.assertEqual(len(manager.notification_handlers), 3)
        self.assertIn("daily_digest", manager.notification_handlers)
        self.assertIn("deadline_reminder", manager.notification_handlers)
        self.assertIn("new_task_notification", manager.notification_handlers)
    
    def test_register_handler(self):
        """Test handler registration"""
        def test_handler():
            pass
        
        self.notification_manager.register_handler("test", test_handler)
        self.assertIn("test", self.notification_manager.notification_handlers)
        self.assertEqual(self.notification_manager.notification_handlers["test"], test_handler)
    
    @patch('schedule.every')
    def test_setup_schedule(self, mock_schedule):
        """Test schedule setup"""
        # Mock the schedule chain
        mock_day = MagicMock()
        mock_hour = MagicMock()
        mock_schedule.return_value.day.at.return_value.do = MagicMock()
        mock_schedule.return_value.hours.do = MagicMock()
        
        # Test that schedule is configured
        self.notification_manager._setup_schedule()
        
        # Verify schedule calls were made
        self.assertTrue(mock_schedule.called)
    
    def test_get_tasks_completed_today(self):
        """Test getting tasks completed today"""
        now = int(time.time())
        yesterday = now - 25 * 60 * 60  # 25 hours ago
        today = now - 2 * 60 * 60      # 2 hours ago
        
        # Mock tasks
        task1 = MagicMock()
        task1.status = "completed"
        task1.completed_at = today  # Completed today
        
        task2 = MagicMock()
        task2.status = "completed"
        task2.completed_at = yesterday  # Completed yesterday
        
        task3 = MagicMock()
        task3.status = "pending"
        task3.completed_at = None
        
        self.mock_user_data.tasks = [task1, task2, task3]
        
        completed_today = self.notification_manager._get_tasks_completed_today(self.mock_user_data)
        
        # Should only return task1 (completed today)
        self.assertEqual(len(completed_today), 1)
        self.assertEqual(completed_today[0], task1)
    
    def test_get_upcoming_deadlines(self):
        """Test getting upcoming deadlines"""
        now = int(time.time())
        soon = now + 12 * 60 * 60     # 12 hours from now
        far = now + 48 * 60 * 60      # 48 hours from now
        
        # Mock tasks
        task1 = MagicMock()
        task1.status = "pending"
        task1.due_date = soon  # Due soon
        
        task2 = MagicMock()
        task2.status = "in_progress"
        task2.due_date = far  # Due far
        
        task3 = MagicMock()
        task3.status = "completed"
        task3.due_date = soon  # Completed, should be ignored
        
        task4 = MagicMock()
        task4.status = "pending"
        task4.due_date = None  # No deadline
        
        self.mock_user_data.tasks = [task1, task2, task3, task4]
        
        # Test 24 hour window
        upcoming = self.notification_manager._get_upcoming_deadlines(self.mock_user_data, 24)
        
        # Should only return task1 (due within 24 hours and not completed)
        self.assertEqual(len(upcoming), 1)
        self.assertEqual(upcoming[0][0], task1)
        self.assertAlmostEqual(upcoming[0][1], 12, delta=1)  # ~12 hours
    
    async def test_notify_new_task(self):
        """Test new task notification"""
        with patch.object(self.notification_manager, '_send_new_task_notification') as mock_send:
            await self.notification_manager.notify_new_task(123, "Test Task")
            mock_send.assert_called_once_with(123, "Test Task")
    
    def test_start_stop_scheduler(self):
        """Test scheduler start/stop"""
        # Test start
        with patch('threading.Thread') as mock_thread:
            self.notification_manager.start_scheduler()
            self.assertTrue(self.notification_manager.running)
            mock_thread.assert_called_once()
        
        # Test stop
        with patch('schedule.clear') as mock_clear:
            self.notification_manager.stop_scheduler()
            self.assertFalse(self.notification_manager.running)
            mock_clear.assert_called_once()
    
    def test_notification_manager_with_bot(self):
        """Test notification manager with bot instance"""
        manager = NotificationManager(self.mock_bot)
        self.assertEqual(manager.bot, self.mock_bot)

def run_notification_tests():
    """Run all notification tests"""
    print("🧪 Testing notification system...")
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNotificationSystem)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("✅ All notification tests passed!")
        return True
    else:
        print("❌ Some notification tests failed!")
        return False

if __name__ == "__main__":
    run_notification_tests()