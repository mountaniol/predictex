# TOML Migration Plan: q4.json → q4.toml

## Executive Summary

### Purpose
This document outlines a comprehensive migration plan for converting the QnA Evaluator system from JSON-based configuration (`public/questions/q4.json`) to a more maintainable TOML format (`public/questions/q4.toml`).

### Key Benefits
- **Improved Readability**: TOML's human-friendly syntax with comments support
- **Better Configuration Management**: Native support for multi-line strings and structured data
- **Enhanced Maintainability**: Cleaner syntax for complex configurations
- **Type Safety**: Better validation and error reporting
- **Future Extensibility**: Easier to add new configuration options

### Current Challenges
- **File Size**: 1,684 lines of complex nested JSON structure
- **Deep Nesting**: 4-5 levels of nested objects (follow_ups, options, ai_context)
- **Maintenance Difficulty**: Hard to read and modify large JSON configurations
- **No Comments**: JSON doesn't support documentation within the configuration

### Timeline Overview
**Total Duration**: 4-7 days across 3 phases
- **Phase 1**: TOML Structure Design & Conversion (2-3 days)
- **Phase 2**: DSL Parser Development (1-2 days)
- **Phase 3**: System Integration & Testing (1-2 days)

---

## Current JSON Structure Analysis

### File Statistics
- **Location**: `public/questions/q4.json`
- **Size**: 1,684 lines
- **Main Questions**: 49 questions + optional questions
- **Analysis Sections**: 8 final analysis configuration sections
- **Complexity**: 4-5 levels of nesting in multiple areas

### Key Structural Elements

#### 1. Questions Array Structure
```json
{
  "questions": [
    {
      "id": "SG01",
      "text": "Why are you selling now?",
      "question_type": "choice-multi",
      "options": [
        {"code": "retirement_move", "label": "Retirement or move"},
        {"code": "health", "label": "Health or personal"}
      ],
      "follow_ups": [
        {
          "when": {"in": ["down_20plus"]},
          "ask": {
            "id": "SG04_REASON",
            "question_type": "text",
            "ui": "textarea",
            "placeholder": "Main reason for decline",
            "max_chars": 140
          }
        }
      ],
      "ai_context": {
        "include_answers": ["SG03A", "SG03B"]
      }
    }
  ]
}
```

#### 2. Final Analysis Configuration
```json
{
  "final_analysis_config": {
    "sections": [
      {
        "name": "Business Environment",
        "model": "gpt-4o",
        "web_search": {
          "enabled": true,
          "max_searches": 12
        },
        "ai_context": {
          "include_answers": ["all"],
          "include_scores": true
        },
        "model_config": {
          "max_output_tokens": 1000,
          "temperature": 0.3
        }
      }
    ]
  }
}
```

### Identified Complexity Issues

1. **Options Arrays**: Repetitive `[{"code": "...", "label": "..."}]` patterns
2. **Follow-ups Logic**: Deep nested conditional structures
3. **AI Context**: Complex dependency definitions
4. **Long Prompt Strings**: Multi-line prompts in escaped JSON strings
5. **Analysis Configuration**: 8 sections with deep nesting each

---

## TOML Solution Strategy

### Core Transformation Principles

#### 1. **Follow-ups → String DSL**
Transform complex nested follow-up logic into simple string-based Domain Specific Language.

**Before (JSON):**
```json
"follow_ups": [
  {
    "when": {"in": ["down_20plus"]},
    "ask": {
      "id": "SG04_REASON",
      "question_type": "text",
      "ui": "textarea",
      "placeholder": "Main reason for decline",
      "max_chars": 140
    }
  }
]
```

**After (TOML):**
```toml
follow_up_rules = [
  "when:down_20plus -> ask:SG04_REASON:text:Main reason for decline:140"
]
```

#### 2. **Options → Inline Tables**
Convert arrays of objects to TOML inline table syntax.

**Before (JSON):**
```json
"options": [
  {"code": "lt250k", "label": "< $250k"},
  {"code": "250k_1m", "label": "$250k to $1m"}
]
```

**After (TOML):**
```toml
options = [
  {code = "lt250k", label = "< $250k"},
  {code = "250k_1m", label = "$250k to $1m"}
]
```

#### 3. **AI Context → Simple Arrays**
Flatten nested AI context objects to simple arrays.

**Before (JSON):**
```json
"ai_context": {
  "include_answers": ["SG01", "SG02"]
}
```

**After (TOML):**
```toml
ai_context_include_answers = ["SG01", "SG02"]
```

#### 4. **Analysis Config → Named Sections**
Transform array of analysis sections into named TOML sections.

**Before (JSON):**
```json
"sections": [
  {
    "name": "Business Environment",
    "model": "gpt-4o",
    "web_search": {"enabled": true}
  }
]
```

**After (TOML):**
```toml
[analysis.business_environment]
name = "Business Environment"
model = "gpt-4o"
web_search_enabled = true
```

#### 5. **Long Prompts → Multi-line Strings**
Use TOML's native multi-line string support.

**Before (JSON):**
```json
"prompt_add": "Score intent of sale STRICTLY by these rules. CRITICAL RULE: If user selected 'Declining sales' answer, you MUST give score between 0-19..."
```

**After (TOML):**
```toml
prompt_add = """
Score intent of sale STRICTLY by these rules.
CRITICAL RULE: If user selected 'Declining sales' answer, 
you MUST give score between 0-19 (critical risk).
Good answers (score 80-100): planned retirement/move/strategic refocus.
Bad answers (score 0-19): urgent cash need, lawsuits/tax issues, declining sales.
"""
```

---

## Complete TOML Structure Example

### Basic Structure
```toml
version = "1.2"

[settings.labels]
yes = "Yes"
no = "No"
unknown = "I'm not sure"
role = "buyer"
```

