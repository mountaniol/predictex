# Question Creator Parser Format Guide

## 🎯 What is this?

The Question Creator helps you build business risk assessment questionnaires using simple text format. Think of it as creating a smart survey where:
- ✅ People answer business questions
- 🤖 AI automatically scores answers (0-100 points)  
- 📊 Results help assess business risks and opportunities
- 📋 Some questions provide context for better AI scoring

No programming knowledge required!

## 📝 Basic Format Rules

### Simple Keyword Format
- Each line: `keyword: value` (lowercase, simple and clean)
- Keywords are case-insensitive  
- Unknown lines continue the previous field
- Multiline content just keeps going until the next keyword

### ✅ Required Fields (Every question needs these)
- **id:** - Unique identifier (like SG01, MET.LOC, BIZ01)
- **text:** - The actual question you want to ask
- **cluster:** - Section name that groups related questions
- **position:** - Order within the section (1, 2, 3...)
- **type:** - How people will answer (see types below)

### ⚙️ Optional Fields (Add these if you want)
- **hint:** - Helpful text shown under the question
- **info:** - Detailed explanation in a popup bubble
- **ui:** - Change how the question looks (radio, dropdown, multiselect)
- **option:** - Answer choice (for choice questions - repeat for multiple)
- **max_selections:** - Limit selections for multi-choice (number)
- **prompt:** - Tell AI exactly how to score this question
- **include:** - Questions this depends on (comma-separated IDs)
- **score:** - Should AI score this? (AUTO=yes, NO=context only)

## 🔧 Question Types (How people answer)

### Text Input Types
```
type: text          # 📝 Single line text box (names, short answers)
type: textarea      # 📄 Multi-line text box (detailed explanations)
type: number        # 🔢 Numbers only (revenue, employees, etc.)
```

### Choice Types
```
type: yes-no        # ✅ Simple Yes/No choice
type: choice-single # ⚪ Pick one option from a list
type: choice-multi  # ☑️ Pick multiple options from a list
```

## 📋 For Choice Questions

### Simple Option Format
```
option: Staff shortage
option: Supply chain disruption
option: Technology failure
option: Other
```

**What happens automatically:**
- ✅ No codes needed - they're auto-generated from labels
- ✅ `Staff shortage` becomes code `staff_shortage`
- ✅ Special `option: Other` automatically enables text field
- ✅ Codes are made from: lowercase, spaces→underscores, clean formatting

### 🎨 UI Variants (How questions look)
```
ui: radio       # ⚪ Round buttons (default for single choice)
ui: dropdown    # 📋 Dropdown menu (saves space)
ui: multiselect # ☑️ Checkboxes (default for multiple choice)
```

### 🔢 Multi-Choice Limits
```
type: choice-multi
max_selections: 3    # Limit to 3 selections maximum
option: Option A
option: Option B
option: Option C
option: Option D
option: Other
```

## 🎯 Scoring System (How AI evaluates)

### Two Types of Questions
```
score: AUTO     # ✅ AI will score this question (0-100 points)
score: NO       # 📋 Question provides context but isn't scored itself
```

**When to use `score: NO`:**
- Background information (company location, industry, contact info)
- Meta data that helps AI understand other answers
- Questions that provide context but don't assess risk themselves

**When to use `score: AUTO`:**
- Questions that directly assess business risks or opportunities
- Most of your questionnaire should use this
- AI gives 0-100 points based on your prompt instructions

## 🤖 AI Instructions

### Tell AI How to Score
```
prompt: Score based on growth trajectory and market conditions
prompt: Evaluate risk severity and company preparedness  
prompt: Consider market diversification and expansion risks
```

### Dependencies (Advanced)
```
include: SG01, SG02, MET.LOC    # Questions this depends on
```
- Makes this question wait for others to be answered first
- Helps AI understand context from previous answers

## 📝 Multiline Content

These fields can span multiple lines:
- **text:** - Question text (can be long with bullets, etc.)
- **prompt:** - AI instructions (detailed criteria)
- **hint:** - Hint text
- **info:** - Info bubble content

### Multiline Example
```
id: STRATEGY01
text: What is your business strategy?
Please provide detailed information about:
- Market positioning
- Competitive advantages
- Growth plans
prompt: Evaluate this strategic response carefully.
Consider the following criteria:
1. Clarity of vision
2. Market understanding  
3. Competitive analysis
cluster: Strategic Planning
position: 1
type: textarea
score: AUTO
```

## 📚 Complete Examples

### 💼 Basic Text Question
```
id: BIZ01
text: What is your primary revenue source?
cluster: Business Basics
position: 1
type: text
hint: Main source of income
prompt: Evaluate based on revenue stability and market position
score: AUTO
```

### ✅ Yes/No Question
```
id: REV01
text: Has revenue grown in the last 12 months?
cluster: Financial Health
position: 1
type: yes-no
hint: Compare to previous year
prompt: Score based on growth trajectory and market conditions
score: AUTO
```

### ⚪ Single Choice Question
```
id: RISK02
text: What is your biggest operational risk?
cluster: Risk Assessment
position: 2
type: choice-single
ui: radio
option: Staff shortage
option: Supply chain disruption
option: Technology failure
option: Regulatory changes
option: Other
hint: Select the most significant risk
prompt: Evaluate risk severity and company preparedness
include: BIZ01
score: AUTO
```

