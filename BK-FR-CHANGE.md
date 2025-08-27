# Server-Driven UI Migration Plan with Test-Driven Development
**Version:** 1.0
**Date:** 2025-01-27
**Project:** QnA Evaluator Server-Driven UI Architecture

---

## 1. EXECUTIVE SUMMARY

### Problem Statement
The current QnA Evaluator has a **thick client architecture** where the React frontend contains significant business logic:
- **Dependency Management**: Frontend calculates question dependencies and evaluation order
- **State Computation**: Frontend determines when to trigger AI evaluations
- **Validation Logic**: Answer validation spread across multiple frontend components
- **Flow Control**: Question flow and cascading updates managed client-side
- **Score Calculations**: Frontend applies complex calculation formulas

This results in:
- **Duplicated Logic**: Business rules exist in both frontend and backend
- **Maintenance Burden**: Changes require coordinated updates to multiple files
- **Testing Complexity**: Business logic tests mixed with UI tests
- **Poor Separation of Concerns**: Frontend knows too much about business domain

### Goal Definition
Transform into a **Server-Driven UI architecture** where:
- **Backend as Brain**: All business logic, dependency management, and flow control in backend
- **Frontend as Display**: Pure rendering based on server commands
- **Protocol-Based**: Standardized command/event protocol for communication
- **Stateless Frontend**: No business logic, just UI state and rendering

### Success Criteria
✅ **Zero Business Logic in Frontend**: All logic moved to backend
✅ **100% Test Coverage**: Complete TDD with test-first approach
✅ **Protocol Documentation**: Clear command/event specification
✅ **Performance Maintained**: No degradation in user experience
✅ **Gradual Migration**: System remains functional during migration
✅ **Easy Rollback**: Feature flags for instant rollback if needed

---

## 2. ARCHITECTURE OVERVIEW

### Current Architecture (AS-IS)

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                      │
│  ┌─────────────────────────────────────────────────┐    │
│  │         Business Logic (QuestionSection.js)      │    │
│  │  - Dependency calculation                        │    │
│  │  - Evaluation triggering                         │    │
│  │  - Answer validation                             │    │
│  │  - State computation                             │    │
│  │  - Score calculations                            │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │              UI Components                       │    │
│  │  - AnswerInput.js                               │    │
│  │  - SidebarResults.js                            │    │
│  │  - FinalReport.js                               │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                            │
                    HTTP REST API
                            │
┌─────────────────────────────────────────────────────────┐
│                    BACKEND (Python)                      │
│  ┌─────────────────────────────────────────────────┐    │
│  │           Simple AI Evaluation                   │    │
│  │  - Single question evaluation                    │    │
│  │  - Score + explanation                          │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

**Problems with Current Approach:**
1. **Logic Duplication**: Validation rules in 3+ places
2. **Complex Testing**: UI tests entangled with business tests
3. **Difficult Debugging**: Logic spread across multiple files
4. **High Coupling**: Components tightly coupled to business rules
5. **Limited Flexibility**: Hard to change business rules without UI changes

### Target Architecture (TO-BE)