### Question Examples
```toml
# Simple text question
[[questions]]
id = "MET.LOC"
text = "Where is the business located (country, state, city)?"
hint = "List main operating location(s)"
info = """
Write the country, state or province if applicable, and the city where 
the business mainly operates. If multiple locations, list them all.
Example: USA, North Carolina, Charlotte.
"""
cluster_name = "Basic Information"
position_in_cluster = 1
question_type = "text"
score = "NO"
ai_validate_prompt = """
Rephrase the following location and confirm your understanding. 
Start your response with 'As I understand, the business is located in...'. 
If the input is unclear, ask for clarification. The user's input is: {answer}
"""

# Choice question with options
[[questions]]
id = "MET.SIZE"
text = "Approximate annual revenue bracket"
hint = "Pick a rough yearly sales range"
cluster_name = "Basic Information"
position_in_cluster = 3
question_type = "choice-single"
ui = "dropdown"
score = "NO"
options_sort = "as_is"
options = [
  {code = "lt250k", label = "< $250k"},
  {code = "250k_1m", label = "$250k to $1m"},
  {code = "1m_5m", label = "$1m to $5m"},
  {code = "gt5m", label = ">$5m"}
]
custom_text_input = {id = "MET.SIZE_CUSTOM", placeholder = "Or enter exact annual revenue"}

# Multi-choice with follow-ups
[[questions]]
id = "SG01"
text = "Why are you selling now?"
hint = "Select up to two reasons (rank them)"
info = """
We want to know if the sale is planned (retirement, moving) or forced 
(falling sales, lawsuits, urgent cash needs). Ask the seller directly.
"""
cluster_name = "Strategic Fundamentals"
position_in_cluster = 1
question_type = "choice-multi"
ui = "multiselect"
max_selections = 2
ranked = true
with_other = true
other_text_id = "SG01_OTHER"
options_sort = "as_is"
options = [
  {code = "retirement_move", label = "Retirement or move"},
  {code = "health", label = "Health or personal"},
  {code = "strategic_refocus", label = "Strategic refocus"},
  {code = "declining_sales", label = "Declining sales"},
  {code = "lawsuits_tax", label = "Lawsuits or tax issues"},
  {code = "urgent_cash", label = "Urgent cash need"},
  {code = "other", label = "Other"}
]
ai_context_include_answers = []
prompt_add = """
Score intent of sale STRICTLY by these rules.
CRITICAL RULE: If user selected 'Declining sales' answer, you MUST give score between 0-19 (critical risk), no exceptions.
Good answers (score 80-100): planned retirement/move/strategic refocus.
Bad answers (score 0-19): urgent cash need, lawsuits/tax issues, declining sales.
Follow bands exactly: 0–19 critical; 20–49 high; 50–79 moderate; 80–100 low.
"""

# Question with follow-ups using DSL
[[questions]]
id = "SG04"
text = "Last 12 months revenue compared to the previous 12 months"
hint = "Up / flat / down ≥20%"
cluster_name = "Financial & Legal Situation"
position_in_cluster = 1
question_type = "choice-single"
ui = "radio"
options_sort = "as_is"
options = [
  {code = "up", label = "Up"},
  {code = "flat", label = "About flat"},
  {code = "down_20plus", label = "Down 20% or more"}
]
# Simplified follow-up using string DSL
follow_up_rules = [
  "when:down_20plus -> ask:SG04_REASON:text:Main reason for decline:140"
]
ai_context_include_answers = ["SG03A", "SG03B"]
prompt_add = """
Good: up/flat with plausible context. 
Red: down ≥20% without credible reason or conflicting with SG05/SG12/SG13. 
Weigh industry cyclicality (MET.IND).
"""
```

### Analysis Configuration
```toml
[analysis]
loading_message = "Analyzing... This may take a few minutes."
base_prompt = """
You're a skeptical buy-side M&A analyst writing for non-experts. 
Be conservative and risk-first. Use plain language (grade 6–8), short sentences, no jargon. 
Do not use terms like EBITDA or SDE; if unavoidable, explain in brackets the first time. 
Do not mention browsing. Do not reveal chain-of-thought; give conclusions and evidence only. 
Verify important claims with recent reputable sources. 
If solid sources are not found quickly, use reasonable proxies and still deliver results; never write 'Not enough public data'. 
CRITICAL: You MUST return a FLAT JSON object with exactly ONE field named 'report'. 
The 'report' field must contain ONLY the Markdown text content as a string. 
DO NOT create nested JSON objects inside the 'report' field. 
DO NOT create arrays or complex structures. 
The 'report' field should be a simple string containing the full Markdown content. 
Example format: {"report": "# Section Title\\n\\n- Item 1: Description\\n- Item 2: Description"}. 
Return response up to 250 words.
"""

[analysis.business_environment]
name = "Business Environment"
model = "gpt-4o"
web_search_enabled = true
web_search_max_searches = 12
ai_context_include_answers = "all"
ai_context_include_scores = true
ai_context_include_overall_score = true
specific_prompt = """
Your task is to write ONLY the 'Business Environment' section. 
Begin with one line: 'For this type of business in {location}, we see the following:' 
Then provide a concise place-and-industry scan. 
Cover: demand and ability to pay, market reach, sustainability and trends, labor and hiring, 
operating conditions, economic backdrop, regulatory climate, specific constraints, 
risk snapshot by category, and a 2–3 sentence bottom line. 
Use up to 12 targeted searches; do not cite URLs.
"""
output_constraint = "return one JSON object with one field named report whose value is the full Markdown for this section, the response size no more than 250 words"
model_config = {max_output_tokens = 1000, temperature = 0.3, stream = true}

[analysis.deal_breakers]
name = "Deal-Breakers Checklist"
model = "gpt-4o-mini"
web_search_enabled = false
ai_context_include_answers = "all"
ai_context_include_scores = false
ai_context_include_overall_score = false
specific_prompt = """
Your task is to write ONLY the 'Deal-Breakers Checklist' section in Markdown format. 
Create a bulleted list where each item is marked very low score < 40 or very high score > 90 
with a brief explanation.
"""
output_constraint = "return one JSON object with one field named report whose value is the full Markdown for this section, the response size no more than 250 words"
model_config = {max_output_tokens = 1000, temperature = 0.2, stream = true}

# Additional analysis sections would follow the same pattern...
```

