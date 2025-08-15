import React, { useState } from 'react';

interface QuestionEditorProps {
  textInput: string;
  onTextChange: (text: string) => void;
  parseErrors: string[];
  aiScore: number | null;
  aiExplanation: string;
  onSendToAI: () => void;
  onSaveQuestion: () => void;
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
Question Format Help:

Required Fields:
• id: SG02                    (Unique question identifier)
• text: Question text?        (The actual question)
• cluster: Section Name       (Groups questions together)
• position: 2                 (Order within the section)
• type: question_type         (See types below)

Optional Fields:
• hint: Brief tooltip         (Shown under question)
• info: Detailed explanation  (Info bubble)
• ui: interface_variant       (Override default UI)
• score: AUTO/NO             (AUTO=evaluate, NO=skip)

Question Types:
• text                       (Single line text input)
• textarea                   (Multi-line text area)  
• number                     (Numeric input)
• yes-no                     (Yes/No radio buttons)
• choice-single              (Single selection)
• choice-multi               (Multiple selection)

For Choice Questions:
• option: code -> Label      (Answer options)
• with_other: true/false     (Enable "Other" option)
• other_text_id: ID_OTHER    (ID for "Other" text field)
• max_selections: 2          (For multi-choice only)

UI Variants:
• radio                      (Radio buttons)
• dropdown                   (Select dropdown)
• multiselect               (Checkbox group)

Dependencies:
• include_answers: Q1, Q2    (Questions this depends on)
• include_meta: MET.LOC      (Meta information to include)

AI Instructions:
• prompt_add: Additional scoring instructions for AI

Example:
id: SG02
text: Have there been serious buyers in the last 6 months?
hint: LOI or DD access counts as serious
cluster: Strategic Fundamentals
position: 2
type: choice-single
ui: radio
option: no -> No
option: initial -> Only initial inquiries
option: loi -> LOI or due diligence access
include_answers: SG01
score: AUTO
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
option: no -> No
option: initial -> Only initial inquiries
option: loi -> LOI or due diligence access`}
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