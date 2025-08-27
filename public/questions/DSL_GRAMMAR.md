# Follow-up DSL Grammar Specification

## Overview
This DSL (Domain Specific Language) simplifies complex follow-up logic in questions from nested JSON objects to simple, readable string rules.

## Grammar Definition

```
follow_up_rule := "when:" condition " -> ask:" question_spec

condition := value | value_list
value_list := value ("," value)*
value := [a-zA-Z0-9_]+

question_spec := question_id ":" question_type [":" placeholder [":" max_chars]]
question_id := [a-zA-Z0-9_]+
question_type := "text" | "textarea" | "number" | "choice-single" | "choice-multi"
placeholder := string_literal
max_chars := integer
```

## Examples from q4.json

### Example 1: SG04 Revenue Decline Follow-up
**Original JSON:**
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

**DSL Equivalent:**
```toml
follow_up_rules = [
  "when:down_20plus -> ask:SG04_REASON:text:Main reason for decline:140"
]
```

### Example 2: SG05 Yes/No Follow-up
**Original JSON:**
```json
"follow_ups": [
  {
    "when": {"in": ["yes"]},
    "ask": {
      "id": "SG05_NOTE",
      "question_type": "text",
      "ui": "textarea",
      "placeholder": "Brief reason",
      "max_chars": 120
    }
  }
]
```

**DSL Equivalent:**
```toml
follow_up_rules = [
  "when:yes -> ask:SG05_NOTE:text:Brief reason:120"
]
```

### Example 3: Multiple Conditions (hypothetical)
```toml
follow_up_rules = [
  "when:option1,option2 -> ask:FOLLOW_UP:textarea:Please explain:200"
]
```

## DSL Syntax Rules

### 1. **Condition Matching**
- Single value: `when:down_20plus`
- Multiple values: `when:option1,option2,option3`
- Case-sensitive matching
- No spaces around commas in value lists

### 2. **Question Specification**
- Minimum required: `question_id:question_type`
- With placeholder: `question_id:question_type:Placeholder text`
- Full specification: `question_id:question_type:Placeholder text:140`

### 3. **Question Type Mapping**
- `text` → `{"question_type": "text", "ui": "text"}`
- `textarea` → `{"question_type": "text", "ui": "textarea"}`
- `number` → `{"question_type": "number", "ui": "number"}`
- `choice-single` → `{"question_type": "choice-single", "ui": "radio"}`
- `choice-multi` → `{"question_type": "choice-multi", "ui": "multiselect"}`

### 4. **Default Values**
- If `placeholder` omitted: no placeholder set
- If `max_chars` omitted: no character limit
- UI type is automatically inferred from question_type

## Validation Rules

### 1. **Syntax Validation**
```python
DSL_PATTERN = re.compile(
    r'when:(?P<condition>[^-]+)\s*->\s*ask:(?P<question_spec>.+)'
)

QUESTION_SPEC_PATTERN = re.compile(
    r'(?P<id>[^:]+):(?P<type>[^:]+)(?::(?P<placeholder>[^:]+))?(?::(?P<max_chars>\d+))?'
)
```

### 2. **Semantic Validation**
- Question ID must be unique within questionnaire
- Question type must be valid
- Max chars must be positive integer if specified
- Placeholder cannot contain colons (use alternative separators if needed)

### 3. **Error Messages**
- Invalid syntax: `"Invalid DSL rule: {rule_string}"`
- Invalid question spec: `"Invalid question specification: {question_spec}"`
- Invalid question type: `"Unknown question type: {type}"`
- Invalid max_chars: `"Max chars must be positive integer: {max_chars}"`

## Parser Implementation Strategy

### Python Parser
```python
class FollowUpParser:
    def parse_rule(self, rule_string: str) -> dict
    def rules_to_json(self, rules: list) -> list
    def json_to_rules(self, follow_ups: list) -> list  # For reverse conversion
```

### JavaScript Parser
```javascript
class FollowUpParser {
    parseRule(ruleString: string): object
    rulesToJson(rules: string[]): object[]
    jsonToRules(followUps: object[]): string[]  // For reverse conversion
}
```

## Benefits of DSL Approach

### 1. **Readability**
- Before: 13 lines of nested JSON
- After: 1 line of readable DSL

### 2. **Maintainability**
- Clear intent: "when X happens, ask Y"
- No deep nesting to navigate
- Easy to add/remove/modify rules

### 3. **Type Safety**
- Grammar enforces valid structure
- Parser validates all components
- Clear error messages for invalid rules

### 4. **Extensibility**
- Easy to add new question types
- Can extend syntax for complex conditions
- Backwards compatible

## Edge Cases and Limitations

### 1. **Special Characters in Placeholder**
- Colons in placeholder text not supported (use alternative separators)
- Solution: Use `|` or `~` as internal separator if needed

### 2. **Complex Conditions**
- Current DSL supports only "OR" logic (any value matches)
- Future: Could extend to support AND logic: `when:val1&val2`

### 3. **Multiple Follow-ups**
- Multiple rules per question supported
- Each rule creates separate follow-up question

### 4. **Internationalization**
- Placeholder text in DSL uses source language
- Translation handled at UI layer, not DSL level

## Testing Strategy

### Unit Tests
```python
def test_simple_rule():
    rule = "when:yes -> ask:TEST:text:Explain:100"
    result = parser.parse_rule(rule)
    assert result['when']['in'] == ['yes']
    assert result['ask']['id'] == 'TEST'

def test_multiple_conditions():
    rule = "when:opt1,opt2 -> ask:TEST:textarea:Details"
    result = parser.parse_rule(rule)
    assert result['when']['in'] == ['opt1', 'opt2']

def test_minimal_spec():
    rule = "when:yes -> ask:TEST:text"
    result = parser.parse_rule(rule)
    assert 'placeholder' not in result['ask']
    assert 'max_chars' not in result['ask']
```

### Integration Tests
```python
def test_bidirectional_conversion():
    """Test DSL -> JSON -> DSL roundtrip conversion"""
    original_json = {...}  # Original follow-up structure
    dsl_rules = parser.json_to_rules(original_json)
    converted_json = parser.rules_to_json(dsl_rules)
    assert original_json == converted_json
```

## Migration Path

### Phase 1: Create DSL Parsers
1. Implement Python parser with all test cases
2. Implement JavaScript parser with identical behavior
3. Validate with all existing follow-up scenarios

### Phase 2: Apply to TOML Conversion
1. Convert all follow-ups in q4.json to DSL format
2. Validate semantic equivalence
3. Update backend to use DSL parser

### Phase 3: Integration Testing
1. Test complete question flow with DSL
2. Verify UI behavior unchanged
3. Performance testing vs original JSON

This DSL grammar provides a clean, readable, and maintainable approach to expressing follow-up logic while preserving all functionality of the original JSON structure.