---

## Detailed Implementation Plan

### Phase 1: TOML Structure Design & Conversion (2-3 days)

#### Day 1: Core Structure Design
**Tasks:**
1. **Design Follow-up DSL Syntax**
   - Define grammar for follow-up rules
   - Create parser specification document
   - Test DSL with complex examples from q4.json

2. **Create TOML Schema**
   - Design complete TOML structure based on JSON analysis
   - Define validation rules for all fields
   - Document transformation patterns

3. **Convert Basic Questions**
   - Transform first 10-15 simple questions (text, yes-no types)
   - Test TOML parsing with these questions
   - Validate readability and structure

**Success Criteria:**
- [ ] Follow-up DSL grammar documented and validated
- [ ] Complete TOML schema designed
- [ ] 15 basic questions converted and validated

#### Day 2: Complex Questions Conversion
**Tasks:**
1. **Convert Choice Questions**
   - Transform all single-choice and multi-choice questions
   - Convert options arrays to inline tables
   - Handle custom_text_input configurations

2. **Implement Follow-up Rules**
   - Apply DSL to all follow-up scenarios
   - Test complex conditional logic
   - Validate against original JSON behavior

3. **Convert AI Context**
   - Transform ai_context objects to simple arrays
   - Handle prompt_add multi-line strings
   - Convert validation prompts

**Success Criteria:**
- [ ] All 49 main questions converted to TOML
- [ ] Follow-up DSL applied to all relevant questions
- [ ] AI context and prompts properly formatted

#### Day 3: Analysis Configuration
**Tasks:**
1. **Convert Final Analysis Config**
   - Transform 8 analysis sections to named TOML sections
   - Flatten nested web_search and ai_context objects
   - Convert model_config inline tables

2. **Handle Long Prompts**
   - Convert all multi-line prompts to TOML multi-line strings
   - Ensure proper escaping and formatting
   - Test prompt parsing and usage

3. **Create Validation Script**
   - Build script to validate TOML structure
   - Check for missing fields and invalid references
   - Generate conversion report

**Success Criteria:**
- [ ] All 8 analysis sections converted to TOML
- [ ] All long prompts properly formatted
- [ ] Validation script created and passing

### Phase 2: DSL Parser Development (1-2 days)

#### DSL Grammar Definition
```
follow_up_rule := "when:" condition " -> ask:" question_spec

condition := value | value_list
value_list := value ("," value)*
value := [a-zA-Z0-9_]+

question_spec := question_id ":" question_type [":" placeholder [":" max_chars]]
question_id := [a-zA-Z0-9_]+
question_type := "text" | "textarea" | "number" | "choice-single" | "choice-multi"
placeholder := string
max_chars := number
```

#### Day 1: Parser Implementation
**Tasks:**
1. **Create DSL Parser**
   ```python
   # src/backend/follow_up_parser.py
   class FollowUpParser:
       def parse_rule(self, rule_string: str) -> dict:
           """Parse DSL string into follow-up object structure"""
           pass
       
       def rules_to_json(self, rules: list) -> list:
           """Convert DSL rules to original JSON format"""
           pass
   ```

2. **JavaScript DSL Parser**
   ```javascript
   // src/utils/followUpParser.js
   export class FollowUpParser {
       parseRule(ruleString) {
           // Parse DSL string into follow-up object
       }
       
       rulesToJson(rules) {
           // Convert DSL rules to JSON format
       }
   }
   ```

3. **Unit Tests**
   - Test all DSL patterns from q4.json
   - Validate parsing accuracy
   - Test error handling for malformed rules

**Success Criteria:**
- [ ] Python DSL parser implemented and tested
- [ ] JavaScript DSL parser implemented and tested
- [ ] 100% test coverage for DSL parsing

#### Day 2: Integration Testing
**Tasks:**
1. **Backend Integration**
   - Integrate DSL parser with question loading
   - Test with converted TOML file
   - Validate API responses

2. **Frontend Integration**
   - Update question loading to use DSL parser
   - Test follow-up logic with new format
   - Validate UI behavior

3. **Data Equivalence Testing**
   - Create test suite to verify JSON ≡ TOML data
   - Test all follow-up scenarios
   - Performance benchmarking

**Success Criteria:**
- [ ] DSL parser integrated in backend and frontend
- [ ] All follow-up logic working correctly
- [ ] Data equivalence tests passing

### Phase 3: System Integration & Testing (1-2 days)

#### Day 1: Backend Integration
**Tasks:**
1. **Update Question Loaders**
   ```python
   # Update src/backend/py_simple_evaluate.py
   def load_questions_data():
       import toml
       with open(questions_path.replace('.json', '.toml'), 'r') as f:
           data = toml.load(f)
       
       # Process follow_up_rules through parser
       for question in data.get('questions', []):
           if 'follow_up_rules' in question:
               question['follow_ups'] = parser.rules_to_json(question['follow_up_rules'])
       
       return data
   ```

2. **Update Analysis Configuration Loading**
   ```python
   # Handle flattened analysis config
   def process_analysis_config(toml_data):
       sections = []
       for key, section in toml_data.get('analysis', {}).items():
           if key.startswith('analysis.'):
               # Reconstruct nested structure for backward compatibility
               sections.append(reconstruct_section(section))
       return sections
   ```

3. **Add TOML Dependencies**
   ```python
   # requirements.txt
   toml>=0.10.2
   ```

**Success Criteria:**
- [ ] Backend loads TOML file successfully
- [ ] All question data properly processed
- [ ] Analysis configuration working
- [ ] No regression in API responses