```
┌─────────────────────────────────────────────────────────┐
│                THIN CLIENT (React)                       │
│  ┌─────────────────────────────────────────────────┐    │
│  │          Command Processor                       │    │
│  │  - Receives UI commands from server              │    │
│  │  - Sends user events to server                   │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │          Pure UI Renderers                       │    │
│  │  - Render components based on UI schema          │    │
│  │  - No business logic, only presentation          │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                            │
                    SSE + HTTP REST
                            │
┌─────────────────────────────────────────────────────────┐
│              SMART SERVER (Python)                       │
│  ┌─────────────────────────────────────────────────┐    │
│  │          Session Manager                         │    │
│  │  - User session state                           │    │
│  │  - Answer persistence                           │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │          Dependency Engine                       │    │
│  │  - Question dependencies                        │    │
│  │  - Evaluation order                             │    │
│  │  - Cascade detection                            │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │          Command Generator                       │    │
│  │  - UI update commands                           │    │
│  │  - State synchronization                        │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │          Business Logic Core                     │    │
│  │  - Answer validation                            │    │
│  │  - Score calculations                           │    │
│  │  - AI evaluation orchestration                  │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### Key Architecture Decisions

**1. Why Server-Driven UI:**
- **Single Source of Truth**: All business logic in one place
- **Easier Testing**: Business logic isolated from UI
- **Better Maintainability**: Changes in one location
- **Platform Flexibility**: Same backend can serve web, mobile, CLI

**2. Protocol Choice Rationale:**
- **Server-Sent Events (SSE)**: For server → client commands
  - Simple, HTTP-based, automatic reconnection
  - No WebSocket complexity, works through proxies
- **HTTP REST**: For client → server events
  - Stateless, simple, well-understood
  - Easy to test and debug

**3. Session Management Approach:**
- **Server-side sessions**: UUID-based session tracking
- **Persistent storage**: SQLite for session data
- **Automatic cleanup**: TTL-based session expiry

**4. Real-time Communication Strategy:**
- **Push-based updates**: Server pushes UI changes via SSE
- **Event-driven**: User actions trigger server processing
- **Optimistic UI**: Immediate visual feedback with server confirmation

---

## 3. PROTOCOL SPECIFICATION

### Command Protocol Design

#### RENDER Commands (Server → Client)
```typescript
interface RenderCommand {
  type: 'RENDER';
  component: 'question' | 'section' | 'results' | 'report';
  data: {
    id: string;
    schema: UISchema;
    props: Record<string, any>;
  };
}

// Example: Render a question
{
  "type": "RENDER",
  "component": "question",
  "data": {
    "id": "SG01",
    "schema": {
      "type": "choice-multi",
      "label": "What are the main challenges?",
      "options": ["option1", "option2", "other"],
      "validation": {
        "required": true,
        "min": 1,
        "max": 3
      }
    },
    "props": {
      "value": ["option1"],
      "disabled": false,
      "thinking": false
    }
  }
}
```

#### UPDATE Commands (Server → Client)
```typescript
interface UpdateCommand {
  type: 'UPDATE';
  target: string;  // Component ID
  updates: {
    path: string;  // JSON path to update
    value: any;    // New value
  }[];
}

// Example: Update question state
{
  "type": "UPDATE",
  "target": "SG01",
  "updates": [
    {"path": "props.thinking", "value": true},
    {"path": "props.disabled", "value": true}
  ]
}
```

#### EVENT Handling (Client → Server)
```typescript
interface UserEvent {
  type: 'USER_EVENT';
  event: 'answer_change' | 'answer_blur' | 'submit' | 'navigation';
  data: {
    questionId?: string;
    value?: any;
    metadata?: Record<string, any>;
  };
}

// Example: User changes answer
{
  "type": "USER_EVENT",
  "event": "answer_change",
  "data": {
    "questionId": "SG01",
    "value": ["option1", "option2"]
  }
}
```

#### State Synchronization
```typescript
interface StateSync {
  type: 'STATE_SYNC';
  state: {
    session_id: string;
    questions: Record<string, QuestionState>;
    scores: Record<string, number>;
    explanations: Record<string, string>;
  };
}
```

### Data Schema

#### UI Schema Format
```typescript
interface UISchema {
  type: 'text' | 'number' | 'choice-single' | 'choice-multi' | 'textarea';
  label: string;
  hint?: string;
  info?: string;
  options?: Array<{code: string; label: string}>;
  validation?: {
    required?: boolean;
    min?: number;
    max?: number;
    pattern?: string;
  };
  conditional?: {
    show_when: string;  // DSL expression
  };
}
```

#### Event Format
```typescript
interface EventEnvelope {
  id: string;        // UUID for tracking
  timestamp: number;
  session_id: string;
  payload: UserEvent | ServerCommand;
}
```

#### Response Format
```typescript
interface ApiResponse {
  success: boolean;
  data?: any;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
}
```

---

## 4. BACKEND ARCHITECTURE CHANGES

### New Components

#### Session Manager
```python
class SessionManager:
    """Manages user sessions and state persistence"""
    - create_session() -> str
    - get_session(session_id: str) -> SessionData
    - update_session(session_id: str, updates: dict)
    - cleanup_expired_sessions()
