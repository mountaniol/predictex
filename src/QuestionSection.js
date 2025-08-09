import React, { useContext, useState } from 'react';
import { AppContext } from './App';
import AnswerInput from './AnswerInput';
import MetaQuestionsSection from './MetaQuestionsSection';

/**
 * @brief Main questions rendering and evaluation component
 * 
 * Core component that renders all questions, handles user interactions,
 * manages answer state, and orchestrates AI evaluation. Integrates with
 * AppContext for global state management and provides the main user interface
 * for the QnA evaluation process.
 * 
 * @function QuestionSection
 * @returns {JSX.Element} Complete questions interface with evaluation capabilities
 * 
 * @context {AppContext} - Global application state and functions
 * @context {Array} sections - Questions grouped by cluster/section
 * @context {Array} metaQuestions - Meta questions for basic information
 * @context {string} aiPrompt - System prompt for AI evaluation
 * @context {string} apiKey - API endpoint URL for evaluation
 * @context {Object} labels - UI labels for yes/no options
 * @context {boolean} loading - Loading state for questions
 * @context {string} error - Error message if loading fails
 * @context {Array} calculations - Calculation rules for derived scores
 * @context {Object} answers - User answers to questions
 * @context {Function} setAnswers - Function to update answers
 * @context {Object} scores - AI evaluation scores
 * @context {Function} setScores - Function to update scores
 * 
 * @state {Object} loading - Loading states for individual question evaluations
 * @state {Object} depWarnings - Dependency warnings for unanswered questions
 * 
 * @dependencies {AppContext} - Global state management
 * @dependencies {AnswerInput} - Universal input component for questions
 * @dependencies {MetaQuestionsSection} - Component for basic information questions
 * 
 * @architecture {Component Hierarchy} - Main questions rendering component
 * @architecture {State Management} - Uses AppContext for global state
 * @architecture {Event Handling} - Manages user interactions and API calls
 * @architecture {Error Handling} - Provides dependency warnings and error states
 * 
 * @role {Question Renderer} - Renders all questions with appropriate UI
 * @role {State Manager} - Manages local loading and warning states
 * @role {Evaluation Orchestrator} - Coordinates AI evaluation process
 * @role {User Interface} - Provides main interaction interface
 * 
 * @workflow {1} Renders meta questions section
 * @workflow {2} Renders regular questions grouped by sections
 * @workflow {3} Handles user answer changes
 * @workflow {4} Validates dependencies before evaluation
 * @workflow {5} Calls AI evaluation API
 * @workflow {6} Updates scores and applies calculations
 */
