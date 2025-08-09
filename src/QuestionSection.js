/**
 * @file This file defines the core QuestionSection component of the QnA Evaluator application.
 * @summary It handles the rendering of all questions (both meta and standard), manages user input,
 * orchestrates the AI evaluation process, and implements the complex logic for handling
 * question dependencies and cascading re-evaluations.
 * @version 1.1.0
 * @author Predictex AI
 */

import React, { useContext, useState, useEffect } from 'react';
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
 * @workflow {7} Manages cascading re-evaluation of dependent questions.
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
    setScores,
    questionStates,
    setQuestionStates
  } = context || {};

  const [loading, setLoading] = useState({});
  const [depWarnings, setDepWarnings] = useState({});

  /**
   * @brief Effect to run a comprehensive check on component mount.
   * @description This effect runs once after the initial render. It performs two key tasks:
   * 1.  It recalculates the state of every single question based on the latest loaded data
   *     to ensure consistency after a page reload or changes in logic.
   * 2.  It then triggers re-evaluation for any questions that are 'partially_answered'
   *     but now have all their dependencies met (i.e., are 'fully_answered').
   * This ensures the application state is always consistent and up-to-date on startup.
   */
  useEffect(() => {
    if (!sections || sections.length === 0 || contextLoading) {
      return;
    }

    const runStartupCheck = async () => {
      console.log('--- Running Startup Check ---');

      // Use an iterative approach to resolve dependencies layer by layer.
      // This is more robust than a single or two-pass check.
      let changedInPass = true;
      let passes = 0;
      const maxPasses = 5; // Sufficient for deep dependency chains.

      let currentStates = { ...questionStates };

      while (changedInPass && passes < maxPasses) {
        changedInPass = false;
        passes++;
        console.log(`\n[Startup Check] Pass ${passes}`);

        const nextStates = { ...currentStates };

        for (const section of sections) {
          for (const question of section.questions) {
            const oldState = currentStates[question.id] || 'unanswered';
            const newState = getQuestionState(question, answers, scores, currentStates);

            if (oldState !== newState) {
              console.log(`[Startup Check] State change for ${question.id}: ${oldState} -> ${newState}`);
              nextStates[question.id] = newState;
              changedInPass = true;
            }

            // Check if a partially answered question is now ready for re-evaluation.
            if (newState === 'partially_answered') {
              const dependencies = getQuestionDependencies(question);
              // Create a snapshot of the states for this specific check to avoid unsafe references in the loop.
              const statesSnapshot = { ...currentStates };
              const allDependenciesMet = dependencies.every(
                (depId) => statesSnapshot[depId] === 'fully_answered'
              );

              console.log(`[Startup Check] Checking ${question.id}: Dependencies met? ${allDependenciesMet}`, dependencies.map(d => ({ [d]: statesSnapshot[d] })));

              if (allDependenciesMet) {
                const si = sections.findIndex((s) => s.title === section.title);
                const qi = section.questions.findIndex((q) => q.id === question.id);
                if (si !== -1 && qi !== -1) {
                  // This question is ready, re-evaluate it.
                  // Note: This happens outside the state update loop to avoid side-effects within state calculation.
                  console.log(`[Startup Check] ---> RE-EVALUATING ${question.id}`);
                  evaluateAnswer(si, qi, true);
                }
              }
            }
          }
        }
        currentStates = nextStates;
      }

      // After all iterations, update the global state.
      console.log('--- Startup Check Finished ---');
      setQuestionStates(currentStates);
    };

    runStartupCheck();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contextLoading, sections]);

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
   * @brief Determines the current state of a question
   * 
   * Checks if a question is unanswered, partially answered, or fully answered
   * based on whether it has an answer and whether all its dependencies are fully answered.
   * 
   * @function getQuestionState
   * @param {Object} question - Question object
   * @returns {string} Question state: 'unanswered', 'partially_answered', or 'fully_answered'
   * 
   * @reads {answers} - Checks if question has an answer
   * @reads {scores} - Checks if question has been evaluated
   * @reads {questionStates} - Checks current state of dependencies
   * 
   * @role {State Determiner} - Determines current state of a question
   */
  const getQuestionState = (question, currentAnswers, currentScores, currentStates) => {
    const hasAnswer = currentAnswers[question.id] && currentAnswers[question.id] !== '';
    const hasScore = currentScores[question.id] !== undefined;
    const dependencies = getQuestionDependencies(question);
    
    if (!hasAnswer) {
      return 'unanswered';
    }
    
    if (dependencies.length === 0) {
      // No dependencies, so if it has a score, it's fully answered
      return hasScore ? 'fully_answered' : 'partially_answered';
    }
    
    // Check if all dependencies are fully answered
    const allDependenciesFullyAnswered = dependencies.every(depId => 
      currentStates[depId] === 'fully_answered'
    );
    
    if (allDependenciesFullyAnswered && hasScore) {
      return 'fully_answered';
    }
    
    return 'partially_answered';
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

  /**
   * @brief Finds all questions that depend on a given question
   * 
   * Searches through all sections to find questions that have the given question
   * in their ai_context.include_answers array.
   * 
   * @function findDependentQuestions
   * @param {string} questionId - Question ID to find dependents for
   * @returns {Array} Array of question objects that depend on the given question
   * 
   * @reads {sections} - Searches through all sections and questions
   * 
   * @role {Dependency Finder} - Finds questions that depend on a given question
   */
  const findDependentQuestions = (questionId) => {
    const dependents = [];
    sections.forEach(section => {
      section.questions.forEach(question => {
        const dependencies = getQuestionDependencies(question);
        if (dependencies.includes(questionId)) {
          dependents.push(question);
        }
      });
    });
    return dependents;
  };

  /**
   * @brief Recursively updates dependent questions when a question becomes fully answered
   * 
   * When a question becomes fully answered, this function finds all questions that depend on it
   * and checks if they should be re-evaluated. This creates a cascade of updates.
   * 
   * @function cascadeUpdateDependents
   * @param {string} questionId - Question ID that just became fully answered
   * 
   * @uses {findDependentQuestions} - Finds questions that depend on the given question
   * @uses {getQuestionState} - Determines current state of dependent questions
   * @uses {evaluateAnswer} - Re-evaluates questions that are ready
   * 
   * @role {Cascade Manager} - Manages cascade updates of dependent questions
   */
  const cascadeUpdateDependents = async (questionId) => {
    const dependents = findDependentQuestions(questionId);
    
    for (const dependent of dependents) {
      const currentState = getQuestionState(dependent, answers, scores, questionStates);
      
      if (currentState === 'partially_answered') {
        // Check if all dependencies are now fully answered
        const dependencies = getQuestionDependencies(dependent);
        const allDependenciesFullyAnswered = dependencies.every(depId => 
          questionStates[depId] === 'fully_answered'
        );
        
        if (allDependenciesFullyAnswered) {
          // Find the section and question indices for this dependent
          let foundSectionIndex = -1;
          let foundQuestionIndex = -1;
          
          sections.forEach((section, si) => {
            section.questions.forEach((q, qi) => {
              if (q.id === dependent.id) {
                foundSectionIndex = si;
                foundQuestionIndex = qi;
              }
            });
          });
          
          if (foundSectionIndex !== -1 && foundQuestionIndex !== -1) {
            // Re-evaluate this dependent question
            await evaluateAnswer(foundSectionIndex, foundQuestionIndex, true); // true = isReevaluation
          }
        }
      }
    }
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
   * @param {*} value - The new answer value.
   */
  const handleAnswerChange = (si, qi, value) => {
    const question = sections[si]?.questions[qi];
    if (!question) return;

    // The main answer is updated directly. Follow-up answers are handled by AnswerInput.
    const newAnswers = {
      ...answers,
      [question.id]: value,
    };
    setAnswers(newAnswers);

    // Clear dependency warning for this question when answer changes.
    if (depWarnings[question.id]) {
      setDepWarnings(prev => ({
        ...prev,
        [question.id]: undefined
      }));
    }

    // Update the question's state based on the latest answers.
    const newState = getQuestionState(question, newAnswers, scores, questionStates);
    updateQuestionState(question.id, newState);
  };

  /**
   * @brief Retrieves the location answer from meta questions.
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
    
    // Fallback to legacy format is removed as the structure is standardized.
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
  const evaluateAnswer = async (si, qi, isReevaluation = false) => {
    const question = sections[si]?.questions[qi];
    if (!question) return;

    const key = qKey(si, qi);
    setLoading(prev => ({ ...prev, [key]: true }));

    try {
      // Remove dependency warnings - we now allow evaluation without dependencies
      if (depWarnings[question.id]) {
        setDepWarnings(prev => ({
          ...prev,
          [question.id]: undefined
        }));
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
        const newScores = { ...scores, [question.id]: data.score };
        
        // Update scores and states
        setScores(newScores);

        // Update question state and trigger cascade updates
        const newState = getQuestionState(question, answers, newScores, questionStates);
        updateQuestionState(question.id, newState);
        
        // If this question just became fully answered, trigger cascade updates
        if (newState === 'fully_answered' && !isReevaluation) {
          await cascadeUpdateDependents(question.id);
        }

        // Apply calculations if any
        if (calculations && calculations.length > 0) {
          const calculatedScores = applyCalculations(newScores, calculations);
          setScores(calculatedScores);
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
      {/* Meta Questions Section is now rendered without its own title */}
      {metaQuestions && metaQuestions.length > 0 && (
        <MetaQuestionsSection />
      )}
      
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
                  setAnswers={setAnswers} // Pass setAnswers directly
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
                    <span style={{ 
                      marginLeft: 8, 
                      fontSize: '12px',
                      padding: '2px 6px',
                      borderRadius: '3px',
                      backgroundColor: questionStates[q.id] === 'fully_answered' ? '#27ae60' : '#f39c12',
                      color: 'white'
                    }}>
                      {questionStates[q.id] === 'fully_answered' ? '✓ Fully' : '⚠ Partly'}
                    </span>
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
 * @input {Array} calcArr - Calculation rules in format "TARGET=EXPRESSION"
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