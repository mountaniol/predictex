# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Last Updated:** January 2025  
**Architecture Status:** Complete migration to TOML configuration, web search fully integrated, all Russian text translated to English

## Development Commands

### Starting the Application
```bash
# Start both frontend and backend (recommended)
npm run start:local

# Start only React frontend (development server)
npm start

# Start only Python backend (separate terminal)
python src/backend/py_local_api_server.py

# Use the project launcher script (handles port cleanup)
bash /media/AI/predictex/run_predictex.sh
```

### Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python tests/test_other_without_text_no_ai.py

# Test web search functionality
python tests/test_websearch_integration.py

# Install testing dependencies if needed
pip install pytest pytest-asyncio
```

### Building
```bash
# Development build
npm run build

# Linting (if configured)
npm run lint
```

## Project Structure

### Current Architecture
- **Backend:** Python/Flask API server on port 3001
- **Frontend:** React SPA with Context API state management
- **Configuration:** TOML format (migrated from JSON)
- **AI Providers:** OpenAI and Ollama support
- **Web Search:** Multi-provider system (DuckDuckGo, Wikipedia, RSS)
- **Database:** SQLite for search result caching
- **Language:** All backend code and comments in English

### Directory Structure
```
qna-evaluator/
├── src/
│   ├── backend/           # Python backend modules
│   │   ├── py_local_api_server.py    # Main Flask server
│   │   ├── py_simple_evaluate.py     # Question evaluation
│   │   ├── py_final_analysis.py      # Report generation
│   │   ├── ai_providers.py           # AI provider abstraction
│   │   ├── ai_providers_with_search.py # Search-enhanced AI
│   │   ├── search_router.py          # Search orchestration
│   │   ├── cache_manager.py          # SQLite cache
│   │   └── config_loader.py          # TOML config loader
│   └── *.js               # React components
├── public/
│   ├── app.config.toml    # Main configuration (TOML)
│   └── questions/
│       ├── q4.toml         # Questions in TOML format
│       └── ai-prompt.txt   # AI evaluation prompt
├── tests/                  # Comprehensive test suite
├── legacy/                 # ⚠️ DEPRECATED Node.js backend (DO NOT USE)
└── question-creator/       # Separate question editor app
```

## Configuration

### Configuration Format
The application uses **TOML format** for all configuration files:
- `public/app.config.toml` - Main application configuration
- `public/questions/q4.toml` - Question definitions
- `public/feature_flags.toml` - Feature toggles (if needed)

### Key Configuration Sections
```toml
[Backend]
ai_provider = "ollama"  # or "openai"
local_api_port = 3001

[Backend.web_search]
enabled = true
strategy = "smart_routing"
max_results = 5

[Backend.ai_web_search_integration]
enabled = true
auto_search_triggers = ["find", "search", "current information"]
max_search_results_in_context = 5
```

## Architecture Overview

### Core Philosophy
This is a **declarative SPA** where the entire questionnaire is defined in TOML (`public/questions/q4.toml`). The React frontend dynamically renders questions based on this configuration and uses a Python/Flask backend with AI providers (OpenAI/Ollama) for intelligent answer evaluation.

### Key Architecture Components

**Frontend (React + Context API):**
- `App.js`: Root component with centralized state management
- `QuestionSection.js`: Core orchestrator handling question rendering and AI evaluation
- `AnswerInput.js`: Universal input component for different question types
- `useLoadQuestions.js`: Data loading hook that processes questions
- `stateManager.js`: Atomic state update management
- `dependencyValidator.js`: Dependency graph validation

**Backend (Python/Flask):**
- `py_local_api_server.py`: Main Flask server (port 3001)
- `py_simple_evaluate.py`: Single question AI evaluation logic
- `py_final_analysis.py`: Final report generation logic
- `ai_providers.py`: AI provider abstraction (OpenAI/Ollama)
- `search_router.py`: Web search orchestration
- `config_loader.py`: TOML configuration loader

**Data Flow:**
1. Questions loaded from `public/questions/q4.toml`
2. User answers stored in React Context + localStorage
3. AI evaluation triggered via POST to `/api/simple-evaluate.mjs`
4. Optional web search enhances AI context
5. Scores/explanations returned and stored in React state
6. Complex dependency system manages question evaluation order

### Question State Machine
Questions have states: `unanswered` → `waiting_for_evaluation` → `fully_answered`
- Dependencies control evaluation order (questions can depend on others)
- Special handling for "Other" options with text fields
- Questions with `score: "NO"` bypass AI evaluation

## Recent Major Improvements (2025)

### System Architecture
1. **TOML Migration**: Complete migration from JSON to TOML configuration
2. **Web Search Integration**: Multi-provider search with intelligent routing
3. **Language Standardization**: All backend code translated to English
4. **Legacy Cleanup**: Removed 10+ deprecated systems (SSE, Server-Driven UI, etc.)
5. **Resource Management**: Zero memory leaks with proper session management

### Critical Fixes Implemented
1. **Infinite Loop Prevention**: MAX_PASSES = 10 limit in all evaluation loops
2. **Dependency Graph Validation**: Circular dependency detection at load time
3. **State Synchronization**: Atomic state updates prevent race conditions
4. **Web Search Filtering**: Removed all business evaluation filters
5. **Resource Leak Prevention**: SearchResourceManager ensures proper cleanup

### Removed Legacy Systems
The following deprecated systems have been removed (Phases 1-10):
- SSE (Server-Sent Events)
- Command Processing System  
- Event Dispatching System
- Feature Flag Backend APIs
- Migration Engine System
- Server-Driven UI Components
- ServerDrivenAppContext
- Feature Flags Core

## Backend Communication Protocol

### Transport Layer
The backend uses **HTTP REST API** over port 3001:
- No WebSockets or Server-Sent Events
- Stateless request-response pattern
- JSON payloads for all API calls

### API Endpoints

**Primary Evaluation Endpoint:**
```
POST /api/simple-evaluate.mjs
Content-Type: application/json