#### Day 2: Frontend Integration & Testing
**Tasks:**
1. **Frontend TOML Support**
   ```javascript
   // Install TOML parser
   npm install @iarna/toml
   
   // Update src/hooks/useLoadQuestions.js
   import TOML from '@iarna/toml';
   
   const loadQuestionData = async (questionSetId) => {
       const response = await fetch(`/questions/${questionSetId}.toml`);
       const tomlText = await response.text();
       const data = TOML.parse(tomlText);
       
       // Process follow_up_rules
       data.questions.forEach(question => {
           if (question.follow_up_rules) {
               question.follow_ups = followUpParser.rulesToJson(question.follow_up_rules);
           }
       });
       
       return data;
   };
   ```

2. **Comprehensive Testing**
   - End-to-end testing with TOML configuration
   - UI testing for all question types
   - Follow-up logic testing
   - AI evaluation testing

3. **Performance Testing**
   - TOML vs JSON loading performance
   - Memory usage comparison
   - Parsing speed benchmarks

**Success Criteria:**
- [ ] Frontend successfully loads TOML file
- [ ] All UI components working correctly
- [ ] Follow-up logic functioning
- [ ] Performance within acceptable range

---

## Risk Assessment & Mitigation

### High Risk Areas

#### 1. **Data Loss or Corruption**
**Risk**: Converting complex nested JSON to TOML could result in data loss or incorrect transformations.

**Mitigation Strategies:**
- Create comprehensive data equivalence tests
- Maintain original JSON file as backup during migration
- Implement bidirectional conversion validation
- Test every question and follow-up scenario manually

#### 2. **Follow-up Logic Errors**
**Risk**: DSL parser could incorrectly interpret follow-up conditions, breaking question flow.

**Mitigation Strategies:**
- Create exhaustive test suite for all follow-up patterns
- Implement DSL validation with clear error messages
- Test edge cases and complex conditional logic
- Provide fallback to JSON format if DSL fails

#### 3. **Performance Degradation**
**Risk**: TOML parsing could be slower than JSON, affecting application startup time.

**Mitigation Strategies:**
- Benchmark TOML vs JSON parsing performance
- Implement caching for parsed TOML data
- Consider lazy loading for large configurations
- Profile memory usage during parsing

#### 4. **Frontend/Backend Incompatibility**
**Risk**: Different TOML parsers in JavaScript and Python could produce different results.

**Mitigation Strategies:**
- Use well-tested, compatible TOML parsers
- Create cross-platform validation tests
- Document any parser-specific behaviors
- Test identical TOML files in both environments

### Medium Risk Areas

#### 5. **Analysis Configuration Complexity**
**Risk**: Flattening nested analysis config could break existing AI evaluation logic.

**Mitigation Strategies:**
- Maintain backward compatibility layer
- Test all analysis sections individually
- Validate AI prompts and context inclusion
- Compare analysis outputs before/after migration

#### 6. **Edge Case Handling**
**Risk**: Uncommon question configurations might not be properly handled in TOML format.

**Mitigation Strategies:**
- Audit all question types and configurations
- Test optional_questions array separately
- Validate all custom_text_input scenarios
- Handle unicode and special characters properly

### Low Risk Areas

#### 7. **Documentation Updates**
**Risk**: Documentation might become outdated after migration.

**Mitigation Strategies:**
- Update all configuration documentation
- Create TOML format guide for future maintenance
- Update code comments and examples

---

## Testing Strategy

### 1. Data Equivalence Testing

#### Automated Validation Script
```python
# test_toml_equivalence.py
import json
import toml
from follow_up_parser import FollowUpParser

def test_data_equivalence():
    # Load original JSON
    with open('q4.json', 'r') as f:
        json_data = json.load(f)
    
    # Load converted TOML
    with open('q4.toml', 'r') as f:
        toml_data = toml.load(f)
    
    # Process TOML follow-ups
    parser = FollowUpParser()
    for question in toml_data.get('questions', []):
        if 'follow_up_rules' in question:
            question['follow_ups'] = parser.rules_to_json(question['follow_up_rules'])
            del question['follow_up_rules']
    
    # Compare structures
    assert json_data == toml_data, "Data structures must be equivalent"
    
def test_question_completeness():
    """Ensure all questions from JSON exist in TOML"""
    json_questions = {q['id']: q for q in json_data['questions']}
    toml_questions = {q['id']: q for q in toml_data['questions']}
    
    assert json_questions.keys() == toml_questions.keys()
    
    for qid in json_questions:
        assert_question_equivalent(json_questions[qid], toml_questions[qid])

def test_analysis_sections():
    """Validate analysis configuration equivalence"""
    json_sections = {s['name']: s for s in json_data['final_analysis_config']['sections']}
    toml_sections = reconstruct_analysis_sections(toml_data)
    
    assert json_sections.keys() == toml_sections.keys()
    
    for name in json_sections:
        assert_analysis_equivalent(json_sections[name], toml_sections[name])
```

### 2. Follow-up Logic Testing

```python
# test_followup_dsl.py
def test_dsl_parsing():
    test_cases = [
        {
            'dsl': 'when:down_20plus -> ask:SG04_REASON:text:Main reason:140',
            'expected': {
                'when': {'in': ['down_20plus']},
                'ask': {
                    'id': 'SG04_REASON',
                    'question_type': 'text',
                    'placeholder': 'Main reason',
                    'max_chars': 140
                }
            }
        },
        {
            'dsl': 'when:yes -> ask:SG05_NOTE:textarea:Brief reason:120',
            'expected': {
                'when': {'in': ['yes']},
                'ask': {
                    'id': 'SG05_NOTE',
                    'question_type': 'textarea',
                    'placeholder': 'Brief reason',
                    'max_chars': 120
                }
            }
        }
    ]
    
    parser = FollowUpParser()
    for case in test_cases:
        result = parser.parse_rule(case['dsl'])
        assert result == case['expected']
```

### 3. Integration Testing

