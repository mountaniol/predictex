import React, { useRef, useCallback } from 'react';

/**
 * @brief Universal input component for rendering different question types
 * 
 * Core input component that renders appropriate UI elements based on question type.
 * Supports multiple input types including yes/no, single choice, multi-choice,
 * text, textarea, and number inputs. Handles follow-up questions and "Other"
 * options with additional text fields.
 * 
 * @function AnswerInput
 * @param {Object} q - Question configuration object
 * @param {*} value - Current answer value
 * @param {Function} onChange - Callback function for value changes
 * @param {Object} labels - UI labels for yes/no options
 * @param {Object} answers - Global answers object for follow-up data
 * @returns {JSX.Element} Rendered input component with appropriate UI
 * 
 * @input {Object} q - Question configuration with type, options, and UI settings
 * @input {*} value - Current answer value (string, array, or object)
 * @input {Function} onChange - Callback to notify parent of value changes
 * @input {Object} labels - UI labels (yes, no) for internationalization
 * @input {Object} answers - Global answers for follow-up data access
 * 
 * @state {Object} followUpAnswers - Local state for follow-up question answers
 * 
 * @dependencies {useState} - React hook for local state management
 * @dependencies {useEffect} - React hook for side effects and initialization
 * 
 * @architecture {Component Hierarchy} - Universal input component
 * @architecture {State Management} - Local state with parent communication
 * @architecture {UI Rendering} - Dynamic UI based on question type
 * @architecture {Event Handling} - Manages user interactions and value changes
 * 
 * @role {Input Renderer} - Renders appropriate UI for different question types
 * @role {State Manager} - Manages local follow-up answer state
 * @role {Event Handler} - Processes user interactions and value changes
 * @role {Follow-up Manager} - Handles conditional follow-up questions
 * 
 * @workflow {1} Initializes follow-up answers from existing data
 * @workflow {2} Renders main input based on question type
 * @workflow {3} Renders follow-up questions if conditions are met
 * @workflow {4} Handles value changes and notifies parent component
 */