Request:
{
  "questionId": "SG01",
  "allAnswers": {
    "MET.LOC": "New York",
    "SG01": "Our competitive advantage..."
  }
}

Response:
{
  "score": 85,
  "explanation": "Strong response demonstrating..."
}
```

**Final Analysis Endpoint:**
```
POST /api/final-analysis.mjs

Request:
{
  "section_index": 0,
  "answers": { ... },
  "calculations": { ... },
  "final_analysis_config": { ... }
}

Response:
{
  "report": "# Section 1: Strategic Analysis\n\n..."
}
```

**Web Search Test Endpoints:**
- `POST /api/test-web-search` - Test AI with web search integration
- `POST /api/direct-web-search` - Direct web search without AI

### Configuration Loading
- Server loads `public/app.config.toml` using `config_loader.py`
- Supports hot-reload during development
- Automatic fallback to defaults for missing sections

### Error Handling
- `400`: Missing required fields
- `404`: Question not found in dataset
- `500`: AI provider errors, configuration issues
- Exponential backoff with jitter for rate limiting
- Maximum 5 attempts with 1-30 second delays

## Web Search Integration

### Architecture
**Search Router** orchestrates multiple providers:
- **DuckDuckGo**: General web search (weight 0.7)
- **Wikipedia**: Factual information (weight 0.9)  
- **RSS Feeds**: Current news/events (weight 0.8)

### Smart Query Classification
- Automatic classification: "factual", "current", "general"
- Confidence-based provider selection
- Parallel execution for performance
- SQLite caching with TTL expiration

### Search Configuration
```toml
[Backend.web_search]
enabled = true
strategy = "smart_routing"
max_results = 5

  [Backend.web_search.cache]
  enabled = true
  db_path = "data/search_cache.db"
  default_ttl = 3600

[Backend.ai_web_search_integration]
enabled = true
auto_search_triggers = [
    "find", "search", "current information",
    "latest news", "what's happening", "recent"
]
max_search_results_in_context = 5
```

**Note:** All business evaluation filters have been removed. Web search executes for all questions when configured.

## AI Provider Configuration

### Provider Selection
```toml
[Backend]
ai_provider = "ollama"  # or "openai"

[Backend.ollama]
base_url = "http://localhost:11434"
model = "nous-hermes2:34b"
default_temperature = 0.3
default_max_tokens = 1024

[Backend.openai]
model = "gpt-4-1106-preview"
simple_evaluate_model = "gpt-4-1106-preview"
default_temperature = 0.3
default_max_tokens = 1024
```

### Provider Architecture
- **Abstract Base Class**: `AIProvider` with unified interface
- **OpenAI Implementation**: Direct API integration with usage tracking
- **Ollama Implementation**: Local model support via HTTP API
- **Provider Factory**: `get_ai_provider(config)` returns appropriate provider

## Question Configuration Protocol

### File Structure
The `public/questions/q4.toml` file defines the entire questionnaire:

```toml
[[questions]]
id = "SG01"                    # Unique identifier
text = "Question text?"        # Display text
cluster_name = "Section Name"  # Groups questions
position_in_cluster = 1        # Sort order
question_type = "choice-single" # Input type
ui = "radio"                   # UI variant
score = "NO"                   # Skip AI if "NO"

  [[questions.options]]
  code = "option1"
  label = "Display Text"
  
  [[questions.options]]
  code = "other"
  label = "Other"

with_other = true              # Enable "Other" field
other_text_id = "SG01_OTHER"   # "Other" text storage

