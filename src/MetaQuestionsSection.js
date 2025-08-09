import React, { useContext, useState } from 'react';
import { AppContext } from './App';
import AnswerInput from './AnswerInput';

/**
 * @brief Component for rendering meta questions (basic information)
 * 
 * Renders a dedicated section for meta questions that collect basic information
 * before the main evaluation questions. These questions are typically used for
 * context and demographic information. Filters out internal questions and
 * provides a consistent UI with the main questions.
 * 
 * @function MetaQuestionsSection
 * @returns {JSX.Element|null} Meta questions section or null if no meta questions
 * 
 * @context {AppContext} - Global application state and functions
 * @context {Array} metaQuestions - Array of meta question configurations
 * @context {Object} answers - Current user answers
 * @context {Function} setAnswers - Function to update answers
 * @context {Object} labels - UI labels for yes/no options
 * @context {Object} metaSummaries - State to store AI-generated summaries for meta questions
 * @context {Function} setMetaSummaries - Function to update metaSummaries
 * 
 * @dependencies {AppContext} - Global state management
 * @dependencies {AnswerInput} - Universal input component for questions
 * 
 * @architecture {Component Hierarchy} - Specialized section component
 * @architecture {State Management} - Uses AppContext for global state
 * @architecture {UI Rendering} - Consistent styling with main questions
 * @architecture {Question Filtering} - Filters out internal questions
 * 
 * @role {Meta Renderer} - Renders basic information questions
 * @role {Question Filter} - Filters out internal/system questions
 * @role {UI Organizer} - Provides organized section for meta questions
 * @role {Context Provider} - Collects context information for evaluation
 * 
 * @workflow {1} Checks if meta questions exist
 * @workflow {2} Filters out internal questions
 * @workflow {3} Renders each meta question with AnswerInput
 * @workflow {4} Handles answer changes through global state
 * 
 * @section {Basic Information} - Section title for meta questions
 * @section {Question Rendering} - Individual question rendering with hints and info
 * @section {Answer Handling} - Global state management for answers
 */
const MetaQuestionsSection = ({ onMetaChange }) => {
  const { metaQuestions, answers, setAnswers, metaSummaries, setMetaSummaries } = useContext(AppContext);
  const [loadingSummary, setLoadingSummary] = useState({});

  console.log('[MetaQuestionsSection] Rendering. Received props:', {
    metaQuestionsCount: metaQuestions?.length,
    answersCount: Object.keys(answers || {}).length,
  });

  if (!metaQuestions || metaQuestions.length === 0) {
    return null;
  }

  /**
   * @brief Handles meta question answer changes
   * 
   * Updates the global answers state when a meta question answer changes.
   * Uses the same pattern as main questions for consistency in state management.
   * 
   * @function handleAnswerChange
   * @param {string} questionId - Unique identifier for the meta question
   * @param {*} value - New answer value for the question
   * 
   * @input {string} questionId - Unique identifier for the meta question
   * @input {*} value - New answer value (string, array, or object)
   * 
   * @writes {AppContext.answers} - Updates global answers state
   * 
   * @dependencies {setAnswers} - Function to update global answers state
   * 
   * @role {State Updater} - Updates global answers state
   * @role {Event Handler} - Processes meta question answer changes
   * @role {Consistency Manager} - Maintains consistent state management
   */
  const handleAnswerChange = (questionId, value) => {
    setAnswers(prev => ({ ...prev, [questionId]: value }));
    // If user clears the input, also clear the summary
    if (!value) {
      setMetaSummaries(prev => {
        const newSummaries = { ...prev };
        delete newSummaries[questionId];
        return newSummaries;
      });
    }
  };

  /**
   * @brief Handles blur event for meta questions
   * 
   * Triggers the AI validation endpoint when the user blurs the input.
   * Updates the global metaSummaries state with the AI-generated summary.
   * 
   * @function handleBlur
   * @param {Object} question - Question object
   * 
   * @input {Object} question - Question object
   * 
   * @writes {AppContext.metaSummaries} - Updates global summaries state
   * 
   * @dependencies {setMetaSummaries} - Function to update global summaries state
   * 
   * @role {State Updater} - Updates global summaries state
   * @role {Event Handler} - Processes blur event for AI validation
   * @role {Consistency Manager} - Maintains consistent state management
   */
  const handleBlur = async (question) => {
    const answer = answers[question.id];
    if (!question.ai_validate_prompt || !answer) {
      return;
    }

    setLoadingSummary(prev => ({ ...prev, [question.id]: true }));

    try {
      const payload = {
        validation_prompt: question.ai_validate_prompt,
        answer: answer,
      };

      const response = await fetch('/api/simple-validate.mjs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      if (data.summary) {
        setMetaSummaries(prev => ({ ...prev, [question.id]: data.summary }));
      }

      // After successful validation and summary, trigger re-evaluation of dependent questions
      if (onMetaChange) {
        onMetaChange(question.id);
      }

    } catch (error) {
      console.error('Error fetching AI validation:', error);
      // Optionally, set an error message in the state to show the user
    } finally {
      setLoadingSummary(prev => ({ ...prev, [question.id]: false }));
    }
  };

  return (
    <div style={{ marginBottom: 32 }}>
      {metaQuestions.filter(q => q.question_type !== 'internal').map((q) => (
        <div
          key={q.id}
          style={{
            background: '#fff',
            padding: 24,
            marginBottom: 28,
            borderRadius: 12,
          }}
        >
          <div>
            <strong>{q.text}</strong>
          </div>
          {q.hint && (
            <div style={{ fontSize: '14px', color: '#7f8c8d', marginTop: 8, marginBottom: 8, fontStyle: 'italic' }}>
              💡 {q.hint}
            </div>
          )}
          <AnswerInput
            q={q}
            value={answers[q.id] || ''}
            onChange={(value) => handleAnswerChange(q.id, value)}
            onBlur={() => handleBlur(q)}
            answers={answers}
            setAnswers={setAnswers}
          />
          {loadingSummary[q.id] && (
            <div style={{ marginTop: '12px', fontSize: '14px', color: '#7f8c8d' }}>
              Getting feedback...
            </div>
          )}
          {metaSummaries[q.id] && (
            <div style={{
              marginTop: '12px',
              padding: '12px',
              backgroundColor: '#f8f9fa',
              borderLeft: '3px solid #3498db',
              fontSize: '14px',
              color: '#2c3e50',
              lineHeight: '1.6'
            }}>
              {metaSummaries[q.id]}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export default MetaQuestionsSection;