```javascript
// test/integration/toml-loading.test.js
describe('TOML Question Loading', () => {
  test('should load all questions correctly', async () => {
    const questions = await loadQuestionData('q4');
    
    expect(questions.questions).toHaveLength(49);
    expect(questions.version).toBe('1.2');
    expect(questions.settings.labels.yes).toBe('Yes');
  });
  
  test('should process follow-up rules correctly', async () => {
    const questions = await loadQuestionData('q4');
    const sg04 = questions.questions.find(q => q.id === 'SG04');
    
    expect(sg04.follow_ups).toBeDefined();
    expect(sg04.follow_ups[0].when.in).toContain('down_20plus');
    expect(sg04.follow_ups[0].ask.id).toBe('SG04_REASON');
  });
  
  test('should handle multi-line prompts correctly', async () => {
    const questions = await loadQuestionData('q4');
    const sg01 = questions.questions.find(q => q.id === 'SG01');
    
    expect(sg01.prompt_add).toContain('Score intent of sale STRICTLY');
    expect(sg01.prompt_add).toContain('CRITICAL RULE');
  });
});
```

### 4. Performance Testing

```python
# test_performance.py
import time
import json
import toml

def benchmark_parsing():
    # JSON parsing
    start_time = time.time()
    for i in range(100):
        with open('q4.json', 'r') as f:
            json.load(f)
    json_time = time.time() - start_time
    
    # TOML parsing
    start_time = time.time()
    for i in range(100):
        with open('q4.toml', 'r') as f:
            toml.load(f)
    toml_time = time.time() - start_time
    
    print(f"JSON parsing: {json_time:.3f}s")
    print(f"TOML parsing: {toml_time:.3f}s")
    print(f"Performance ratio: {toml_time/json_time:.2f}x")
    
    assert toml_time < json_time * 2, "TOML parsing should not be more than 2x slower"
```

### 5. End-to-End Testing

```javascript
// test/e2e/question-flow.test.js
describe('Question Flow with TOML', () => {
  test('should handle follow-up questions correctly', async () => {
    // Navigate to question SG04
    await page.goto('/questions');
    await page.selectOption('#SG04', 'down_20plus');
    
    // Follow-up should appear
    const followUp = await page.waitForSelector('#SG04_REASON');
    expect(followUp).toBeTruthy();
    
    // Fill follow-up
    await page.fill('#SG04_REASON', 'Lost major client');
    
    // Should trigger AI evaluation
    await page.waitForSelector('.evaluation-complete');
  });
  
  test('should evaluate questions with AI correctly', async () => {
    await page.selectOption('#SG01', 'declining_sales');
    await page.waitForSelector('.ai-evaluation');
    
    const score = await page.textContent('.question-score');
    expect(parseInt(score)).toBeLessThan(20); // Should be critical risk
  });
});
```

---

## Implementation Details

### File Structure Changes

#### Current Structure
```
public/questions/
├── q4.json                 # Main questionnaire (1,684 lines)
├── ai-prompt.txt           # AI evaluation prompts
└── test_*.json            # Test configurations
```

#### New Structure
```
public/questions/
├── q4.toml                 # New TOML questionnaire
├── q4.json.backup         # Backup of original JSON
├── ai-prompt.txt           # AI evaluation prompts (unchanged)
└── test_*.toml            # Test configurations (converted)
```

### Backend Code Changes

#### 1. Question Data Loading
```python
# src/backend/py_simple_evaluate.py
def load_questions_data():
    """Load questionnaire data from TOML format"""
    questions_file = get_questions_file_path()  # Returns .toml file
    
    # Load TOML data
    import toml
    with open(questions_file, 'r', encoding='utf-8') as f:
        data = toml.load(f)
    
    # Process follow-up rules using DSL parser
    from .follow_up_parser import FollowUpParser
    parser = FollowUpParser()
    
    for question in data.get('questions', []):
        if 'follow_up_rules' in question:
            question['follow_ups'] = parser.rules_to_json(question['follow_up_rules'])
            # Remove DSL rules from final data
            del question['follow_up_rules']
        
        # Process flattened AI context
        if 'ai_context_include_answers' in question:
            question['ai_context'] = {
                'include_answers': question['ai_context_include_answers']
            }
            del question['ai_context_include_answers']
    
    # Process analysis configuration
    if 'analysis' in data:
        data['final_analysis_config'] = process_analysis_config(data['analysis'])
        del data['analysis']
    
    return data

def process_analysis_config(analysis_data):
    """Convert flattened TOML analysis config to nested JSON structure"""
    sections = []
    
    for key, section_data in analysis_data.items():
        if key == 'loading_message' or key == 'base_prompt':
            continue
            
        section = {
            'name': section_data.get('name', key),
            'model': section_data.get('model', 'gpt-4o'),
            'web_search': {
                'enabled': section_data.get('web_search_enabled', False),
                'max_searches': section_data.get('web_search_max_searches', 3)
            },
            'ai_context': {
                'include_answers': section_data.get('ai_context_include_answers', []),
                'include_scores': section_data.get('ai_context_include_scores', False),
                'include_overall_score': section_data.get('ai_context_include_overall_score', False)
            },
            'specific_prompt': section_data.get('specific_prompt', ''),
            'output_constraint': section_data.get('output_constraint', ''),
            'model_config': section_data.get('model_config', {})
        }
        sections.append(section)
    
    return {
        'loading_message': analysis_data.get('loading_message', ''),
        'base_prompt': analysis_data.get('base_prompt', ''),
        'sections': sections
    }
```

