import React from 'react';

interface QuestionData {
  id: string;
  text: string;
  hint?: string;
  info?: string;
  cluster_name: string;
  position_in_cluster: number;
  question_type: string;
  ui?: string;
  options?: Array<{code: string, label: string}>;
  with_other?: boolean;
  other_text_id?: string;
  max_selections?: number;
  ranked?: boolean;
}

interface QuestionPreviewProps {
  question: QuestionData | null;
  hasErrors: boolean;
}

const QuestionPreview: React.FC<QuestionPreviewProps> = ({ question, hasErrors }) => {
  if (hasErrors) {
    return (
      <div className="question-preview error">
        <h3>Live Preview</h3>
        <div className="preview-error">
          <p>⚠️ Please fix parsing errors to see preview</p>
        </div>
      </div>
    );
  }

  if (!question) {
    return (
      <div className="question-preview empty">
        <h3>Live Preview</h3>
        <div className="preview-placeholder">
          <p>Start typing to see how your question will look...</p>
        </div>
      </div>
    );
  }

  const renderQuestionInput = () => {
    switch (question.question_type) {
      case 'text':
        return (
          <input
            type="text"
            placeholder="Type text..."
            className="preview-input text-input"
          />
        );

      case 'textarea':
        return (
          <textarea
            placeholder="Type text..."
            className="preview-input textarea-input"
            rows={4}
          />
        );

      case 'number':
        return (
          <input
            type="number"
            placeholder="0"
            className="preview-input number-input"
          />
        );

      case 'yes-no':
        return (
          <div className="preview-input radio-group">
            <label className="radio-option">
              <input type="radio" name="yes-no-preview" />
              <span>Yes</span>
            </label>
            <label className="radio-option">
              <input type="radio" name="yes-no-preview" />
              <span>No</span>
            </label>
          </div>
        );

      case 'choice-single':
        if (question.ui === 'dropdown') {
          return (
            <select className="preview-input dropdown-input">
              <option>Select an option...</option>
              {question.options?.map((option, index) => (
                <option key={index} value={option.code}>
                  {option.label}
                </option>
              ))}
              {question.with_other && <option value="other">Other</option>}
            </select>
          );
        } else {
          // Default to radio buttons
          return (
            <div className="preview-input radio-group">
              {question.options?.map((option, index) => (
                <label key={index} className="radio-option">
                  <input
                    type="radio"
                    name={`choice-single-${question.id}`}
                    value={option.code}
                  />
                  <span>{option.label}</span>
                </label>
              ))}
              {question.with_other && (
                <label className="radio-option">
                  <input
                    type="radio"
                    name={`choice-single-${question.id}`}
                    value="other"
                  />
                  <span>Other</span>
                </label>
              )}
            </div>
          );
        }

      case 'choice-multi':
        return (
          <div className="preview-input checkbox-group">
            {question.options?.map((option, index) => (
              <label key={index} className="checkbox-option">
                <input
                  type="checkbox"
                  value={option.code}
                />
                <span>{option.label}</span>
              </label>
            ))}
            {question.with_other && (
              <label className="checkbox-option">
                <input type="checkbox" value="other" />
                <span>Other</span>
              </label>
            )}
            {question.max_selections && (
              <div className="selection-info">
                <small>Select up to {question.max_selections} options</small>
              </div>
            )}
          </div>
        );

      default:
        return (
          <div className="preview-input unknown-type">
            <p>Unknown question type: {question.question_type}</p>
          </div>
        );
    }
  };

  return (
    <div className="question-preview">
      <h3>Live Preview</h3>
      <div className="preview-content">
        {/* Question header - similar to existing UI */}
        <div className="question-header">
          <div className="question-meta">
            <span className="question-id">{question.id}</span>
            <span className="question-cluster">{question.cluster_name}</span>
            <span className="question-position">#{question.position_in_cluster}</span>
          </div>
        </div>

        {/* Question text */}
        <div className="question-text">
          <h4>{question.text}</h4>
        </div>

        {/* Hint */}
        {question.hint && (
          <div className="question-hint">
            <span className="hint-icon">💡</span>
            <span className="hint-text">{question.hint}</span>
          </div>
        )}

        {/* Info bubble */}
        {question.info && (
          <div className="question-info">
            <details>
              <summary>ℹ️ More info</summary>
              <p>{question.info}</p>
            </details>
          </div>
        )}

        {/* Question input */}
        <div className="question-input-area">
          {renderQuestionInput()}
        </div>

        {/* Other text field if applicable */}
        {question.with_other && question.question_type.includes('choice') && (
          <div className="other-text-field">
            <input
              type="text"
              placeholder="Please specify..."
              className="preview-input other-input"
            />
          </div>
        )}

        {/* Question metadata */}
        <div className="question-metadata">
          <div className="metadata-item">
            <strong>Type:</strong> {question.question_type}
            {question.ui && ` (${question.ui})`}
          </div>
          {question.max_selections && (
            <div className="metadata-item">
              <strong>Max selections:</strong> {question.max_selections}
            </div>
          )}
          {question.ranked && (
            <div className="metadata-item">
              <strong>Ranked:</strong> Yes
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default QuestionPreview;