```

#### Dependency Engine
```python
class DependencyEngine:
    """Manages question dependencies and evaluation order"""
    - build_dependency_graph(questions: List[Question])
    - get_evaluation_order(changed_question: str) -> List[str]
    - detect_cascades(answers: dict) -> List[str]
    - validate_dependencies() -> List[str]  # Errors
```

#### Command Generator
```python
class CommandGenerator:
    """Generates UI commands based on state changes"""
    - generate_render_command(question: Question) -> RenderCommand
    - generate_update_command(changes: StateChange) -> UpdateCommand
    - generate_state_sync() -> StateSync
```

#### UI Schema Generator
```python
class UISchemaGenerator:
    """Converts questions to UI schemas"""
    - question_to_schema(question: Question) -> UISchema
    - apply_conditionals(schema: UISchema, answers: dict) -> UISchema
    - validate_schema(schema: UISchema) -> bool
```

#### Event Handler
```python
class EventHandler:
    """Processes client events and triggers actions"""
    - handle_answer_change(event: UserEvent) -> List[Command]
    - handle_submit(event: UserEvent) -> List[Command]
    - handle_navigation(event: UserEvent) -> List[Command]
```

#### Communication Layer
```python
class SSEManager:
    """Manages Server-Sent Events connections"""
    - register_client(session_id: str) -> SSEClient
    - send_command(session_id: str, command: Command)
    - broadcast(command: Command)
    - cleanup_disconnected()
```

### API Design

#### New Endpoints
```python
# Session Management
POST   /api/session/create
GET    /api/session/:id
DELETE /api/session/:id

# Server-Sent Events
GET    /api/sse/:session_id

# Event Processing
POST   /api/event
{
  "session_id": "uuid",
  "event": {...}
}

# State Query
GET    /api/state/:session_id
GET    /api/ui-schema/:session_id
```

---

## 5. FRONTEND ARCHITECTURE CHANGES

### Components to Remove
1. **Business Logic in QuestionSection.js:**
   - `applyCalculations()` function
   - `findNextQuestionToReevaluate()` function
   - Dependency checking logic
   - Evaluation trigger logic

2. **State Computation:**
   - Question state determination
   - Cascading update detection
   - Validation logic

3. **Complex Refs:**
   - `lastEvaluatedAnswers`
   - `evaluationInProgress`
   - Manual dependency tracking

### New Components

#### Command Processor
```typescript
class CommandProcessor {
  processCommand(command: Command): void {
    switch(command.type) {
      case 'RENDER':
        this.handleRender(command);
        break;
      case 'UPDATE':
        this.handleUpdate(command);
        break;
      case 'STATE_SYNC':
        this.handleStateSync(command);
        break;
    }
  }
}
```

#### Event Dispatcher
```typescript
class EventDispatcher {
  dispatch(event: UserEvent): void {
    fetch('/api/event', {
      method: 'POST',
      body: JSON.stringify({
        session_id: this.sessionId,
        event
      })
    });
  }
}
```

#### Pure UI Renderers
```typescript
// Before: Complex logic
const QuestionRenderer = ({ question, answer, onAnswer }) => {
  // 100+ lines of logic
  const isValid = validateAnswer(answer);
  const shouldEvaluate = checkDependencies(question);
  // ...
}

// After: Pure rendering
const QuestionRenderer = ({ schema, value, onChange }) => {
  // Just render based on schema
  return <Input {...schema} value={value} onChange={onChange} />;
}
```

---

## 6. IMPLEMENTATION PLAN WITH TDD

### Phase 1: Backend Foundation (Weeks 1-2)

#### Task 1.1: Session Manager
**Specification:** Manages user sessions with persistence and expiry

**Test First:**
```bash
# Create test file
tests/test_session_manager.py
```

**Test Cases:**
```python
def test_create_session():
    """Session creation returns UUID and persists data"""
    