#### 2. Follow-up DSL Parser
```python
# src/backend/follow_up_parser.py
import re
from typing import Dict, List, Any

class FollowUpParser:
    """Parser for follow-up DSL rules"""
    
    DSL_PATTERN = re.compile(
        r'when:(?P<condition>[^-]+)\s*->\s*ask:(?P<question_spec>.+)'
    )
    
    QUESTION_SPEC_PATTERN = re.compile(
        r'(?P<id>[^:]+):(?P<type>[^:]+)(?::(?P<placeholder>[^:]+))?(?::(?P<max_chars>\d+))?'
    )
    
    def parse_rule(self, rule_string: str) -> Dict[str, Any]:
        """Parse a single DSL rule string into follow-up object"""
        match = self.DSL_PATTERN.match(rule_string.strip())
        if not match:
            raise ValueError(f"Invalid DSL rule: {rule_string}")
        
        condition = match.group('condition').strip()
        question_spec = match.group('question_spec').strip()
        
        # Parse condition (simple values or comma-separated list)
        conditions = [c.strip() for c in condition.split(',')]
        
        # Parse question specification
        spec_match = self.QUESTION_SPEC_PATTERN.match(question_spec)
        if not spec_match:
            raise ValueError(f"Invalid question specification: {question_spec}")
        
        ask_config = {
            'id': spec_match.group('id'),
            'question_type': spec_match.group('type')
        }
        
        if spec_match.group('placeholder'):
            ask_config['placeholder'] = spec_match.group('placeholder')
        
        if spec_match.group('max_chars'):
            ask_config['max_chars'] = int(spec_match.group('max_chars'))
        
        # Determine UI type based on question type
        ui_mapping = {
            'text': 'text',
            'textarea': 'textarea',
            'number': 'number',
            'choice-single': 'radio',
            'choice-multi': 'multiselect'
        }
        
        if ask_config['question_type'] in ui_mapping:
            ask_config['ui'] = ui_mapping[ask_config['question_type']]
        
        return {
            'when': {'in': conditions},
            'ask': ask_config
        }
    
    def rules_to_json(self, rules: List[str]) -> List[Dict[str, Any]]:
        """Convert list of DSL rules to JSON follow-up format"""
        return [self.parse_rule(rule) for rule in rules]
    
    def json_to_rules(self, follow_ups: List[Dict[str, Any]]) -> List[str]:
        """Convert JSON follow-ups back to DSL format (for reverse conversion)"""
        rules = []
        for follow_up in follow_ups:
            condition = ','.join(follow_up['when']['in'])
            ask = follow_up['ask']
            
            rule_parts = [f"when:{condition}", "->", f"ask:{ask['id']}:{ask['question_type']}"]
            
            if 'placeholder' in ask:
                rule_parts.append(f":{ask['placeholder']}")
                
                if 'max_chars' in ask:
                    rule_parts.append(f":{ask['max_chars']}")
            
            rules.append(''.join(rule_parts))
        
        return rules
```

### Frontend Code Changes

#### 1. TOML Loading Hook
```javascript
// src/hooks/useLoadQuestions.js
import TOML from '@iarna/toml';
import { FollowUpParser } from '../utils/followUpParser';

const useLoadQuestions = (questionSetId) => {
  const [questions, setQuestions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadQuestionData = async () => {
      try {
        setLoading(true);
        
        // Fetch TOML file
        const response = await fetch(`/questions/${questionSetId}.toml`);
        if (!response.ok) {
          throw new Error(`Failed to load questions: ${response.statusText}`);
        }
        
        const tomlText = await response.text();
        const data = TOML.parse(tomlText);
        
        // Process follow-up rules
        const parser = new FollowUpParser();
        data.questions?.forEach(question => {
          if (question.follow_up_rules) {
            question.follow_ups = parser.rulesToJson(question.follow_up_rules);
            delete question.follow_up_rules;
          }
          
          // Process flattened AI context
          if (question.ai_context_include_answers) {
            question.ai_context = {
              include_answers: question.ai_context_include_answers
            };
            delete question.ai_context_include_answers;
          }
        });
        
        // Process analysis configuration
        if (data.analysis) {
          data.final_analysis_config = processAnalysisConfig(data.analysis);
          delete data.analysis;
        }
        
        setQuestions(data);
        setError(null);
      } catch (err) {
        console.error('Error loading questions:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadQuestionData();
  }, [questionSetId]);

  return { questions, loading, error };
};

function processAnalysisConfig(analysisData) {
  // Convert flattened TOML structure back to nested JSON
  const sections = [];
  
  Object.entries(analysisData).forEach(([key, sectionData]) => {
    if (key === 'loading_message' || key === 'base_prompt') {
      return;
    }
    
    sections.push({
      name: sectionData.name || key,
      model: sectionData.model || 'gpt-4o',
      web_search: {
        enabled: sectionData.web_search_enabled || false,
        max_searches: sectionData.web_search_max_searches || 3
      },
      ai_context: {
        include_answers: sectionData.ai_context_include_answers || [],
        include_scores: sectionData.ai_context_include_scores || false,
        include_overall_score: sectionData.ai_context_include_overall_score || false
      },
      specific_prompt: sectionData.specific_prompt || '',
      output_constraint: sectionData.output_constraint || '',
      model_config: sectionData.model_config || {}
    });
  });
  
  return {
    loading_message: analysisData.loading_message || '',
    base_prompt: analysisData.base_prompt || '',
    sections
  };
}
```

