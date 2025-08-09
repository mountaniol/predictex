import React, { useContext } from 'react';
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
const MetaQuestionsSection = () => {
  const context = useContext(AppContext);
  const { metaQuestions, answers, setAnswers, labels, setQuestionStates } = context || {};

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
  /**
   * @brief Gets dependencies for a question
   * 
   * Extracts the list of question IDs that the current question depends on
   * from the ai_context.include_answers field.
   * 
   * @function getQuestionDependencies
   * @param {Object} question - Question object
   * @returns {Array} Array of question IDs that this question depends on
   * 
   * @reads {question.ai_context.include_answers} - List of dependent question IDs
   * 
   * @role {Dependency Extractor} - Extracts dependency information from questions
   */
  const getQuestionDependencies = (question) => {
    return question.ai_context?.include_answers || [];
  };

  /**
   * @brief Formats question title with dependencies
   * 
   * Creates a formatted title that shows dependencies in square brackets
   * before the question ID and text.
   * 
   * @function formatQuestionTitle
   * @param {Object} question - Question object
   * @returns {string} Formatted question title with dependencies
   * 
   * @uses {getQuestionDependencies} - Gets dependencies for the question
   * 
   * @role {Title Formatter} - Formats question titles with dependency information
   */
  const formatQuestionTitle = (question) => {
    const dependencies = getQuestionDependencies(question);
    if (dependencies.length > 0) {
      return `${question.id} [${dependencies.join(', ')}]: ${question.text}`;
    }
    return `${question.id}: ${question.text}`;
  };

  /**
   * @brief Updates the state of a question
   * 
   * Updates the questionStates state with the new state for the given question.
   * 
   * @function updateQuestionState
   * @param {string} questionId - Question ID
   * @param {string} state - New state: 'unanswered', 'partially_answered', or 'fully_answered'
   * 
   * @writes {questionStates} - Updates question state
   * 
   * @role {State Updater} - Updates question state
   */
  const updateQuestionState = (questionId, state) => {
    setQuestionStates(prev => ({
      ...prev,
      [questionId]: state
    }));
  };

  const handleAnswerChange = (questionId, value) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: value
    }));
    
    // Update question state after answer change
    const newState = value && value !== '' ? 'partially_answered' : 'unanswered';
    updateQuestionState(questionId, newState);
  };

  return (
    <div>
      {metaQuestions.map((question) => {
        if (question.question_type === 'internal') {
          return null; // Skip internal questions
        }

        return (
          <div
            key={question.id}
            style={{
              background: '#fff',
              padding: 24,
              marginBottom: 20,
              borderRadius: 12,
              border: '1px solid #e1e8ed'
            }}
          >
            <div style={{ marginBottom: 16 }}>
              <strong style={{ color: '#2c3e50' }}>{formatQuestionTitle(question)}</strong>
            </div>
            
            {question.hint && (
              <div style={{
                fontSize: '14px',
                color: '#7f8c8d',
                marginBottom: 12,
                fontStyle: 'italic'
              }}>
                💡 {question.hint}
              </div>
            )}
            
            {question.info && (
              <details style={{ marginBottom: 12 }}>
                <summary style={{
                  cursor: 'pointer',
                  color: '#3498db',
                  fontSize: '14px',
                  fontWeight: '500'
                }}>
                  Learn more
                </summary>
                <div style={{
                  marginTop: 8,
                  padding: 12,
                  background: '#f8f9fa',
                  borderRadius: 6,
                  fontSize: '14px',
                  color: '#2c3e50'
                }}>
                  {question.info}
                </div>
              </details>
            )}
            
            <AnswerInput
              q={question}
              value={answers[question.id] || ''}
              onChange={(value) => handleAnswerChange(question.id, value)}
              labels={labels}
              answers={answers}
            />
          </div>
        );
      })}
    </div>
  );
};

export default MetaQuestionsSection;