const AnswerInput = ({ q, value, onChange, onBlur, labels, answers }) => {
  const debounceTimerRef = useRef(null);

  // Debounced onBlur for "Other" text fields to prevent excessive API calls
  const debouncedOnBlur = useCallback((id) => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = setTimeout(() => {
      onBlur(id);
    }, 500); // Wait 500ms after user stops typing
  }, [onBlur]);

  const handleFollowUpChange = (e, followUpQuestion) => {
    onChange(followUpQuestion.id, e.target.value, false);
  };

  const renderFollowUps = () => {
    if (!q.follow_ups) return null;

    return q.follow_ups.map((followUp, index) => {
      const mainAnswer = value;
      const condition = Array.isArray(mainAnswer)
        ? mainAnswer.some(a => followUp.when.in.includes(a))
        : followUp.when.in.includes(mainAnswer);

      if (!condition) return null;

      const followUpQuestion = followUp.ask;
      const followUpValue = answers[followUpQuestion.id] || '';

      return (
        <div key={index} style={{ marginTop: '15px', paddingTop: '15px', borderTop: '1px solid #eee' }}>
          <textarea
            rows={3}
            value={followUpValue}
            onChange={(e) => handleFollowUpChange(e, followUpQuestion)}
            onBlur={() => onBlur(followUpQuestion.id)}
            placeholder={followUpQuestion.placeholder}
            maxLength={followUpQuestion.max_chars}
            style={{ width: '100%', padding: 8, borderRadius: 4, border: '1px solid #ddd' }}
          />
        </div>
      );
    });
  };

  const renderInput = () => {
    const { question_type, ui } = q;
    const inputValue = value || '';

    switch (question_type) {
      case 'yes-no':
        const yesLabel = labels?.yes || 'Yes';
        const noLabel = labels?.no || 'No';
        return (
          <div>
            <label style={{ marginRight: 16 }}>
              <input
                type="radio"
                name={q.id}
                value="yes"
                checked={inputValue === 'yes'}
                onChange={() => onChange(q.id, 'yes', true)}
              />{' '}
              {yesLabel}
            </label>
            <label>
              <input
                type="radio"
                name={q.id}
                value="no"
                checked={inputValue === 'no'}
                onChange={() => onChange(q.id, 'no', true)}
              />{' '}
              {noLabel}
            </label>
          </div>
        );

      case 'choice-single':
        if (ui === 'dropdown') {
          const customInputId = q.custom_text_input?.id;
          const customValue = customInputId ? answers[customInputId] || '' : '';
          const isDropdownDisabled = customInputId && customValue !== '';

          return (
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <select
                value={isDropdownDisabled ? '' : inputValue}
                onChange={(e) => {
                  const selectedValue = e.target.value;
                  // Don't submit immediately if selecting "other" without text
                  let shouldSubmitNow = true;
                  if (q.with_other && q.other_text_id && selectedValue === 'other') {
                    const otherText = answers[q.other_text_id] || '';
                    if (otherText.trim() === '') {
                      shouldSubmitNow = false;
                    }
                  }
                  onChange(q.id, selectedValue, shouldSubmitNow);
                }}
                onBlur={() => onBlur(q.id)}
                style={{ flex: 1, padding: 8, borderRadius: 4, border: '1px solid #ddd' }}
                disabled={isDropdownDisabled}
              >
                <option value="">Select an option</option>
                {q.options?.map((option) => (
                  <option key={option.code} value={option.code}>
                    {option.label}
                  </option>
                ))}
              </select>
              {customInputId && (
                <input
                  type="text"
                  value={customValue}
                  onChange={(e) => onChange(customInputId, e.target.value, false)}
                  onBlur={() => onBlur(q.id)}
                  placeholder={q.custom_text_input.placeholder}
                  style={{ flex: 1, padding: 8, borderRadius: 4, border: '1px solid #ddd' }}
                />
              )}
            </div>
          );
        } else { // radio
          return (
            <div>
              {q.options?.map((option) => (
                <label key={option.code} style={{ display: 'block', marginBottom: 8 }}>
                  <input
                    type="radio"
                    name={q.id}
                    value={option.code}
                    checked={inputValue === option.code}
                    onChange={() => {
                      // Don't submit immediately if selecting "other" without text
                      let shouldSubmitNow = true;
                      if (q.with_other && q.other_text_id && option.code === 'other') {
                        const otherText = answers[q.other_text_id] || '';
                        if (otherText.trim() === '') {
                          shouldSubmitNow = false;
                        }
                      }
                      onChange(q.id, option.code, shouldSubmitNow);
                    }}
                  />{' '}
                  {option.label}
                </label>
              ))}
            </div>
          );
        }
      
      case 'choice-multi':
        const selectedOptions = Array.isArray(value) ? value : [];
        const handleMultiChange = (optionCode) => {
            const newSelected = selectedOptions.includes(optionCode)
                ? selectedOptions.filter(item => item !== optionCode)
                : [...selectedOptions, optionCode];
            
            // Don't submit immediately if selecting/deselecting "other" without text
            let shouldSubmitNow = true;
            if (q.with_other && q.other_text_id && optionCode === 'other') {
                const otherText = answers[q.other_text_id] || '';
                // If selecting "other" and text field is empty, don't submit
                if (!selectedOptions.includes('other') && otherText.trim() === '') {
                    shouldSubmitNow = false;
                }
                // If only "other" will be selected and no text, don't submit
                if (newSelected.length === 1 && newSelected[0] === 'other' && otherText.trim() === '') {
                    shouldSubmitNow = false;
                }
            }
            
            onChange(q.id, newSelected, shouldSubmitNow);
        };
        
        // Handle "other" text field for multi-choice questions
        // Priority: follow_ups over with_other to avoid duplication
        const hasFollowUps = q.follow_ups && q.follow_ups.length > 0;
        const otherTextId = q.other_text_id;
        const otherTextValue = otherTextId ? answers[otherTextId] || '' : '';
        const isOtherSelected = selectedOptions.includes('other');
        
        return (
            <div>
                {q.options?.map((option) => (
                    <label key={option.code} style={{ display: 'block', marginBottom: 8 }}>
                        <input
                            type="checkbox"
                            checked={selectedOptions.includes(option.code)}
                            onChange={() => handleMultiChange(option.code)}
                        />{' '}
                        {option.label}
                    </label>
                ))}
                
                {/* Render "Other" text field only if with_other is true, no follow_ups exist, and "other" is selected */}
                {q.with_other && !hasFollowUps && otherTextId && isOtherSelected && (
                    <div style={{ marginTop: '10px', marginLeft: '20px' }}>
                        <textarea
                            rows={3}
                            value={otherTextValue}
                            onChange={(e) => onChange(otherTextId, e.target.value, false)}
                            onBlur={() => debouncedOnBlur(otherTextId)}
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

      case 'text':
        if (ui === 'textarea') {
          return (
            <textarea
              rows={3}
              value={inputValue}
              onChange={(e) => onChange(q.id, e.target.value, false)}
              onBlur={() => onBlur(q.id)}
              placeholder={q.placeholder}
              maxLength={q.max_chars}
              style={{ width: '100%', padding: 8, borderRadius: 4, border: '1px solid #ddd' }}
            />
          );
        }
        return (
          <input
            type="text"
            value={inputValue}
            onChange={(e) => onChange(q.id, e.target.value, false)}
            onBlur={() => onBlur(q.id)}
            placeholder={q.placeholder}
            maxLength={q.max_chars}
            style={{ width: '100%', padding: 8, borderRadius: 4, border: '1px solid #ddd' }}
          />
        );
      
      default:
        return <div>Unsupported question type: {q.question_type}</div>;
    }
  };

  return (
    <div>
      {renderInput()}
      {renderFollowUps()}
    </div>
  );
};

export default AnswerInput;
