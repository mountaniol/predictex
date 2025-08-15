import React, { useState } from 'react';

interface QuestionEditorProps {
  textInput: string;
  onTextChange: (text: string) => void;
  parseErrors: string[];
  aiScore: number | null;
  aiExplanation: string;
  onSendToAI: () => void;
  onSaveQuestion: () => void;
  onTemplateClick: (type: string) => void;
  canSendToAI: boolean;
  canSave: boolean;
}

const QuestionEditor: React.FC<QuestionEditorProps> = ({
  textInput,
  onTextChange,
  parseErrors,
  aiScore,
  aiExplanation,
  onSendToAI,
  onSaveQuestion,
  onTemplateClick,
  canSendToAI,
  canSave
}) => {
  const [showHelp, setShowHelp] = useState<boolean>(false);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);

  const handleSendToAI = async () => {
    setIsEvaluating(true);
    try {
      await onSendToAI();
    } finally {
      setIsEvaluating(false);
    }
  };

  const helpContent = `
🎯 QUESTIONNAIRE BUILDER GUIDE
═══════════════════════════════════════════════════════════════════════════

📝 What is this?
This tool helps you create business risk assessment questionnaires. Think of it as 
building a survey where each question gets automatically scored by AI to assess 
business risks. No programming knowledge needed!

✅ REQUIRED FIELDS (Every question needs these):

• id: SG02                    🆔 Unique name for your question (like SG01, MET.LOC)
• text: Question text?        ❓ The actual question you want to ask
• cluster: Section Name       📂 Which section/group this belongs to
• position: 2                 📊 Order within the section (1, 2, 3...)
• type: question_type         🔧 What kind of answer you want (see types below)

🔧 QUESTION TYPES (How people will answer):

• text                       📝 Single line text box (names, short answers)
• textarea                   📄 Multi-line text box (longer explanations)  
• number                     🔢 Numbers only (revenue, employees, etc.)
• yes-no                     ✅ Simple Yes/No choice
• choice-single              ⚪ Pick one option from a list
• choice-multi               ☑️ Pick multiple options from a list

⚙️ OPTIONAL FIELDS (Add these if you want):

• hint: Brief tooltip         💡 Helpful text shown under the question
• info: Detailed explanation  ℹ️ More info in a popup bubble
• ui: interface_variant       🎨 Change how the question looks (see UI types)
• score: AUTO/NO             🤖 Should AI score this? (explained below)

🎨 UI VARIANTS (How questions look):

• radio                      ⚪ Round buttons (for single choice)
• dropdown                   📋 Dropdown menu (saves space)
• multiselect               ☑️ Checkboxes (for multiple choice)

📋 FOR CHOICE QUESTIONS (when type is choice-single or choice-multi):

• option: Label              📝 Each possible answer (code auto-generated)
• option: Other              ✨ Special "Other" option (enables text field)
• max_selections: 2          🔢 Limit how many options can be picked (multi only)

🔗 DEPENDENCIES (Make questions depend on others):

• include: Q1, Q2            🔗 This question needs answers from Q1 and Q2 first

🤖 AI INSTRUCTIONS:

• prompt: Explain to AI how to process the question
                            💭 Tell the AI exactly how to score this question

🎯 SCORING SYSTEM:

• score: AUTO               ✅ AI will automatically score this (0-100 points)
• score: NO                 📋 Question provides context but isn't scored itself
                               (useful for background info that helps AI score other questions)

📚 EXAMPLES:

💼 Basic Text Question:
id: BIZ01
text: What is your primary revenue source?
cluster: Business Basics
position: 1
type: text
hint: Main source of income
score: AUTO

✅ Yes/No Question:
id: REV01
text: Has revenue grown in the last 12 months?
cluster: Financial Health
position: 1
type: yes-no
prompt: Score based on growth trajectory and market conditions
score: AUTO

⚪ Single Choice with Dependencies:
id: RISK02
text: What is your biggest operational risk?
cluster: Risk Assessment
position: 2
type: choice-single
ui: radio
option: Staff shortage
option: Supply chain disruption
option: Technology failure
option: Other
include: BIZ01, REV01
prompt: Consider the business context from previous answers
score: AUTO

☑️ Multiple Choice Question:
id: MARKET01
text: Which markets do you operate in?
cluster: Market Position
position: 1
type: choice-multi
max_selections: 3
option: Local/Regional
option: National
option: International
option: Online only
score: AUTO

📋 Context-Only Question (not scored):
id: META01
text: Company location
cluster: Company Info
position: 1
type: text
hint: Used for context in other questions
score: NO

🚀 GETTING STARTED:

1. Use the template buttons above to start quickly
2. Start with id, text, cluster, position, and type
3. Add options if using choice types
4. Add other fields as needed
5. Click "Add Question" to see the preview

💡 TIPS:
• Keep question text clear and specific
• Use hints for clarification
• Group related questions in the same cluster
• Start with score: AUTO for most questions
• Use score: NO for background/context questions
  `;

  return (
    <div className="question-editor">
      <div className="editor-header">
        <h3>Adding Question</h3>
        <div className="header-buttons">
          <button
            className="help-btn yellow"
            onClick={() => setShowHelp(!showHelp)}
            title="Show format help"
          >
            ?
          </button>
          {parseErrors.length > 0 && (
            <button
              className="error-btn red"
              title={parseErrors.join('\n')}
            >
              !
            </button>
          )}
        </div>
      </div>

      {showHelp && (
        <div className="help-content">
          <pre>{helpContent}</pre>
        </div>
      )}

      {/* Template Buttons */}
      <div className="template-buttons">
        <div className="template-buttons-header">
          <label>Quick Templates:</label>
        </div>
        <div className="template-buttons-row">
          <button 
            className="btn btn-template" 
            onClick={() => onTemplateClick('text')}
            title="Single line text input"
          >
            📝 Text
          </button>
          <button 
            className="btn btn-template"
            onClick={() => onTemplateClick('textarea')}
            title="Multi-line text area"
          >
            📄 TextArea
          </button>
          <button 
            className="btn btn-template"
            onClick={() => onTemplateClick('number')}
            title="Numeric input"
          >
            🔢 Number
          </button>
          <button 
            className="btn btn-template"
            onClick={() => onTemplateClick('yes-no')}
            title="Yes/No radio buttons"
          >
            ✅ Yes/No
          </button>
          <button 
            className="btn btn-template"
            onClick={() => onTemplateClick('choice-single')}
            title="Single selection"
          >
            ⚪ Single Choice
          </button>
          <button 
            className="btn btn-template"
            onClick={() => onTemplateClick('choice-multi')}
            title="Multiple selection"
          >
            ☑️ Multi Choice
          </button>
        </div>
      </div>

      <div className="editor-content">
        <div className="text-input-section">
          <label>The question showed to user</label>
          <textarea
            value={textInput}
            onChange={(e) => onTextChange(e.target.value)}
            placeholder={`Enter question details in the following format:

id: SG02
text: Have there been serious buyers in the last 6 months?
hint: LOI or DD access counts as serious
cluster: Strategic Fundamentals
position: 2
type: choice-single
option: No
option: Only initial inquiries
option: LOI or due diligence access`}
            className={`question-input ${parseErrors.length > 0 ? 'error' : ''}`}
            rows={12}
          />

          {parseErrors.length > 0 && (
            <div className="parse-errors">
              <h4>Parsing Errors:</h4>
              <ul>
                {parseErrors.map((error, index) => (
                  <li key={index} className="error-message">
                    {error}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="action-buttons">
          <button
            onClick={handleSendToAI}
            disabled={!canSendToAI || isEvaluating}
            className="btn btn-primary"
          >
            {isEvaluating ? 'Evaluating...' : 'Send to AI >'}
          </button>
          <button
            onClick={onSaveQuestion}
            disabled={!canSave}
            className="btn btn-secondary"
          >
            Save the question
          </button>
        </div>

        {/* AI Response Section */}
        {(aiScore !== null || aiExplanation) && (
          <div className="ai-response">
            <div className="ai-score-section">
              <label>Score:</label>
              <div className="score-display">
                {aiScore !== null ? aiScore : 'N/A'}
              </div>
            </div>
            
            <div className="ai-explanation-section">
              <label>Explanation:</label>
              <textarea
                value={aiExplanation}
                readOnly
                className="explanation-display"
                rows={6}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default QuestionEditor;