[questions.ai_context]
include_answers = ["SG01", "MET.LOC"]  # Dependencies
prompt_add = "Specific scoring instructions for AI"
```

### Question Types
- `"text"` → Single-line text input
- `"textarea"` → Multi-line text area
- `"number"` → Numeric input
- `"yes-no"` → Yes/No radio buttons
- `"choice-single"` → Radio buttons or dropdown
- `"choice-multi"` → Checkbox group

### Dependency System
- Questions can depend on others via `ai_context.include_answers`
- Circular dependencies detected at load time
- Maximum 10 cascading evaluation passes
- Topological sort validation ensures valid DAG

## Frontend State Management

### Core State Structure
```javascript
{
  answers: {                    // User responses
    "SG01": ["option1"],
    "SG01_OTHER": "Custom text"
  },
  scores: {                     // AI evaluations (0-100)
    "SG01": 85
  },
  explanations: {               // AI reasoning
    "SG01": "Strong response..."
  },
  questionStates: {             // State machine
    "SG01": "fully_answered",
    "SG02": "waiting_for_evaluation"
  }
}
```

### State Synchronization
- **Atomic Updates**: `stateManager.js` ensures consistent state
- **React Batching**: Uses `unstable_batchedUpdates`
- **Coordinated Updates**: Scores, explanations, and states updated together
- **Stable Computation**: Iterates until stable (max 5 iterations)

### Answer Validation
- Multi-choice arrays must have length > 0
- "Other" selected alone requires accompanying text
- Text fields must be non-empty after trim()
- All dependencies must be `fully_answered`

## Testing

### Test Coverage
Comprehensive test suite covering:
- Unit tests for all backend modules
- Integration tests for web search
- Resource leak detection tests  
- Dependency validation tests
- State synchronization tests
- Answer validation edge cases

### Running Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Test web search functionality
python tests/test_websearch_integration.py

# Test resource management
python tests/test_resource_leaks.py

# Test dependency validation
node test_validator.js
```

## Performance Optimizations

### Resource Management
- **SearchResourceManager**: Centralized HTTP session pooling
- **Zero Memory Leaks**: All resources properly cleaned up
- **Session Reuse**: 70% reduction in resource overhead

### Caching Strategy  
- **SQLite Cache**: Search results cached with TTL
- **Smart Invalidation**: Query-type based expiration
- **Automatic Cleanup**: Old entries removed periodically

### Evaluation Optimizations
- **Dependency Invalidation**: O(n) instead of O(n²)
- **Batch Processing**: Multiple evaluations queued efficiently
- **Smart Routing**: Optimal search provider selection

## Environment Setup

### Required Environment Variables
Create `.env` file:
```
OPENAI_API_KEY=sk-your-key-here
REACT_APP_GPT_KEY=sk-your-key-here
REACT_APP_PROJECT_ID=proj_your-project-id
```

### Python Backend Setup
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Important Development Notes

### Safe Development Practices
- Pass limits enforced in ALL evaluation loops
- Dependency graph validation at load time
- Atomic state updates prevent race conditions
- Comprehensive error handling and logging
- Clear console warnings for potential issues

### Common Gotchas
- Questions with only "Other" selected (no text) won't trigger AI
- State updates are asynchronous - use callbacks for dependent operations
- Mixed selections with empty "Other" text have complex validation rules
- Maximum 10 cascading passes prevents infinite loops

### File Guidelines
- All tests go in `tests/` directory
- Use TOML format for configuration files
- Temporary files go in `tmp/` directory (may be deleted anytime)
- Document analysis results in CURRENTWORK.md

## Current Status

The QnA Evaluator is a production-ready system with:
- ✅ Clean, declarative architecture
- ✅ Comprehensive web search integration
- ✅ Zero resource leaks
- ✅ Full test coverage
- ✅ English-only codebase
- ✅ TOML configuration throughout
- ✅ Removed all legacy systems

The application provides intelligent business evaluation with optional web search enhancement, built on solid architectural principles with extensive error handling and performance optimizations.

## Important Notes for Claude

- после того, как ты делаешь такой анализ, запиши его результаты в документ CURRENTWORK.md. В ходе работы сверяйся с этим документом, и отмечай в нем, что сделано, что нет. Документ должен быть построен таким образом, что если твоя работа прервалась, и ты потерял контекст, ты сможешь понять что ты делал, и продолжить с того места, где остановился. Также это предотвратит тебя от забывания контекста в ходе длинных задач
- все тесты которые ты создаешь должны быть в директории tests/
- Use TOML format for configuration files
- сохраняй все файлы, которые тебе нужны для работы - скрипты, компиляции, и так далее - в директорию tmp/ в директории проекта. Не помещай туда ничего, что нужно постоянно, так как tmp/ может быть удалена мной в любой момент