def test_get_session():
    """Retrieve session by ID returns correct data"""
    
def test_update_session():
    """Update session modifies persisted data"""
    
def test_session_expiry():
    """Expired sessions are cleaned up automatically"""
    
def test_concurrent_sessions():
    """Multiple sessions work independently"""
```

**Implementation:**
```python
# src/backend/session_manager.py
class SessionManager:
    def __init__(self, db_path='sessions.db'):
        self.db = sqlite3.connect(db_path)
        self._init_schema()
```

**Verification:**
```bash
pytest tests/test_session_manager.py -v
```

**Integration:** Connect to Flask app in request context

---

#### Task 1.2: Dependency Engine
**Specification:** Manages question dependencies and evaluation order

**Test First:**
```bash
# Create test file
tests/test_dependency_engine.py
```

**Test Cases:**
```python
def test_build_dependency_graph():
    """Correctly builds DAG from questions"""
    
def test_topological_sort():
    """Returns valid evaluation order"""
    
def test_circular_dependency_detection():
    """Detects and reports circular dependencies"""
    
def test_cascade_detection():
    """Identifies all affected questions when one changes"""
    
def test_missing_dependency_handling():
    """Gracefully handles missing dependencies"""
```

**Implementation:**
```python
# src/backend/dependency_engine.py
class DependencyEngine:
    def __init__(self):
        self.graph = {}
        self.reverse_graph = {}
```

**Verification:**
```bash
pytest tests/test_dependency_engine.py -v
```

---

#### Task 1.3: Command Generator
**Specification:** Generates UI commands from state changes

**Test First:**
```bash
tests/test_command_generator.py
```

**Test Cases:**
```python
def test_render_command_generation():
    """Generates correct RENDER commands"""
    
def test_update_command_generation():
    """Generates correct UPDATE commands"""
    
def test_batch_command_generation():
    """Batches multiple updates efficiently"""
    
def test_state_sync_generation():
    """Generates complete state sync"""
```

---

#### Task 1.4: UI Schema Generator
**Test First:**
```bash
tests/test_ui_schema_generator.py
```

**Test Cases:**
```python
def test_text_question_schema():
    """Converts text questions to UI schema"""
    
def test_choice_question_schema():
    """Converts choice questions with options"""
    
def test_conditional_schema():
    """Applies conditional visibility rules"""
    
def test_validation_rules():
    """Includes validation in schema"""
```

---

### Phase 2: Protocol Implementation (Week 3)

#### Task 2.1: SSE Communication Layer
**Test First:**
```bash
tests/test_sse_communication.py
```

**Test Cases:**
```python
def test_sse_connection():
    """Client can establish SSE connection"""
    
def test_command_streaming():
    """Commands stream to connected clients"""
    
def test_reconnection():
    """Client reconnects after disconnect"""
    
def test_heartbeat():
    """Keepalive prevents timeout"""
```

---

#### Task 2.2: Event Handler
**Test First:**
```bash
tests/test_event_handler.py
```

**Test Cases:**
```python
def test_answer_change_event():
    """Process answer change events"""
    
def test_validation_on_blur():
    """Validate and trigger evaluation on blur"""
    
def test_cascade_triggering():
    """Dependent questions evaluate after change"""
```

---

### Phase 3: Frontend Refactoring (Weeks 4-5)

#### Task 3.1: Command Processor
**Test First:**
```bash
tests/test_command_processor.test.js
```

**Test Cases:**
```javascript
describe('CommandProcessor', () => {
  test('processes RENDER commands')
  test('processes UPDATE commands')
  test('processes STATE_SYNC commands')
  test('queues commands during processing')
})
```

---

#### Task 3.2: Event Dispatcher
**Test First:**
```bash
tests/test_event_dispatcher.test.js
```

**Test Cases:**
```javascript
describe('EventDispatcher', () => {
  test('sends events to backend')
  test('includes session ID')
  test('handles network errors')
  test('retries failed events')
})
```

---

#### Task 3.3: Pure UI Components
**Test First:**
```bash
tests/test_pure_components.test.js
```

**Test Cases:**
```javascript
describe('Pure UI Components', () => {
  test('renders based on schema only')
  test('no business logic in components')
  test('dispatches events on user interaction')
})
```

---

### Phase 4: Integration & Migration (Week 6)

#### Task 4.1: End-to-End Testing
**Test First:**
```bash
tests/test_e2e_server_driven.py
```

**Test Cases:**
```python
def test_complete_questionnaire_flow():
    """User can complete entire questionnaire"""
    
