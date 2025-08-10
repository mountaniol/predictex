import React from 'react';

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
const AnswerInput = ({ q, value, onChange, onBlur, labels, answers, setAnswers }) => {
  /**
   * @brief Renders follow-up questions based on current answer
   * 
   * Maps through follow-up questions and renders them if conditions
   * are met. Provides visual hierarchy with indentation and styling
   * to distinguish follow-ups from main questions.
   * 
   * @function renderFollowUps
   * @returns {JSX.Element|null} Rendered follow-up questions or null
   * 
   * @reads {q.follow_ups} - Array of follow-up question configurations
   * @reads {followUpAnswers} - Current follow-up answer values
   * @reads {value} - Main answer value for condition evaluation
   * 
   * @dependencies {shouldShowFollowUp} - Function to evaluate display conditions
   * @dependencies {renderInput} - Function to render individual input elements
   * @dependencies {handleFollowUpChange} - Function to handle follow-up changes
   * 
   * @role {Follow-up Renderer} - Renders conditional follow-up questions
   * @role {UI Organizer} - Organizes follow-up questions with visual hierarchy
   * @role {Condition Manager} - Manages display conditions for follow-ups
   */
  const renderFollowUps = () => {
    if (!q.follow_ups) return null;

    return q.follow_ups.map((followUp, index) => {
      const condition = followUp.when.in.includes(value);
      if (!condition) return null;

      const followUpQuestion = followUp.ask;
      const followUpValue = answers[followUpQuestion.id] || '';

      // This is a simplified renderer for the follow-up.
      // A more robust implementation would use a component similar to AnswerInput itself.
      if (followUpQuestion.ui === 'textarea') {
        return (
          <div key={index} style={{ marginTop: '10px' }}>
            <textarea
              rows={3}
              value={followUpValue}
              onChange={(e) => setAnswers(prev => ({ ...prev, [followUpQuestion.id]: e.target.value }))}
              placeholder={followUpQuestion.placeholder}
              maxLength={followUpQuestion.max_chars}
              style={{ width: '100%', padding: 8, borderRadius: 4, border: '1px solid #ddd' }}
            />
          </div>
        );
      }
      return null;
    });
  };

  /**
   * @brief Renders appropriate input element based on question type
   * 
   * Universal input renderer that creates appropriate UI elements based on
   * question type and UI configuration. Supports all question types with
   * proper styling and event handling.
   * 
   * @function renderInput
   * @param {Object} question - Question configuration object
   * @param {*} inputValue - Current input value
   * @param {Function} inputOnChange - Callback for input value changes
   * @returns {JSX.Element} Rendered input element
   * 
   * @input {Object} question - Question configuration with type and UI settings
   * @input {*} inputValue - Current value for the input element
   * @input {Function} inputOnChange - Callback function for value changes
   * 
   * @returns {JSX.Element} inputElement - Rendered input component
   * 
   * @types {yes-no} - Radio buttons for yes/no questions
   * @types {choice-single} - Radio buttons or dropdown for single choice
   * @types {choice-multi} - Checkboxes for multiple choice questions
   * @types {text} - Text input or textarea based on UI setting
   * @types {textarea} - Multi-line text input
   * @types {number} - Numeric input field
   * @types {default} - Fallback textarea for unknown types
   * 
   * @dependencies {labels} - UI labels for yes/no options
   * @dependencies {handleMultiChange} - Function for multi-choice handling
   * 
   * @role {Input Renderer} - Renders appropriate UI for question type
   * @role {Type Handler} - Handles different question types and UI variants
   * @role {Event Manager} - Manages input events and value changes
   * @role {UI Stylist} - Applies consistent styling to input elements
   */
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
                onChange={() => onChange('yes', true)}
              />{' '}
              {yesLabel}
            </label>
            <label>
              <input
                type="radio"
                name={q.id}
                value="no"
                checked={inputValue === 'no'}
                onChange={() => onChange('no', true)}
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

          const handleCustomChange = (e) => {
            const newCustomValue = e.target.value;
            setAnswers(prev => ({
              ...prev,
              [customInputId]: newCustomValue,
              // If user types in custom, clear the dropdown selection
              [q.id]: newCustomValue ? '' : prev[q.id]
            }));
          };

          return (
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <select
                value={isDropdownDisabled ? '' : inputValue}
                onChange={(e) => onChange(e.target.value, true)}
                onBlur={onBlur}
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
                  onChange={handleCustomChange}
                  onBlur={onBlur} // Assuming onBlur works for custom input too
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
                    onChange={() => onChange(option.code, true)}
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
            onChange(newSelected, true); // Always submit on change for multi-choice
        };
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
            </div>
        );

      case 'text':
        if (ui === 'textarea') {
          return (
            <textarea
              rows={3}
              value={inputValue}
              onChange={(e) => onChange(e.target.value, false)}
              onBlur={onBlur}
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
            onChange={(e) => onChange(e.target.value, false)}
            onBlur={onBlur}
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
