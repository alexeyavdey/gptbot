# Bug Fix: None Values in Analytics Calculation

## Problem
```
ERROR:gptbot:Error getting user state: unsupported operand type(s) for -: 'int' and 'NoneType'
```

User reported error when asking "у меня есть задачи?" - the system crashed when calculating analytics for users with no tasks.

## Root Cause
1. **SQL NULL Values**: When user has no tasks, SQL `SUM()` functions return `NULL` instead of `0`
2. **Arithmetic Operations**: Python cannot subtract `None` from `int` 
3. **Missing Protection**: No null-safety checks in analytics processing

## Files Fixed

### 1. task_database.py
**Problem**: SQL query returned `NULL` for empty results
```sql
-- Before (problematic)
SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks

-- After (fixed)  
COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) as completed_tasks
```

**Additional protection** in completion rate calculation:
```python
# Before
total = stats['total_tasks'] 
completed = stats['completed_tasks']

# After
total = stats.get('total_tasks', 0) or 0
completed = stats.get('completed_tasks', 0) or 0
```

### 2. enhanced_ai_agents.py - OrchestratorAgent._get_user_state()
**Problem**: Arithmetic operations with potential `None` values
```python
# Before (crashed)
"active_tasks": analytics.get('total_tasks', 0) - analytics.get('completed_tasks', 0)

# After (safe)
total_tasks = analytics.get('total_tasks', 0) or 0
completed_tasks = analytics.get('completed_tasks', 0) or 0
"active_tasks": total_tasks - completed_tasks
```

### 3. enhanced_ai_agents.py - AIMentorAgent._get_user_context()
**Added null-safety protection**:
```python
# Before
"total_tasks": analytics.get('total_tasks', 0)

# After  
"total_tasks": analytics.get('total_tasks', 0) or 0
```

## Solution Strategy
1. **Database Level**: Use `COALESCE()` to ensure SQL never returns `NULL`
2. **Application Level**: Double protection with `get(key, default) or default`
3. **Calculation Level**: Explicit variable assignment before arithmetic operations

## Testing
Created `test_fix.py` to verify:
- ✅ Database analytics returns proper integers for empty users
- ✅ User state calculation works without crashes  
- ✅ AI mentor context handles empty scenarios

## Impact
- **Before**: Bot crashed for users with no tasks asking about task status
- **After**: Bot gracefully handles empty task lists with proper zero values
- **Users**: Can now safely ask about tasks even when they have none

## Status: FIXED ✅
The error is completely resolved and users can query task status regardless of whether they have tasks or not.