def test_dependency_cascades():
    """Dependencies evaluate correctly"""
    
def test_session_persistence():
    """Answers persist across sessions"""
    
def test_concurrent_users():
    """Multiple users work simultaneously"""
```

---

#### Task 4.2: Performance Testing
**Test First:**
```bash
tests/test_performance.py
```

**Test Cases:**
```python
def test_command_latency():
    """Commands process within 100ms"""
    
def test_sse_throughput():
    """SSE handles 100+ clients"""
    
def test_memory_usage():
    """No memory leaks with sessions"""
```

---

## 7. TESTING STRATEGY

### Test Pyramid
```
         /\
        /E2E\      10% - End-to-end tests
       /______\
      /        \
     /Integration\ 20% - Integration tests  
    /____________\
   /              \
  /   Unit Tests   \ 70% - Unit tests
 /__________________\
```

### Continuous Testing

#### Backend Testing
```bash
# Install test watcher
pip install pytest-watch

# Run tests continuously
pytest-watch tests/ --clear --nobeep

# With coverage
pytest-watch tests/ --cov=src --cov-report=term-missing
```

#### Frontend Testing
```bash
# Run tests with watch
npm test -- --watchAll

# With coverage
npm test -- --coverage --watchAll=false
```

### CI/CD Pipeline
```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v1
  
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: npm install
      - run: npm test -- --coverage
```

### Coverage Requirements
- **Minimum:** 80% overall coverage
- **Backend Core:** 95% coverage required
- **Protocol:** 100% coverage required
- **UI Components:** 70% coverage acceptable

### Test Commands
```bash
# Backend continuous testing
pytest tests/ --watch

# Frontend continuous testing  
npm test -- --watch

# Coverage reports
pytest --cov=src tests/
npm test -- --coverage

# Integration tests only
pytest tests/ -m integration

# Performance tests
pytest tests/test_performance.py --benchmark
```

---

## 8. MIGRATION STRATEGY

### Risk Mitigation

#### 1. Feature Flags
```python
# config.py
FEATURES = {
    'server_driven_ui': False,  # Toggle new architecture
    'legacy_mode': True,         # Keep old code path
}

# Usage
if FEATURES['server_driven_ui']:
    return handle_with_new_architecture()
else:
    return handle_with_legacy()
```

#### 2. Parallel Running
- Keep both architectures functional
- A/B test with subset of users
- Monitor metrics for regression

#### 3. Rollback Procedures
```bash
# Instant rollback
UPDATE config SET server_driven_ui = false;