#### 2. Follow-up DSL Parser (JavaScript)
```javascript
// src/utils/followUpParser.js
export class FollowUpParser {
  static DSL_PATTERN = /when:(?<condition>[^-]+)\s*->\s*ask:(?<questionSpec>.+)/;
  static QUESTION_SPEC_PATTERN = /(?<id>[^:]+):(?<type>[^:]+)(?::(?<placeholder>[^:]+))?(?::(?<maxChars>\d+))?/;
  
  parseRule(ruleString) {
    const match = ruleString.trim().match(FollowUpParser.DSL_PATTERN);
    if (!match) {
      throw new Error(`Invalid DSL rule: ${ruleString}`);
    }
    
    const condition = match.groups.condition.trim();
    const questionSpec = match.groups.questionSpec.trim();
    
    // Parse condition
    const conditions = condition.split(',').map(c => c.trim());
    
    // Parse question specification
    const specMatch = questionSpec.match(FollowUpParser.QUESTION_SPEC_PATTERN);
    if (!specMatch) {
      throw new Error(`Invalid question specification: ${questionSpec}`);
    }
    
    const askConfig = {
      id: specMatch.groups.id,
      question_type: specMatch.groups.type
    };
    
    if (specMatch.groups.placeholder) {
      askConfig.placeholder = specMatch.groups.placeholder;
    }
    
    if (specMatch.groups.maxChars) {
      askConfig.max_chars = parseInt(specMatch.groups.maxChars);
    }
    
    // Determine UI type
    const uiMapping = {
      'text': 'text',
      'textarea': 'textarea',
      'number': 'number',
      'choice-single': 'radio',
      'choice-multi': 'multiselect'
    };
    
    if (uiMapping[askConfig.question_type]) {
      askConfig.ui = uiMapping[askConfig.question_type];
    }
    
    return {
      when: { in: conditions },
      ask: askConfig
    };
  }
  
  rulesToJson(rules) {
    return rules.map(rule => this.parseRule(rule));
  }
  
  jsonToRules(followUps) {
    return followUps.map(followUp => {
      const condition = followUp.when.in.join(',');
      const ask = followUp.ask;
      
      let ruleParts = [`when:${condition}`, '->', `ask:${ask.id}:${ask.question_type}`];
      
      if (ask.placeholder) {
        ruleParts.push(`:${ask.placeholder}`);
        
        if (ask.max_chars) {
          ruleParts.push(`:${ask.max_chars}`);
        }
      }
      
      return ruleParts.join(' ');
    });
  }
}
```

### New Dependencies

#### Backend Dependencies
```python
# requirements.txt additions
toml>=0.10.2           # TOML parsing support
```

#### Frontend Dependencies
```json
// package.json additions
{
  "dependencies": {
    "@iarna/toml": "^2.2.5"
  }
}
```

### Configuration Updates

#### Update Configuration File References
```python
# src/backend/config_loader.py
def get_questions_file_path():
    """Return path to questions configuration file"""
    base_path = get_project_root() / "public" / "questions"
    
    # Check for TOML file first, fall back to JSON
    toml_path = base_path / "q4.toml"
    json_path = base_path / "q4.json"
    
    if toml_path.exists():
        return toml_path
    elif json_path.exists():
        return json_path
    else:
        raise FileNotFoundError("No questions configuration file found")
```

---

## Post-Migration Benefits

### 1. **Improved Readability and Maintainability**

#### Before (JSON):
```json
{
  "prompt_add": "Score intent of sale STRICTLY by these rules. CRITICAL RULE: If user selected 'Declining sales' answer, you MUST give score between 0-19 (critical risk), no exceptions. Good answers (score 80-100): planned retirement/move/strategic refocus. Bad answers (score 0-19): urgent cash need, lawsuits/tax issues, declining sales. Follow bands exactly: 0–19 critical; 20–49 high; 50–79 moderate; 80–100 low."
}
```

#### After (TOML):
```toml
# AI Scoring Instructions for Question SG01
prompt_add = """
Score intent of sale STRICTLY by these rules.

CRITICAL RULE: If user selected 'Declining sales' answer, 
you MUST give score between 0-19 (critical risk), no exceptions.

Good answers (score 80-100): 
  - planned retirement/move/strategic refocus

Bad answers (score 0-19): 
  - urgent cash need
  - lawsuits/tax issues
  - declining sales

Follow bands exactly: 
  - 0–19 critical
  - 20–49 high  
  - 50–79 moderate
  - 80–100 low
"""
```

### 2. **Better Configuration Management**

#### Comments Support
```toml
# Basic Information Questions
# These questions collect fundamental business data

[[questions]]
id = "MET.LOC"
text = "Where is the business located?"
# This question doesn't require AI scoring
score = "NO"
# Location helps contextualize all other analysis
ai_validate_prompt = "Rephrase and confirm location..."
```

#### Section Organization
```toml
# =================================================================
# STRATEGIC FUNDAMENTALS SECTION
# Questions that assess core business strategy and sale motivation
# =================================================================

[[questions]]
id = "SG01"
# ... question configuration

[[questions]]
id = "SG02"
# ... question configuration

# =================================================================
# FINANCIAL & LEGAL SITUATION SECTION  
# Questions about financial performance and legal compliance
# =================================================================
```

### 3. **Simplified Follow-up Logic**

#### Before (Complex JSON):
```json
"follow_ups": [
  {
    "when": {"in": ["down_20plus"]},
    "ask": {
      "id": "SG04_REASON",
      "question_type": "text", 
      "ui": "textarea",
      "placeholder": "Main reason for decline",
      "max_chars": 140
    }
  }
]
```

#### After (Simple DSL):
```toml
# Simple, readable follow-up rules
follow_up_rules = [
  "when:down_20plus -> ask:SG04_REASON:text:Main reason for decline:140"
]
```

### 4. **Enhanced Analysis Configuration**

#### Before (Deeply Nested JSON):
```json
"sections": [
  {
    "name": "Business Environment",
    "model": "gpt-4o",
    "web_search": {
      "enabled": true,
      "max_searches": 12
    },
    "ai_context": {
      "include_answers": ["all"],
      "include_scores": true
    }
  }
]
```

#### After (Flat, Clear TOML):
```toml
[analysis.business_environment]
name = "Business Environment"
model = "gpt-4o"
web_search_enabled = true
web_search_max_searches = 12
ai_context_include_answers = "all"
ai_context_include_scores = true
```

### 5. **Future Extensibility**

#### Easy Configuration Additions
```toml
# New features can be easily added with clear documentation

[[questions]]
id = "NEW_QUESTION"
text = "New question text"
# Feature flag for gradual rollout
experimental = true
# A/B testing configuration
ab_test = {variant = "A", split = 0.5}
# Custom validation rules
validation = {min_length = 10, max_length = 500}
# Integration with external systems
external_sync = {enabled = true, endpoint = "/api/sync"}
```

