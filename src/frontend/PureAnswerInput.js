/**
 * Pure Answer Input Component for Server-Driven UI
 * 
 * Completely pure React component with ZERO business logic:
 * - Only renders UI based on props
 * - No state management or side effects
 * - Dispatches events to Server-Driven UI system
 * - All business logic handled by backend
 */

import React from 'react';

/**
 * Pure Answer Input - Mathematical guarantee: No side effects
 * @param {Object} question - Question configuration from backend
 * @param {*} value - Current answer value
 * @param {Function} onUserInteraction - Event dispatcher function
 * @param {Object} labels - UI labels for rendering
 * @param {Object} allAnswers - All current answers (read-only for rendering)
 * @returns {JSX.Element} Pure rendered UI
 */
const PureAnswerInput = ({ 
  question, 
  value, 
  onUserInteraction, 
  labels = {}, 
  allAnswers = {} 
}) => {
  // Pure rendering functions - no business logic

  /**
   * Dispatch user interaction event to Server-Driven UI
   */
  const dispatchEvent = (eventType, eventData) => {
    if (onUserInteraction) {
      onUserInteraction(eventType, {
        questionId: question.id,
        ...eventData
      });
    }
  };

  /**
   * Handle value changes - pure event dispatch
   */
  const handleChange = (newValue, immediate = false) => {
    dispatchEvent('answer_change', {
      value: newValue,
      immediate,
      timestamp: Date.now()
    });
  };

  /**
   * Handle blur events - pure event dispatch
   */
  const handleBlur = (targetId = question.id) => {
    dispatchEvent('answer_blur', {
      targetId,
      currentValue: value,
      timestamp: Date.now()
    });
  };

  /**
   * Render follow-up questions based on current value
   * Pure rendering - no state management
   */
  const renderFollowUps = () => {
    if (!question.follow_ups) return null;

    return question.follow_ups.map((followUp, index) => {
      const mainAnswer = value;
      const condition = Array.isArray(mainAnswer)
        ? mainAnswer.some(a => followUp.when.in.includes(a))
        : followUp.when.in.includes(mainAnswer);

      if (!condition) return null;

      const followUpQuestion = followUp.ask;
      const followUpValue = allAnswers[followUpQuestion.id] || '';

      return (
        <div key={index} style={{ marginTop: '15px', paddingTop: '15px', borderTop: '1px solid #eee' }}>
          <textarea
            rows={3}
            value={followUpValue}
            onChange={(e) => {
              dispatchEvent('answer_change', {
                questionId: followUpQuestion.id,
                value: e.target.value,
                immediate: false
              });
            }}
            onBlur={() => {
              dispatchEvent('answer_blur', {
                questionId: followUpQuestion.id,
                targetId: followUpQuestion.id,
                currentValue: followUpValue
              });
            }}
            placeholder={followUpQuestion.placeholder}
            maxLength={followUpQuestion.max_chars}
            style={{ 
              width: '100%', 
              padding: 8, 
              borderRadius: 4, 
              border: '1px solid #ddd' 
            }}
          />
        </div>
      );
    });
  };

  /**
   * Render main input based on question type
   * Pure rendering function
   */
  const renderMainInput = () => {
    const { question_type, ui } = question;
    const inputValue = value || '';

    switch (question_type) {
      case 'yes-no':
        return renderYesNoInput(inputValue);
      
      case 'choice-single':
        return ui === 'dropdown' 
          ? renderDropdownInput(inputValue)
          : renderRadioInput(inputValue);
      
      case 'choice-multi':
        return renderCheckboxInput(inputValue);
      
      case 'text':
        return ui === 'textarea' 
          ? renderTextAreaInput(inputValue)
          : renderTextInput(inputValue);
      
      default:
        return <div>Unsupported question type: {question_type}</div>;
    }
  };

  /**
   * Render Yes/No input
   */
  const renderYesNoInput = (inputValue) => {
    const yesLabel = labels?.yes || 'Yes';
    const noLabel = labels?.no || 'No';

    return (
      <div>
        <label style={{ marginRight: 16 }}>
          <input
            type="radio"
            name={question.id}
            value="yes"
            checked={inputValue === 'yes'}
            onChange={() => handleChange('yes', true)}
          />{' '}
          {yesLabel}
        </label>
        <label>
          <input
            type="radio"
            name={question.id}
            value="no"
            checked={inputValue === 'no'}
            onChange={() => handleChange('no', true)}
          />{' '}
          {noLabel}
        </label>
      </div>
    );
  };

  /**
   * Render dropdown single choice input
   */
  const renderDropdownInput = (inputValue) => {
    const customInputId = question.custom_text_input?.id;
    const customValue = customInputId ? allAnswers[customInputId] || '' : '';
    const isDropdownDisabled = customInputId && customValue !== '';

    return (
      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
        <select
          value={isDropdownDisabled ? '' : inputValue}
          onChange={(e) => handleChange(e.target.value, true)}
          onBlur={() => handleBlur()}
          style={{ 
            flex: 1, 
            padding: 8, 
            borderRadius: 4, 
            border: '1px solid #ddd' 
          }}
          disabled={isDropdownDisabled}
        >
          <option value="">Select an option</option>
          {question.options?.map((option) => (
            <option key={option.code} value={option.code}>
              {option.label}
            </option>
          ))}
        </select>
        {customInputId && (
          <input
            type="text"
            value={customValue}
            onChange={(e) => {
              dispatchEvent('answer_change', {
                questionId: customInputId,
                value: e.target.value,
                immediate: false
              });
            }}
            onBlur={() => handleBlur(question.id)}
            placeholder={question.custom_text_input.placeholder}
            style={{ 
              flex: 1, 
              padding: 8, 
              borderRadius: 4, 
              border: '1px solid #ddd' 
            }}
          />
        )}
      </div>
    );
  };

  /**
   * Render radio single choice input
   */
  const renderRadioInput = (inputValue) => {
    return (
      <div>
        {question.options?.map((option) => (
          <label key={option.code} style={{ display: 'block', marginBottom: 8 }}>
            <input
              type="radio"
              name={question.id}
              value={option.code}
              checked={inputValue === option.code}
              onChange={() => handleChange(option.code, true)}
            />{' '}
            {option.label}
          </label>
        ))}
      </div>
    );
  };

  /**
   * Render checkbox multi-choice input
   */
  const renderCheckboxInput = (inputValue) => {
    const selectedOptions = Array.isArray(inputValue) ? inputValue : [];
    
    const handleMultiChange = (optionCode) => {
      const newSelected = selectedOptions.includes(optionCode)
        ? selectedOptions.filter(item => item !== optionCode)
        : [...selectedOptions, optionCode];
      
      handleChange(newSelected, true);
    };

    // Handle "other" text field rendering
    const hasFollowUps = question.follow_ups && question.follow_ups.length > 0;
    const otherTextId = question.other_text_id;
    const otherTextValue = otherTextId ? allAnswers[otherTextId] || '' : '';
    const isOtherSelected = selectedOptions.includes('other');

    return (
      <div>
        {question.options?.map((option) => (
          <label key={option.code} style={{ display: 'block', marginBottom: 8 }}>
            <input
              type="checkbox"
              checked={selectedOptions.includes(option.code)}
              onChange={() => handleMultiChange(option.code)}
            />{' '}
            {option.label}
          </label>
        ))}
        
        {/* Render "Other" text field if applicable */}
        {question.with_other && !hasFollowUps && otherTextId && isOtherSelected && (
          <div style={{ marginTop: '10px', marginLeft: '20px' }}>
            <textarea
              rows={3}
              value={otherTextValue}
              onChange={(e) => {
                dispatchEvent('answer_change', {
                  questionId: otherTextId,
                  value: e.target.value,
                  immediate: false
                });
              }}
              onBlur={() => {
                dispatchEvent('answer_blur', {
                  questionId: otherTextId,
                  targetId: otherTextId,
                  currentValue: otherTextValue
                });
              }}
              placeholder="Please specify..."
              style={{
                width: '100%',
                padding: 8,
                borderRadius: 4,
                border: '1px solid #ddd',
                resize: 'vertical'
              }}
            />
          </div>
        )}
      </div>
    );
  };

  /**
   * Render text area input
   */
  const renderTextAreaInput = (inputValue) => {
    return (
      <textarea
        rows={3}
        value={inputValue}
        onChange={(e) => handleChange(e.target.value, false)}
        onBlur={() => handleBlur()}
        placeholder={question.placeholder}
        maxLength={question.max_chars}
        style={{ 
          width: '100%', 
          padding: 8, 
          borderRadius: 4, 
          border: '1px solid #ddd' 
        }}
      />
    );
  };

  /**
   * Render text input
   */
  const renderTextInput = (inputValue) => {
    return (
      <input
        type="text"
        value={inputValue}
        onChange={(e) => handleChange(e.target.value, false)}
        onBlur={() => handleBlur()}
        placeholder={question.placeholder}
        maxLength={question.max_chars}
        style={{ 
          width: '100%', 
          padding: 8, 
          borderRadius: 4, 
          border: '1px solid #ddd' 
        }}
      />
    );
  };

  // Pure render - no side effects, no business logic
  return (
    <div>
      {renderMainInput()}
      {renderFollowUps()}
    </div>
  );
};

/**
 * Higher-Order Component for Server-Driven UI integration
 * Connects pure component to Server-Driven UI event system
 */
export const withServerDrivenEvents = (PureComponent) => {
  return function ServerDrivenAnswerInput({ 
    question, 
    value, 
    labels, 
    allAnswers, 
    dispatchUserEvent 
  }) {
    // Event handler that dispatches to Server-Driven UI system
    const handleUserInteraction = (eventType, eventData) => {
      if (dispatchUserEvent) {
        dispatchUserEvent(eventType, eventData);
      } else {
        console.warn('[PureAnswerInput] No event dispatcher provided');
      }
    };

    return (
      <PureComponent
        question={question}
        value={value}
        onUserInteraction={handleUserInteraction}
        labels={labels}
        allAnswers={allAnswers}
      />
    );
  };
};

// Export pure component and Server-Driven UI connected version
export { PureAnswerInput };
export default withServerDrivenEvents(PureAnswerInput);