# Full rollback script
./scripts/rollback_to_legacy.sh
```

### Gradual Migration Path

#### Step 1: Deploy Backend Changes (Week 1)
- ✅ Deploy new backend with backward compatibility
- ✅ New endpoints alongside old ones
- ✅ Session manager active but optional

#### Step 2: Test with Existing Frontend (Week 2)
- ✅ Verify new endpoints work
- ✅ Load test new architecture
- ✅ Monitor for issues

#### Step 3: Deploy Frontend Behind Flag (Week 3)
- ✅ New frontend code deployed but disabled
- ✅ Feature flag controls activation
- ✅ Internal testing with flag enabled

#### Step 4: Gradual Rollout (Week 4)
- ✅ 10% → 25% → 50% → 100% rollout
- ✅ Monitor metrics at each stage
- ✅ Rollback if issues detected

#### Step 5: Remove Old Code (Week 6)
- ✅ Confirm stable for 2 weeks
- ✅ Remove feature flags
- ✅ Delete legacy code

---

## 9. SUCCESS METRICS

### Technical Metrics
- ✅ **Test Coverage:** Minimum 80% overall
- ✅ **No Regressions:** All existing tests pass
- ✅ **Performance:** Response time < 100ms
- ✅ **Memory:** No increase in memory usage
- ✅ **Errors:** Error rate < 0.1%

### Architecture Metrics
- ✅ **Code Reduction:** Frontend LOC reduced by 50%
- ✅ **Test Isolation:** Business tests separate from UI
- ✅ **Duplication:** Zero duplicated business logic

### Business Metrics
- ✅ **User Experience:** No degradation in UX
- ✅ **Completion Rate:** Maintained or improved
- ✅ **Load Time:** Page load < 2 seconds

---

## 10. DETAILED TODO LIST

### Week 1: Backend Foundation
- [ ] **Day 1-2: Session Manager**
  - [ ] Write tests: `test_session_manager.py`
  - [ ] Implement SessionManager class
  - [ ] Add SQLite persistence
  - [ ] Verify: `pytest tests/test_session_manager.py`

- [ ] **Day 3-4: Dependency Engine**
  - [ ] Write tests: `test_dependency_engine.py`
  - [ ] Implement graph building
  - [ ] Add cycle detection
  - [ ] Verify: `pytest tests/test_dependency_engine.py`

- [ ] **Day 5: Integration**
  - [ ] Write integration tests
  - [ ] Connect components
  - [ ] End-of-week testing

### Week 2: Command System
- [ ] **Day 1-2: Command Generator**
  - [ ] Write tests: `test_command_generator.py`
  - [ ] Implement command types
  - [ ] Add batching logic
  - [ ] Verify tests pass

- [ ] **Day 3-4: UI Schema Generator**
  - [ ] Write tests: `test_ui_schema_generator.py`
  - [ ] Convert question types
  - [ ] Handle conditionals
  - [ ] Verify schema validity

- [ ] **Day 5: Event Handler**
  - [ ] Write tests: `test_event_handler.py`
  - [ ] Process user events
  - [ ] Trigger commands
  - [ ] Integration testing

### Week 3: Protocol Layer
- [ ] **Day 1-2: SSE Implementation**
  - [ ] Write tests: `test_sse_communication.py`
  - [ ] Implement SSE manager
  - [ ] Add reconnection logic
  - [ ] Test with multiple clients

- [ ] **Day 3-4: Protocol Testing**
  - [ ] Write protocol tests
  - [ ] Verify message format
  - [ ] Test error handling
  - [ ] Load testing

- [ ] **Day 5: Backend Integration**
  - [ ] Full backend integration test
  - [ ] Performance benchmarks
  - [ ] Documentation update

### Week 4: Frontend Refactoring
- [ ] **Day 1-2: Command Processor**
  - [ ] Write tests: `test_command_processor.test.js`
  - [ ] Implement processor
  - [ ] Connect to React
  - [ ] Verify rendering

- [ ] **Day 3-4: Event Dispatcher**
  - [ ] Write tests: `test_event_dispatcher.test.js`
  - [ ] Implement dispatcher
  - [ ] Add retry logic
  - [ ] Test error cases

- [ ] **Day 5: Pure Components**
  - [ ] Refactor QuestionRenderer
  - [ ] Remove business logic
  - [ ] Update tests

### Week 5: Integration
- [ ] **Day 1-2: End-to-End Testing**
  - [ ] Write E2E tests
  - [ ] Test full flow
  - [ ] Verify cascades work

- [ ] **Day 3-4: Performance Optimization**
  - [ ] Profile performance
  - [ ] Optimize hot paths
  - [ ] Cache where needed

- [ ] **Day 5: Feature Flag Setup**
  - [ ] Implement feature flags
  - [ ] Test toggle behavior
  - [ ] Prepare rollout plan

### Week 6: Deployment
- [ ] **Day 1: Staging Deployment**
  - [ ] Deploy to staging
  - [ ] Run test suite
  - [ ] Performance testing

- [ ] **Day 2-3: Production Rollout**
  - [ ] 10% rollout with monitoring
  - [ ] 50% rollout if stable
  - [ ] 100% rollout

- [ ] **Day 4-5: Monitoring & Cleanup**
  - [ ] Monitor metrics
  - [ ] Remove old code (if stable)
  - [ ] Documentation

---

## Implementation Checklist

### Pre-Implementation
- [ ] Review and approve this plan
- [ ] Set up test infrastructure
- [ ] Configure CI/CD pipeline
- [ ] Create feature flag system

### Phase 1: Backend Foundation
- [ ] Session Manager with tests
- [ ] Dependency Engine with tests
- [ ] Command Generator with tests
- [ ] UI Schema Generator with tests
- [ ] Event Handler with tests
- [ ] Integration tests passing

### Phase 2: Protocol Layer
- [ ] SSE implementation with tests
- [ ] Protocol specification complete
- [ ] Client library with tests
- [ ] Load testing complete

### Phase 3: Frontend Refactoring
- [ ] Command Processor with tests
- [ ] Event Dispatcher with tests
- [ ] Pure UI components
- [ ] Old logic removed
- [ ] All frontend tests passing

### Phase 4: Integration
- [ ] E2E tests passing
- [ ] Performance benchmarks met
- [ ] Feature flags working
- [ ] Rollback tested

### Phase 5: Deployment
- [ ] Staging deployment successful
- [ ] Production rollout complete
- [ ] Metrics monitoring active
- [ ] Documentation updated

### Post-Implementation
- [ ] Remove feature flags
- [ ] Delete legacy code
- [ ] Update team training
- [ ] Celebrate success! 🎉

---

## Appendix A: Test File Templates

### Backend Test Template
```python
# tests/test_component.py
import pytest
from src.backend.component import Component