### ☑️ Multiple Choice Question
```
id: MARKET01
text: Which markets do you operate in?
cluster: Market Position
position: 1
type: choice-multi
option: Local/Regional
option: National
option: International
option: Online only
max_selections: 3
hint: Select all that apply
prompt: Consider market diversification and expansion risks
score: AUTO
```

### 📋 Context-Only Question (Not Scored)
```
id: META01
text: Company location
cluster: Company Info
position: 1
type: text
hint: Used for context in other questions
score: NO
```

## Parsing Logic

### Field Processing
1. **Keyword Recognition**: Parser only processes known keywords
2. **Multiline Continuation**: Non-keyword lines are appended to the current field
3. **Auto-Generation**: 
   - Option codes generated from labels
   - "Other" options automatically enable text fields
   - other_text_id set to `{ID}_OTHER`
4. **Field Mapping**:
   - `CLUSTER` → `cluster_name`
   - `POSITION` → `position_in_cluster`
   - `TYPE` → `question_type`
   - `PROMPT` → `prompt_add`
   - `ROLE` → appended to `prompt_add`

### Validation Rules
- **ID Format**: Must match pattern `[A-Z]+[0-9]*[A-Z]?` (e.g., SG01, MET.LOC)
- **Required Fields**: ID, TEXT, CLUSTER, POSITION, TYPE must be present
- **Choice Validation**: Choice questions require at least one OPTION
- **Type Validation**: TYPE must be one of: text, textarea, number, yes-no, choice-single, choice-multi

### Error Handling
- Missing required fields generate specific error messages
- Invalid formats provide guidance on correct syntax
- Unknown question types list valid alternatives
- Empty options are rejected with helpful messages

## JSON Output Format

The parser generates JSON compatible with the main QnA Evaluator:

```json
{
  "id": "SG05",
  "text": "How would you rate your market position?",
  "cluster_name": "Market Analysis",
  "position_in_cluster": 2,
  "question_type": "choice-single",
  "ui": "radio",
  "options": [
    {"code": "market_leader", "label": "Market leader"},
    {"code": "strong_competitor", "label": "Strong competitor"},
    {"code": "emerging_player", "label": "Emerging player"},
    {"code": "struggling", "label": "Struggling"},
    {"code": "other", "label": "Other"}
  ],
  "options_sort": "as_is",
  "with_other": true,
  "other_text_id": "SG05_OTHER",
  "hint": "Choose the option that best describes your current position",
  "ai_context": {
    "include_answers": ["SG01", "SG03"]
  },
  "prompt_add": "Evaluate the company's self-assessment of market position. Consider:\n- Realistic self-awareness\n- Supporting evidence mentioned\n- Market understanding depth\n\nRole: You are a market research expert evaluating business positioning",
  "score": "AUTO"
}
```

## 🚀 Getting Started Guide

### Step-by-Step Process
1. **Start Simple**: Use template buttons for quick examples
2. **Required First**: Begin with id, text, cluster, position, type
3. **Add Options**: For choice questions, add your options
4. **AI Instructions**: Add prompt to tell AI how to score
5. **Preview & Test**: Use the preview to see how it looks
6. **Build Gradually**: Add questions one by one

### 💡 Pro Tips for Success

#### Question Design
- **Keep it clear**: Avoid jargon and ambiguous wording
- **Be specific**: "Revenue in 2024" vs "Recent revenue"  
- **One concept per question**: Don't ask about multiple things
- **Use business language**: Match your industry terminology

#### Scoring Strategy
- **Most questions → AUTO**: These drive your risk assessment
- **Background → NO**: Company info, metadata, context
- **Good prompts matter**: Tell AI exactly what to look for
- **Include context**: Use dependencies to give AI more info

#### Organization Tips
- **Group smartly**: Related questions in same cluster
- **Order matters**: Start general, get more specific
- **Number logically**: 1, 2, 3... within each cluster
- **Use prefixes**: SG01, FIN01, RISK01 for easy organization

### 🔍 Quality Checklist

Before adding a question, ask yourself:
- [ ] Is the question clear and unambiguous?
- [ ] Does it gather useful business information?
- [ ] Is the cluster name descriptive?
- [ ] Are option labels clear and comprehensive?
- [ ] Does the prompt help AI score appropriately?
- [ ] Is this question necessary or does it duplicate others?
- [ ] Would a business person understand what I'm asking?

### 🛠️ Common Fixes

**"My options aren't showing"**
- Check you're using `option:` (not `options:`)
- Make sure question type is choice-single or choice-multi

**"AI isn't scoring well"**
- Add more specific prompt instructions
- Include context from other questions with `include:`
- Make sure question text is clear about what you want

**"Questions seem out of order"**
- Check your position numbers (1, 2, 3...)
- Make sure cluster names are consistent
- Questions display by cluster, then position

**"Preview looks wrong"**
- Verify all required fields are present
- Check spelling of keywords (text:, type:, etc.)
- Look for missing colons after keywords

This simple format lets you create powerful, AI-evaluated business questionnaires that help assess risks and opportunities - no programming required!