const QuestionSection = () => {
  const context = useContext(AppContext);
  const { 
    sections, 
    metaQuestions,
    aiPrompt, 
    apiKey, 
    labels, 
    loading: contextLoading, 
    error: contextError, 
    calculations,
    answers,
    setAnswers,
    scores,
    setScores
  } = context || {};

  const [loading, setLoading] = useState({});
  const [depWarnings, setDepWarnings] = useState({});

  /**
   * @brief Generates unique key for question identification
   * 
   * Creates a unique identifier for each question based on section and question indices.
   * Used for managing loading states and other question-specific operations.
   * 
   * @function qKey
   * @param {number} si - Section index
   * @param {number} qi - Question index within section
   * @returns {string} Unique question key in format "si-qi"
   * 
   * @role {Key Generator} - Creates unique identifiers for questions
   */
  const qKey = (si, qi) => `${si}-${qi}`;

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
   * @brief Handles user answer changes and follow-up data
   * 
   * Processes answer changes from AnswerInput components, including both regular
   * answers and follow-up data from "Other" options. Updates global answers state
   * and clears dependency warnings when answers change.
   * 
   * @function handleAnswerChange
   * @param {number} si - Section index
   * @param {number} qi - Question index within section
   * @param {*} value - New answer value or follow-up data object
   * 
   * @input {*} value - Can be regular answer value or object with followUpData
   * @input {Object} value.followUpData - Follow-up data for "Other" options
   * @input {*} value.mainValue - Main answer value when follow-up data is present
   * 
   * @writes {AppContext.answers} - Updates global answers state
   * @writes {depWarnings} - Clears dependency warnings for changed questions
   * 
   * @dependencies {setAnswers} - Function to update global answers state
   * @dependencies {setDepWarnings} - Function to update dependency warnings
   * 
   * @role {Answer Processor} - Processes and validates user answers
   * @role {State Updater} - Updates global and local state
   * @role {Warning Manager} - Manages dependency warnings
   */
  const handleAnswerChange = (si, qi, value) => {
    const question = sections[si]?.questions[qi];
    if (!question) return;

    // Handle follow-up data
    if (value && typeof value === 'object' && value.followUpData) {
      // This is follow-up data, update both main answer and follow-up
      setAnswers(prev => {
        const newAnswers = {
          ...prev,
          [question.id]: value.mainValue,
          ...value.followUpData
        };
        return newAnswers;
      });
    } else {
      // Regular answer change
      setAnswers(prev => {
        const newAnswers = {
          ...prev,
          [question.id]: value
        };
        return newAnswers;
      });
    }

    // Clear dependency warning for this question when answer changes
    if (depWarnings[question.id]) {
      setDepWarnings(prev => ({
        ...prev,
        [question.id]: undefined
      }));
    }
  };

  /**
   * @brief Retrieves location answer from meta questions or legacy format
   * 
   * Extracts location information from either the new meta questions format
   * (MET.LOC) or the legacy format (LOCATION question). Used to provide
   * location context for AI evaluation.
   * 
   * @function getLocationAnswer
   * @returns {string} Location answer or empty string if not found
   * 
   * @reads {metaQuestions} - Checks for MET.LOC meta question
   * @reads {sections} - Checks for legacy LOCATION question
   * @reads {answers} - Retrieves location answer value
   * 
   * @format {New Format} - Looks for MET.LOC in metaQuestions
   * @format {Legacy Format} - Looks for LOCATION in sections
   * 
   * @role {Location Extractor} - Extracts location information from answers
   * @role {Format Handler} - Handles both new and legacy question formats
   * @role {Context Provider} - Provides location context for AI evaluation
   */
  const getLocationAnswer = () => {
    // For new format, look for MET.LOC in meta questions
    if (metaQuestions && metaQuestions.length > 0) {
      const locationQuestion = metaQuestions.find(q => q.id === 'MET.LOC');
      if (locationQuestion) {
        return answers[locationQuestion.id] || '';
      }
    }
    
    // Fallback to legacy format
    const locationSection = sections.find(s => s.title === 'Location Information');
    if (locationSection) {
      const locationQuestion = locationSection.questions.find(q => q.id === 'LOCATION');
      if (locationQuestion) {
        return answers[locationQuestion.id] || '';
      }
    }
    return '';
  };

  /**
   * @brief Evaluates a question answer using AI evaluation API
   * 
   * Main evaluation function that validates dependencies, builds evaluation payload,
   * calls the AI evaluation API, and updates scores. Handles error states and
   * applies calculation rules for derived scores.
   * 
   * @function evaluateAnswer
   * @param {number} si - Section index
   * @param {number} qi - Question index within section
   * @returns {Promise<void>} Async evaluation operation
   * 
   * @input {number} si - Section index for question identification
   * @input {number} qi - Question index for question identification
   * 
   * @reads {sections} - Retrieves question configuration
   * @reads {answers} - Retrieves current answer values
   * @reads {metaQuestions} - Retrieves meta question values
   * @reads {aiPrompt} - System prompt for AI evaluation
   * @reads {apiKey} - API endpoint URL
   * @reads {calculations} - Calculation rules for derived scores
   * 
   * @writes {loading} - Updates loading state for specific question
   * @writes {depWarnings} - Sets dependency warnings for missing answers
   * @writes {scores} - Updates AI evaluation scores
   * 
   * @environment {Network} - Makes HTTP POST request to evaluation API
   * @environment {OpenAI} - Uses OpenAI API for answer evaluation
   * 
   * @dependencies {fetch} - Browser API for HTTP requests
   * @dependencies {applyCalculations} - Function to apply calculation rules
   * @dependencies {setLoading} - Function to update loading states
   * @dependencies {setDepWarnings} - Function to update dependency warnings
   * @dependencies {setScores} - Function to update evaluation scores
   * 
   * @workflow {1} Validates dependencies and shows warnings if missing
   * @workflow {2} Builds evaluation payload with question, answer, and context
   * @workflow {3} Calls AI evaluation API with payload
   * @workflow {4} Parses AI response and extracts score
   * @workflow {5} Updates scores and applies calculation rules
   * @workflow {6} Handles errors and updates loading states
   * 
   * @role {Evaluation Orchestrator} - Coordinates the entire evaluation process
   * @role {Dependency Validator} - Ensures required answers are provided
   * @role {API Client} - Communicates with AI evaluation service
   * @role {Score Manager} - Updates and manages evaluation scores
   * @role {Error Handler} - Manages evaluation errors and user feedback
   */
  const evaluateAnswer = async (si, qi) => {
    const question = sections[si]?.questions[qi];
    if (!question) return;

    const key = qKey(si, qi);
    setLoading(prev => ({ ...prev, [key]: true }));

    try {
      // Check dependencies first
      if (question.ai_context?.include_answers && question.ai_context.include_answers.length > 0) {
        const missingDeps = question.ai_context.include_answers.filter(depId => 
          !answers[depId] || answers[depId] === ''
        );
        
        if (missingDeps.length > 0) {
          const depNames = missingDeps.map(id => id).join(', ');
          setDepWarnings(prev => ({
            ...prev,
            [question.id]: `Please answer questions: ${depNames} first.`
          }));
          setLoading(prev => ({ ...prev, [key]: false }));
          return;
        }
      }

      // Build the payload according to the new AI spec
      const payload = {
        system: aiPrompt,
        prompt_add: question.prompt_add || '',
        meta: {},
        question: {
          id: question.id,
          text: question.text
        },
        answer: {
          value: answers[question.id],
          extra: {},
          other_text: ''
        },
        answers_ctx: {}
      };

      // Add meta information
      if (question.ai_context?.include_meta) {
        question.ai_context.include_meta.forEach(metaId => {
          const metaQuestion = metaQuestions?.find(q => q.id === metaId);
          if (metaQuestion && answers[metaId]) {
            payload.meta[metaId] = answers[metaId];
          }
        });
      }

      // Add context answers
      if (question.ai_context?.include_answers) {
        question.ai_context.include_answers.forEach(answerId => {
          if (answers[answerId]) {
            payload.answers_ctx[answerId] = answers[answerId];
          }
        });
      }

      // Add location context
      const locationAnswer = getLocationAnswer();
      if (locationAnswer) {
        payload.meta['MET.LOC'] = locationAnswer;
      }

      const response = await fetch(apiKey, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.score !== undefined) {
        setScores(prev => ({
          ...prev,
          [question.id]: data.score
        }));

        // Clear dependency warning on successful evaluation
        if (depWarnings[question.id]) {
          setDepWarnings(prev => ({
            ...prev,
            [question.id]: undefined
          }));
        }

        // Apply calculations if any
        if (calculations && calculations.length > 0) {
          const newScores = applyCalculations(
            { ...scores, [question.id]: data.score },
            calculations
          );
          setScores(newScores);
        }
      }
    } catch (error) {
      console.error('Error evaluating answer:', error);
      alert('Error evaluating answer. Please try again.');
    } finally {
      setLoading(prev => ({ ...prev, [key]: false }));
    }
  };

  if (contextLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <div>Loading questions...</div>
      </div>
    );
  }

  if (contextError) {
    return (
      <div style={{ textAlign: 'center', padding: '40px', color: 'red' }}>
        <div>Error: {contextError}</div>
      </div>
    );
  }

  return (
    <div>
      {/* Meta Questions Section */}
      <MetaQuestionsSection />
      
      {/* Regular Questions Sections */}
      {sections.map((section, si) => (
        <div key={si} style={{ marginBottom: 32 }}>
          <h2 style={{
            fontSize: '24px',
            fontWeight: 'bold',
            marginBottom: '20px',
            color: '#2c3e50'
          }}>
            {section.title}
          </h2>
          
          {section.questions.map((q, qi) => {
            const key = qKey(si, qi);
            
            return (
              <div
                key={key}
                style={{
                  background: '#fff',
                  padding: 24,
                  marginBottom: 28,
                  borderRadius: 12,
                }}
              >
                <div>
                  <strong>{formatQuestionTitle(q)}</strong>
                </div>
                
                {q.hint && (
                  <div style={{
                    fontSize: '14px',
                    color: '#7f8c8d',
                    marginTop: 8,
                    marginBottom: 8,
                    fontStyle: 'italic'
                  }}>
                    💡 {q.hint}
                  </div>
                )}
                
                {q.info && (
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
                      {q.info}
                    </div>
                  </details>
                )}
                
                {depWarnings[q.id] && (
                  <div style={{
                    color: 'crimson',
                    fontWeight: 'bold',
                    marginTop: 8,
                    marginBottom: 8,
                    fontSize: '14px',
                    padding: '8px 12px',
                    background: '#fff5f5',
                    border: '1px solid #fed7d7',
                    borderRadius: '4px'
                  }}>
                    ⚠️ {depWarnings[q.id]}
                  </div>
                )}
                
                <AnswerInput
                  q={q}
                  value={answers[q.id] || ''}
                  onChange={v => handleAnswerChange(si, qi, v)}
                  labels={labels}
                  answers={answers}
                />
                
                <button
                  disabled={loading[key] || !answers[q.id]}
                  onClick={() => evaluateAnswer(si, qi)}
                  style={{
                    marginTop: 16,
                    padding: '10px 20px',
                    backgroundColor: '#3498db',
                    color: 'white',
                    border: 'none',
                    borderRadius: 6,
                    cursor: loading[key] || !answers[q.id] ? 'not-allowed' : 'pointer',
                    opacity: loading[key] || !answers[q.id] ? 0.6 : 1
                  }}
                >
                  {loading[key]
                    ? 'Evaluating...'
                    : scores[q.id]
                    ? 'Re-evaluate'
                    : 'Submit'}
                </button>
                
                {scores[q.id] !== undefined && (
                  <span style={{ marginLeft: 16 }}>
                    Score: {scores[q.id]}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
};

/**
 * @brief Applies calculation rules to derive new scores from existing ones
 * 
 * Evaluates mathematical expressions defined in calculation rules to compute
 * derived scores based on existing question scores. Supports complex expressions
 * with multiple question references and mathematical operations.
 * 
 * @function applyCalculations
 * @param {Object} base - Base scores object with question IDs as keys
 * @param {Array} calcArr - Array of calculation rule strings
 * @returns {Object} Updated scores object with calculated values
 * 
 * @input {Object} base - Current scores with question IDs as keys
 * @input {Array} calcArr - Calculation rules in format "target=expression"
 * 
 * @returns {Object} res - Updated scores object with calculated values
 * 
 * @format {Calculation Rules} - Strings in format "TARGET=EXPRESSION"
 * @format {Question IDs} - Regex pattern matches A3, B10, etc.
 * @format {Expressions} - Mathematical expressions with question ID references
 * 
 * @dependencies {Function} - Uses JavaScript Function constructor for expression evaluation
 * @dependencies {Regex} - Uses regex to identify question ID references
 * 
 * @workflow {1} Parses calculation rules into target and expression parts
 * @workflow {2} Identifies referenced question IDs in expressions
 * @workflow {3} Validates that all referenced IDs exist in base scores
 * @workflow {4} Replaces question IDs with actual score values
 * @workflow {5} Evaluates mathematical expressions
 * @workflow {6} Updates result object with calculated values
 * 
 * @role {Score Calculator} - Computes derived scores from existing ones
 * @role {Expression Evaluator} - Safely evaluates mathematical expressions
 * @role {Validation Manager} - Ensures all referenced scores exist
 * @role {Error Handler} - Handles invalid expressions and missing references
 * 
 * @example
 * // Input calculation rule: "FINAL=(A3+B10)/2"
 * // Base scores: { A3: 80, B10: 90 }
 * // Result: { A3: 80, B10: 90, FINAL: 85 }
 */
const applyCalculations = (base, calcArr) => {
  const res = { ...base };
  const idRegex = /\b([A-Z][0-9]+)\b/g; // matches A3, B10 etc.

  console.log('[calc] applying calculations to base scores:', base);
  console.log('[calc] calculation rules:', calcArr);

  calcArr.forEach(line => {
    if (!line || typeof line !== 'string') return;

    console.debug('[calc] parsing:', line);

    const parts = line.split('=');
    if (parts.length !== 2) {
      console.warn('[calc] invalid expression (no "="):', line);
      return;
    }

    const target = parts[0].trim();
    let expr = parts[1].trim();

    // ------- collect referenced IDs --------------------------------------
    const referenced = [];
    expr.replace(idRegex, (_, id) => {
      referenced.push(id);
      return _;
    });

    console.log(`[calc] for ${target}, referenced IDs:`, referenced);

    // check that every referenced ID already exists in res
    const unknown = referenced.filter(id => res[id] === undefined);
    if (unknown.length) {
      console.warn('[calc] unknown question IDs', unknown, 'in', line, '- rule ignored');
      return; // skip applying this rule
    }

    // replace IDs with current numeric values
    expr = expr.replace(idRegex, (_, id) => `(res['${id}'])`);

    try {
      // eslint-disable-next-line no-new-func
      const val = Function('res', `return ${expr};`)(res);
      if (!Number.isFinite(val)) throw new Error('NaN result');
      res[target] = val;
      console.debug(`[calc] ${target} =>`, val);
    } catch (e) {
      console.error('[calc] evaluation error for', line, e);
    }
  });

  console.log('[calc] final result:', res);
  return res;
};

export default QuestionSection;