#### Modular Configuration
```toml
# Include external configuration modules
[includes]
industry_specific = "industries/manufacturing.toml"
regional_config = "regions/north_america.toml"
experimental_features = "experiments/q1_2024.toml"
```

### 6. **Better Development Experience**

#### IDE Support
- Syntax highlighting for TOML files
- Built-in validation and error detection  
- Auto-completion for known configuration keys
- Folding support for long sections

#### Version Control Benefits
- Cleaner diffs when configurations change
- Better merge conflict resolution
- Easier to track changes in multi-line strings
- Comments preserved in version history

#### Documentation Integration
```toml
# This configuration follows the M&A Risk Assessment Framework v2.1
# See: docs/risk-assessment-methodology.md

[metadata]
framework_version = "2.1"
last_updated = "2024-01-15"
reviewed_by = "Senior Analyst Team"
next_review = "2024-04-15"

# Configuration validation schema
[schema]
version = "1.0"
validation_rules = "schemas/questions-v1.json"
```

---

## Success Criteria & Validation

### Phase 1 Success Criteria
- [ ] **Complete TOML Conversion**: All 49 questions converted to valid TOML format
- [ ] **DSL Implementation**: Follow-up DSL covers all existing follow-up scenarios
- [ ] **Analysis Config**: All 8 analysis sections properly flattened and functional
- [ ] **Multi-line Prompts**: All AI prompts properly formatted and readable
- [ ] **Validation Script**: Automated script confirms structural integrity

### Phase 2 Success Criteria  
- [ ] **DSL Parser**: Python and JavaScript parsers handle all DSL patterns correctly
- [ ] **Unit Test Coverage**: 100% test coverage for DSL parsing and edge cases
- [ ] **Performance**: DSL parsing adds <50ms overhead to question loading
- [ ] **Error Handling**: Clear error messages for malformed DSL rules
- [ ] **Bidirectional Conversion**: Can convert DSL ↔ JSON format losslessly

### Phase 3 Success Criteria
- [ ] **Backend Integration**: All API endpoints work with TOML data
- [ ] **Frontend Integration**: UI renders all question types correctly
- [ ] **Follow-up Logic**: All conditional question flows work as expected
- [ ] **AI Evaluation**: Question evaluation produces identical results to JSON version
- [ ] **End-to-End Testing**: Complete user flows function without regression

### Overall Migration Success Criteria
- [ ] **Data Equivalence**: TOML data produces identical functionality to JSON data
- [ ] **Performance**: TOML loading performance within 2x of JSON performance
- [ ] **No Functionality Loss**: All features work exactly as before migration
- [ ] **Improved Maintainability**: Configuration is demonstrably easier to read and modify
- [ ] **Documentation**: Complete documentation for new TOML format and DSL

### Rollback Criteria
If any of these conditions occur, migration should be rolled back:
- [ ] **Data Loss**: Any question data or configuration is lost or corrupted
- [ ] **Performance Degradation**: >3x performance degradation in any area
- [ ] **Functionality Regression**: Any existing functionality breaks
- [ ] **Critical Bug**: Any bug that prevents core application functionality
- [ ] **Team Rejection**: Development team cannot effectively maintain TOML format

---

## Rollback Procedures

### Immediate Rollback (Emergency)
If critical issues are discovered in production:

1. **Revert File Reference**
   ```python
   # In get_questions_file_path()
   # Temporarily force JSON loading
   return base_path / "q4.json.backup"
   ```

2. **Frontend Fallback**
   ```javascript
   // Emergency fallback in useLoadQuestions.js
   try {
     const tomlData = await loadTOMLData();
     return tomlData;
   } catch (error) {
     console.warn('TOML loading failed, falling back to JSON');
     return await loadJSONData(); // Fallback implementation
   }
   ```

3. **Configuration Toggle**
   ```python
   # Add to app configuration
   USE_TOML_QUESTIONS = False  # Emergency switch
   ```

### Gradual Rollback (Planned)
For planned rollback due to issues:

1. **Phase 3 Rollback** (Remove integrations)
   - Revert backend loaders to JSON format
   - Remove TOML parsing from frontend
   - Remove DSL parser dependencies
   - Duration: 1-2 hours

2. **Phase 2 Rollback** (Remove DSL)
   - Remove DSL parser implementation
   - Revert to original JSON follow-up structure
   - Duration: 2-4 hours

3. **Phase 1 Rollback** (Remove TOML files)
   - Delete q4.toml file
   - Restore q4.json from backup
   - Remove TOML dependencies
   - Duration: 1 hour

### Rollback Validation
After any rollback:
- [ ] All question loading functions work correctly
- [ ] Follow-up logic functions as expected
- [ ] AI evaluation produces correct results
- [ ] No new errors or warnings in logs
- [ ] Application performance returns to baseline

---

## Conclusion

This migration from JSON to TOML format will significantly improve the maintainability and readability of the QnA Evaluator system's configuration. The key innovations include:

1. **Follow-up DSL**: Simplifying complex conditional logic into readable string rules
2. **Flattened Structure**: Reducing nesting levels while preserving functionality  
3. **Multi-line Support**: Making long AI prompts readable and maintainable
4. **Comments**: Enabling inline documentation for complex business logic

The 3-phase implementation plan provides a structured approach with clear success criteria and comprehensive testing at each stage. The estimated 4-7 day timeline includes ample time for testing and validation to ensure no functionality is lost during migration.

Risk mitigation strategies, comprehensive testing plans, and detailed rollback procedures ensure that the migration can be executed safely with minimal risk to the production system.

Upon successful completion, the development team will have a more maintainable, readable, and extensible configuration system that will significantly improve productivity for future enhancements and modifications to the QnA Evaluator.