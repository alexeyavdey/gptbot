# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot that integrates OpenAI's Assistant API with aiogram 3.4+. The bot supports multiple assistants, voice messages via Whisper, PDF processing with RAG, and voice calls through Vapi.ai integration.

## Development Commands

**Run the bot:**
```bash
python -m gptbot
```

**Run tests:**
```bash
pip install pytest pytest-asyncio freezegun
pytest -vv test.py
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

## Architecture

### Core Components

- **handlers.py**: Main aiogram router with message handlers and middleware
- **actions.py**: OpenAI Assistant API interactions and message processing logic
- **client.py**: OpenAI client setup and thread/assistant management
- **assistants_factory.py**: Assistant management with YAML persistence
- **users.py**: User access control and allowed users management
- **modes.py**: Bot operation modes (assistant, gpt-4.1, o4-mini)
- **file_search.py**: PDF processing and RAG functionality
- **voice.py**: Voice message transcription via Whisper
- **message_queues.py**: Request queuing and rate limiting

### Configuration Files

- **tutors.yaml**: Assistant configurations and user preferences
- **threads.yaml**: Thread state persistence
- **allowed_users.yaml**: User access control list
- **config.py**: Bot behavior settings (response delays, polling intervals)
- **env.py**: Environment variable definitions

### Message Flow

1. Messages arrive via aiogram handlers in `handlers.py`
2. Access control checked via `users.py` middleware
3. Thread/assistant retrieved via `client.py` and `assistants_factory.py`
4. Mode-specific processing in `actions.py` (Assistant API vs direct model calls)
5. Queue management via `message_queues.py` for rate limiting
6. Response formatting and delivery

### Key Patterns

- All user state persisted in YAML files (threads, assistants, users)
- Async/await throughout with proper exception handling
- Markdown formatting with aiogram ParseMode.MARKDOWN
- File download to temporary directory with cleanup
- Voice transcription and PDF RAG as optional features

## Environment Variables

Set these before running:
- `BOT_TOKEN`: Telegram bot token
- `API_KEY`: OpenAI API key  
- `ORG_ID`: OpenAI organization ID
- `LOG_LEVEL`: Logging verbosity (default: INFO)
- `WEBAPP_URL`: Mini app URL for web interface
- `VAPI_API_KEY`: Vapi.ai API key (optional)
- `VAPI_ASSISTANT_ID`: Vapi.ai assistant ID (optional)