class TestComponent:
    @pytest.fixture
    def component(self):
        return Component()
    
    def test_functionality(self, component):
        # Arrange
        input_data = {...}
        
        # Act
        result = component.process(input_data)
        
        # Assert
        assert result == expected
```

### Frontend Test Template
```javascript
// tests/component.test.js
import { render, fireEvent, waitFor } from '@testing-library/react';
import Component from '../src/Component';

describe('Component', () => {
  it('should render correctly', () => {
    const { getByText } = render(<Component />);
    expect(getByText('Expected')).toBeInTheDocument();
  });
  
  it('should handle events', async () => {
    const { getByRole } = render(<Component />);
    fireEvent.click(getByRole('button'));
    await waitFor(() => {
      expect(mockHandler).toHaveBeenCalled();
    });
  });
});
```

---

## Appendix B: Protocol Examples

### Complete Question Flow
```javascript
// 1. Client requests session
POST /api/session/create
Response: { session_id: "uuid-1234" }

// 2. Client connects SSE
GET /api/sse/uuid-1234

// 3. Server sends initial state
data: {"type":"STATE_SYNC","state":{...}}

// 4. Server sends first question
data: {"type":"RENDER","component":"question","data":{...}}

// 5. User answers question
POST /api/event
{ "session_id": "uuid-1234", "event": {"type":"USER_EVENT","event":"answer_change",...}}

// 6. Server sends update
data: {"type":"UPDATE","target":"SG01","updates":[...]}

// 7. Server triggers evaluation
data: {"type":"UPDATE","target":"SG01","updates":[{"path":"props.thinking","value":true}]}

// 8. Server sends score
data: {"type":"UPDATE","target":"SG01","updates":[{"path":"score","value":85}]}
```

---

## Appendix C: Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| SSE connection issues | Medium | High | Implement reconnection logic, fallback to polling |
| Performance degradation | Low | High | Continuous performance testing, optimization |
| Complex migration | Medium | Medium | Feature flags, gradual rollout |
| Test coverage gaps | Low | Medium | Mandatory TDD, coverage requirements |
| Team resistance | Low | Low | Training, documentation, benefits demonstration |

---

**END OF DOCUMENT**

This plan provides a complete roadmap for migrating the QnA Evaluator to a Server-Driven UI architecture using Test-Driven Development. Each component has clear specifications, test requirements, and verification steps. The migration is designed to be gradual, safe, and reversible.