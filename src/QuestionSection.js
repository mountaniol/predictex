/**
 * @file This file defines the core QuestionSection component of the QnA Evaluator application.
 * @summary It handles the rendering of all questions (both meta and standard), manages user input,
 * orchestrates the AI evaluation process, and implements the complex logic for handling
 * question dependencies and cascading re-evaluations.
 * @version 1.1.0
 * @author Predictex AI
 */

import React, { useContext, useState, useEffect, useCallback, useRef } from 'react';
import { AppContext } from './App';
import AnswerInput from './AnswerInput';
import { useAtomicState } from './stateManager';
import { validateQuestionAnswer, shouldTriggerAIEvaluation, isAnswerEmpty } from './validationUtils';
import { createEvaluationProgressManager } from './evaluationProgressManager';
import { createManagedRef } from './memoryManager';
import { createDependencyInvalidator, createInvalidationHandler } from './dependencyInvalidator';

const getQuestionDependencies = (question) => {
  return question.ai_context?.include_answers || [];
};

const applyCalculations = (base, calcArr) => {
  const res = { ...base };
  const idRegex = /\b([A-Z]+[0-9]+[A-Z]?)\b/g;

  calcArr.forEach(line => {
    if (!line || typeof line !== 'string') return;
    const parts = line.split('=');
    if (parts.length !== 2) return;
    const target = parts[0].trim();
    let expr = parts[1].trim();
    const referenced = [];
    expr.replace(idRegex, (_, id) => {
      referenced.push(id);
      return _;
    });
    const unknown = referenced.filter(id => res[id] === undefined);
    if (unknown.length) return;
    expr = expr.replace(idRegex, (_, id) => `(res['${id}'])`);
    try {
      // eslint-disable-next-line no-new-func
      const val = Function('res', `return ${expr};`)(res);
      if (Number.isFinite(val)) {
        res[target] = val;
      }
    } catch (e) {
      console.error('[calc] evaluation error for', line, e);
    }
  });
  return res;
};

const QuestionSection = () => {
  const context = useContext(AppContext);
  const { 
    sections, calculations,
    answers, setAnswers, scores, setScores, questionStates, setQuestionStates,
    explanations, setExplanations, loading: contextLoading, labels,
    highlightUnanswered, setHighlightUnanswered, appConfig
  } = context || {};

  const [expandedExplanations, setExpandedExplanations] = useState({});
  const [submissionTrigger, setSubmissionTrigger] = useState(null);
  const startupCheckHasRun = useRef(false);
  const [evaluating, setEvaluating] = useState({});
  
  // Use managed ref for last evaluated answers to prevent memory accumulation
  const lastEvaluatedAnswers = useRef(createManagedRef({
    maxEntries: 500, // Reasonable limit for question answers
    ttlMs: 2 * 60 * 60 * 1000, // 2 hours TTL for answer tracking
    onCleanup: (removedCount) => console.log(`[QuestionSection] Cleaned up ${removedCount} old answer cache entries`)
  })).current;

  // Initialize atomic state manager for coordinated updates
  const atomicState = useAtomicState({
    scores: setScores,
    explanations: setExplanations,
    questionStates: setQuestionStates
  }, {
    scores: {},
    explanations: {},
    questionStates: {}
  });

  // Initialize evaluation progress manager
  const progressManager = useRef(createEvaluationProgressManager({
    timeoutMs: 30000, // 30 second timeout
    maxConcurrentEvaluations: 5,
    onTimeout: (questionId) => {
      console.warn(`[QuestionSection] Evaluation timeout for: ${questionId}`);
      setEvaluating(prev => {
        const newEvaluating = { ...prev };
        delete newEvaluating[questionId];
        return newEvaluating;
      });
    }
  })).current;

  // Initialize dependency invalidator
  const dependencyInvalidator = useRef(createDependencyInvalidator(sections, {
    maxInvalidationDepth: 5, // Prevent excessive cascading
    logInvalidations: true,
    onInvalidation: (questionIds) => {
      if (questionIds.length > 0) {
        console.log(`[QuestionSection] Dependency invalidation triggered for ${questionIds.length} questions:`, questionIds);
      }
    }
  })).current;

  // Create invalidation handler
  const handleInvalidation = useRef(createInvalidationHandler(
    dependencyInvalidator, 
    atomicState
  )).current;

  // --- START: UTILITY AND HELPER FUNCTIONS ---

  const getQuestionState = useCallback((question, currentAnswers, currentScores, currentStates) => {
    // Use centralized validation logic
    const validation = validateQuestionAnswer(question, currentAnswers);
    const hasAnswer = validation.hasValidAnswer;

    const hasScore = currentScores[question.id] !== undefined;
    const dependencies = getQuestionDependencies(question);
    
    if (!hasAnswer) return 'unanswered';
    
    // If score is set to "NO", ignore score requirement
    if (question.score === "NO") {
      return 'fully_answered';
    }
    
    if (dependencies.length === 0) {
      // For questions without dependencies, need both answer and score
      return hasScore ? 'fully_answered' : 'partially_answered';
    }
    
    const allDependenciesFullyAnswered = dependencies.every(depId => currentStates[depId] === 'fully_answered');
    if (allDependenciesFullyAnswered && hasScore) return 'fully_answered';
    
    return 'partially_answered';
  }, []);

  const computeAllStates = useCallback((currentScores, currentStates) => {
    const newStates = { ...currentStates };
    let statesChanged = true;
    let iterations = 0;
    const maxIterations = 5; // Prevent infinite loops in state computation
    
    // Iteratively compute states until they stabilize or max iterations reached
    while (statesChanged && iterations < maxIterations) {
      statesChanged = false;
      iterations++;
      
      for (const sec of sections) {
        for (const q of sec.questions) {
          const newState = getQuestionState(q, answers, currentScores, newStates);
          if (newStates[q.id] !== newState) {
            newStates[q.id] = newState;
            statesChanged = true;
          }
        }
      }
    }
    
    if (iterations >= maxIterations) {
      console.warn('[computeAllStates] State computation did not stabilize after', maxIterations, 'iterations');
    }
    
    return newStates;
  }, [sections, answers, getQuestionState, validateQuestionAnswer]);

  const evaluateAnswer = useCallback(async (question) => {
    if (!question) return null;

    setEvaluating(prev => ({ ...prev, [question.id]: true }));

    try {
      const payload = {
        questionId: question.id,
        allAnswers: answers,
      };

      console.log('--- Frontend Payload to Backend ---');
      console.log(JSON.stringify(payload, null, 2));
      console.log('---------------------------------');

      const baseUrl = appConfig?.Frontend?.api_base_url || '';
      const response = await fetch(`${baseUrl}/simple-evaluate.mjs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const result = (data.score !== undefined && data.explanation !== undefined) ? data : null;
      
      return result;

    } catch (error) {
      console.error('Error evaluating answer:', error);
      alert(`Error evaluating answer: ${error.message}`);
      return null;
    } finally {
      setEvaluating(prev => {
        const newEvaluating = { ...prev };
        delete newEvaluating[question.id];
        return newEvaluating;
      });
    }
  }, [answers, appConfig]);

  const findNextQuestionToReevaluate = useCallback((currentStates) => {
    if (!sections || !answers) return null;
    for (let i = 0; i < sections.length; i++) {
        for (let j = 0; j < sections[i].questions.length; j++) {
            const q = sections[i].questions[j];
            if (answers[q.id] && currentStates[q.id] !== 'fully_answered') {
                const dependencies = getQuestionDependencies(q);
                if (dependencies.every(depId => currentStates[depId] === 'fully_answered')) {
                    return { question: q, si: i, qi: j };
                }
            }
        }
    }
    return null;
  }, [sections, answers]);

  const handleSubmitAndResolveDependencies = useCallback(async (si, qi, questionsToReEvaluate = []) => {
    let initialQuestions = [];
    if (si !== null && qi !== null) {
      const question = sections[si]?.questions[qi];
      if(question) initialQuestions.push({question, si, qi});
    } else if (questionsToReEvaluate.length > 0) {
      questionsToReEvaluate.forEach(q => {
        for(let i = 0; i < sections.length; i++) {
          const q_idx = sections[i].questions.findIndex(sq => sq.id === q.id);
          if(q_idx !== -1) {
            initialQuestions.push({question: q, si: i, qi: q_idx});
            break;
          }
        }
      });
    }

    if(initialQuestions.length === 0) return;

    let currentScores = { ...scores };
    let currentExplanations = { ...explanations };
    
    // Evaluate initial questions
    for(const {question} of initialQuestions) {
      const result = await evaluateAnswer(question);
      if (result) {
        currentScores[question.id] = result.score;
        currentExplanations[question.id] = result.explanation;
      }
      // Complete progress tracking for this question
      progressManager.completeEvaluation(question.id, result ? 'success' : 'no-result');
    }

    let currentStates = computeAllStates(currentScores, questionStates);
    let reevaluatedInPass = true;
    let passes = 0;

    while (reevaluatedInPass && passes < 10) {
      passes++;
      reevaluatedInPass = false;
      const reevalInfo = findNextQuestionToReevaluate(currentStates);

      if (reevalInfo) {
        const { question: questionToReevaluate } = reevalInfo;
        
        // Start progress tracking for cascade evaluation
        if (progressManager.startEvaluation(questionToReevaluate.id)) {
          const result = await evaluateAnswer(questionToReevaluate);
          
          if (result) {
            currentScores[questionToReevaluate.id] = result.score;
            currentExplanations[questionToReevaluate.id] = result.explanation;
            currentStates = computeAllStates(currentScores, currentStates);
            reevaluatedInPass = true;
          }
          
          // Complete progress tracking
          progressManager.completeEvaluation(questionToReevaluate.id, result ? 'cascade-success' : 'cascade-no-result');
        } else {
          console.warn('[handleSubmitAndResolveDependencies] Could not start cascade evaluation for:', questionToReevaluate.id);
        }
      }
    }

    console.log('[Orchestrator] Loop finished. Committing final state atomically.');
        if (calculations && calculations.length > 0) {
      currentScores = applyCalculations(currentScores, calculations);
    }

    console.log('[Orchestrator] Final scores to commit:', currentScores);
    console.log('[Orchestrator] Final explanations to commit:', currentExplanations);
    console.log('[Orchestrator] Final states to commit:', currentStates);

    // Use atomic state manager to prevent intermediate renders with inconsistent state
    atomicState.updateEvaluationResults({
      scores: currentScores,
      explanations: currentExplanations,
      questionStates: currentStates
    });
    
    // Progress flags are automatically cleared by progressManager.completeEvaluation calls above
    // No manual cleanup needed here
  }, [calculations, computeAllStates, evaluateAnswer, explanations, findNextQuestionToReevaluate, questionStates, scores, sections, setExplanations, setQuestionStates, setScores, atomicState]);
  
  const handleAnswerChange = useCallback((id, value, submitNow = false) => {
    setHighlightUnanswered(false); // Reset highlight on any answer change

    let newAnswers = { ...answers, [id]: value };

    const question = sections.flatMap(s => s.questions).find(q =>
        q.id === id || q.custom_text_input?.id === id || q.other_text_id === id
    );

    if (question && question.custom_text_input) {
        const mainId = question.id;
        const customId = question.custom_text_input.id;
        if (id === mainId) {
            newAnswers[customId] = '';
        } else {
            newAnswers[mainId] = '';
        }
    }

    // Handle automatic clearing of "Other" text field when "other" option is unchecked
    if (question && question.other_text_id && id === question.id) {
        // This is a change to the main question (selection options)
        if (Array.isArray(value)) {
            // For multi-choice questions
            const isOtherSelected = value.includes('other');
            if (!isOtherSelected && newAnswers[question.other_text_id]) {
                // "Other" option was unchecked, clear the text field
                console.log(`[handleAnswerChange] "Other" option unchecked, clearing text field ${question.other_text_id}`);
                newAnswers[question.other_text_id] = '';
            }
        }
    }

    setAnswers(newAnswers);
    
    if (question) {
        // Use centralized validation logic
        const validation = validateQuestionAnswer(question, newAnswers);
        const hasAnswer = validation.hasValidAnswer;

        // If answer became empty, clear score and explanation atomically
        if (!hasAnswer) {
            console.log(`[handleAnswerChange] Answer became empty for question ${question.id}, clearing score and explanation`);
            atomicState.clearQuestionData(question.id);
        }

        // Trigger dependency invalidation for questions that depend on this one
        const invalidatedQuestions = handleInvalidation(question.id, 'answer-change');
        
        // Update question state
        const newState = getQuestionState(question, newAnswers, scores, questionStates);
        const stateUpdates = { [question.id]: newState };
        
        // Also update states for invalidated questions (they may now be partially answered)
        invalidatedQuestions.forEach(invalidatedId => {
          const invalidatedQuestion = sections.flatMap(s => s.questions).find(q => q.id === invalidatedId);
          if (invalidatedQuestion) {
            const invalidatedState = getQuestionState(invalidatedQuestion, newAnswers, scores, questionStates);
            stateUpdates[invalidatedId] = invalidatedState;
          }
        });
        
        setQuestionStates(prev => ({...prev, ...stateUpdates}));

        if (submitNow && question.score !== "NO" && hasAnswer) {
            setSubmissionTrigger({ question });
        }
    }
  }, [answers, getQuestionState, questionStates, scores, sections, setAnswers, setHighlightUnanswered, setQuestionStates, atomicState, validateQuestionAnswer, handleInvalidation]);

  const handleAnswerBlur = useCallback((id) => {
    // Find question by id, or by other_text_id if this is an "other" text field
    const question = sections.flatMap(s => s.questions).find(q => 
      q.id === id || q.other_text_id === id
    );
    if (!question) return;
    
    console.log('[handleAnswerBlur] Fired for:', question.id);
    
    // Check if evaluation is already in progress for this question
    if (progressManager.isInProgress(question.id)) {
      console.log('[handleAnswerBlur] Evaluation already in progress for:', question.id, '- skipping');
      return;
    }
    
    // Use centralized validation logic instead of duplicated code
    const hasValidAnswer = shouldTriggerAIEvaluation(question, answers);
    
    // Build a string representation of the current answer for comparison
    const currentAnswerString = JSON.stringify({
      main: answers[question.id],
      other: question.other_text_id ? answers[question.other_text_id] : null,
      custom: question.custom_text_input ? answers[question.custom_text_input.id] : null
    });
    
    // Check if the answer has changed since last evaluation
    if (lastEvaluatedAnswers.get(question.id) === currentAnswerString) {
      console.log('[handleAnswerBlur] Answer unchanged since last evaluation for:', question.id, '- skipping');
      return;
    }
    
    // Only trigger submission if question has a valid answer
    if (question.score !== "NO" && hasValidAnswer) {
      console.log('[handleAnswerBlur] Triggering submission for:', question.id);
      
      // Try to start evaluation with progress manager
      if (progressManager.startEvaluation(question.id)) {
        lastEvaluatedAnswers.set(question.id, currentAnswerString);
        setSubmissionTrigger({ question });
      } else {
        console.log('[handleAnswerBlur] Could not start evaluation (concurrent limit or already in progress):', question.id);
      }
    } else {
      console.log('[handleAnswerBlur] No valid answer, skipping submission for:', question.id);
    }
  }, [answers, sections, shouldTriggerAIEvaluation]);

  const runStartupCheck = useCallback(async () => {
    let currentScores = { ...scores };
    let currentStates = computeAllStates(currentScores, questionStates);

    let reevaluatedInPass = true;
    let passes = 0;
    const MAX_PASSES = 10;

    while (reevaluatedInPass && passes < MAX_PASSES) {
      passes++;
      reevaluatedInPass = false;
      const reevalInfo = findNextQuestionToReevaluate(currentStates);

      if (reevalInfo) {
        const { question: questionToReevaluate } = reevalInfo;
        
        // Use progress manager for startup check evaluations
        if (progressManager.startEvaluation(questionToReevaluate.id)) {
          const result = await evaluateAnswer(questionToReevaluate);
          
          if (result) {
            currentScores[questionToReevaluate.id] = result.score;
            currentStates = computeAllStates(currentScores, currentStates);
            reevaluatedInPass = true;
          }
          
          // Complete progress tracking
          progressManager.completeEvaluation(questionToReevaluate.id, result ? 'startup-success' : 'startup-no-result');
        } else {
          console.warn('[runStartupCheck] Could not start startup evaluation for:', questionToReevaluate.id);
        }
      }
    }

    if (passes >= MAX_PASSES) {
      console.warn('[runStartupCheck] Maximum passes reached! Possible dependency cycle detected.');
    }

    if (calculations && calculations.length > 0) {
      currentScores = applyCalculations(currentScores, calculations);
    }
    
    // Use atomic state manager for consistent startup state updates
    atomicState.updateAtomic({
      scores: currentScores,
      questionStates: currentStates
    });
  }, [calculations, computeAllStates, evaluateAnswer, findNextQuestionToReevaluate, questionStates, scores, setQuestionStates, setScores, atomicState]);

  const toggleExplanation = (questionId) => {
    setExpandedExplanations(prev => ({...prev, [questionId]: !prev[questionId]}));
  };

  // --- END: UTILITY AND HELPER FUNCTIONS ---


  // --- START: LIFECYCLE HOOKS (useEffect) ---

  useEffect(() => {
    if (submissionTrigger) {
      const { question } = submissionTrigger;
      // Find the question's section and question index
      let si, qi;
      for (let i = 0; i < sections.length; i++) {
        const j = sections[i].questions.findIndex(q => q.id === question.id);
        if (j !== -1) {
          si = i; qi = j; break;
        }
      }
      if (si !== undefined && qi !== undefined) {
        handleSubmitAndResolveDependencies(si, qi);
      }
      setSubmissionTrigger(null);
    }
  }, [submissionTrigger, sections, handleSubmitAndResolveDependencies]);

  useEffect(() => {
    if (!contextLoading && sections?.length > 0 && !startupCheckHasRun.current) {
      runStartupCheck();
      startupCheckHasRun.current = true;
    }
  }, [contextLoading, sections, runStartupCheck]);

  // Update dependency invalidator when sections change
  useEffect(() => {
    if (sections && sections.length > 0) {
      dependencyInvalidator.updateSections(sections);
      
      // Log dependency statistics for monitoring
      const stats = dependencyInvalidator.getStats();
      console.log('[QuestionSection] Dependency graph updated:', {
        questions: stats.totalQuestions,
        withDependents: stats.questionsWithDependents,
        totalDeps: stats.totalDependencies
      });
      
      // Validate dependency graph for potential issues
      const validation = dependencyInvalidator.validateGraph();
      if (!validation.isValid) {
        console.error('[QuestionSection] Dependency graph validation failed:', validation.issues);
      }
      if (validation.warnings.length > 0) {
        console.warn('[QuestionSection] Dependency graph warnings:', validation.warnings);
      }
    }
  }, [sections, dependencyInvalidator]);

  // Cleanup progress manager and memory refs on component unmount
  useEffect(() => {
    return () => {
      console.log('[QuestionSection] Component unmounting, clearing all evaluation progress flags and memory refs');
      progressManager.clearAll('component-unmount');
      lastEvaluatedAnswers.clear();
    };
  }, [progressManager, lastEvaluatedAnswers]);

  // Periodic memory cleanup and validation against current questions
  useEffect(() => {
    const interval = setInterval(() => {
      // Clean up old entries based on TTL
      lastEvaluatedAnswers.cleanup();
      
      // Validate against current question set and remove orphaned entries
      if (sections && sections.length > 0) {
        const currentQuestionIds = sections.flatMap(section => 
          section.questions.map(q => q.id)
        );
        lastEvaluatedAnswers.validateAgainstQuestions(currentQuestionIds);
      }
      
      // Log memory stats periodically for monitoring
      const stats = lastEvaluatedAnswers.getStats();
      if (stats.totalEntries > 100) { // Only log if significant usage
        console.log('[QuestionSection] Memory stats:', {
          entries: stats.totalEntries,
          utilization: Math.round(stats.utilizationPercent) + '%',
          avgAge: Math.round(stats.averageAge / 1000 / 60) + 'min'
        });
      }
    }, 5 * 60 * 1000); // Every 5 minutes

    return () => clearInterval(interval);
  }, [sections, lastEvaluatedAnswers]);

  // --- END: LIFECYCLE HOOKS ---

  
  if (contextLoading || !sections) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <div>Loading questions...</div>
      </div>
    );
  }

  return (
    <div>
      {sections.map((section, si) => (
        <div key={si} style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '20px', color: '#2c3e50' }}>
            {section.title}
          </h2>
          {section.questions.map((q, qi) => {
            if (q.question_type === 'internal') return null;
            
            const key = `q-${si}-${qi}`;
            const isUnanswered = questionStates[q.id] === 'unanswered';
            const shouldHighlight = isUnanswered && highlightUnanswered;

            const containerStyle = {
              background: '#fff',
              padding: '24px',
              marginBottom: '28px',
              borderRadius: '12px',
              border: shouldHighlight ? '2px solid #D32F2F' : '1px solid #e1e8ed',
              boxShadow: shouldHighlight ? '0 0 10px rgba(211, 47, 47, 0.2)' : 'none',
              transition: 'border-color 0.3s, box-shadow 0.3s'
            };
            
            return (
              <div
                key={key}
                style={containerStyle}
                className={isUnanswered ? 'question-unanswered' : ''}
              >
                <div style={{ marginBottom: '16px' }}>
                  <strong style={{ color: '#2c3e50' }}>{q.text}</strong>
                </div>
                {q.hint && <div style={{ fontSize: '14px', color: '#7f8c8d', marginTop: 8, marginBottom: 8, fontStyle: 'italic' }}>💡 {q.hint}</div>}
                <AnswerInput
                  q={q} value={answers[q.id] || ''}
                  onChange={handleAnswerChange}
                  onBlur={handleAnswerBlur}
                  labels={labels} answers={answers} setAnswers={setAnswers}
                  questionState={questionStates[q.id]}
                />
                <div style={{ display: 'flex', alignItems: 'center', marginTop: 16 }}>
                  {evaluating[q.id] ? (
                    <div 
                      style={{
                        padding: '4px 10px',
                        border: '1px solid transparent',
                        boxShadow: '0 0 0 1px #ccc',
                        borderRadius: '12px',
                    fontSize: '14px',
                        color: '#777'
                      }}
                    >
                      Thinking...
                    </div>
                  ) : scores[q.id] !== undefined && (
                    <div style={{ marginLeft: 0, display: 'flex', alignItems: 'center' }}>
                      <div 
                        style={{
                          padding: '4px 10px',
                          border: '1px solid transparent',
                          boxShadow: '0 0 0 1px black',
                          borderRadius: '12px',
                          display: 'flex',
                          alignItems: 'baseline',
                          fontSize: '14px'
                        }}
                      >
                        <span style={{ marginRight: '5px' }}>Score:</span>
                        <span
                          style={{
                            fontWeight: 'bold',
                            color: questionStates[q.id] === 'fully_answered' ? '#27ae60' : '#3498db',
                            cursor: 'help'
                          }}
                          title={
                            questionStates[q.id] === 'fully_answered'
                            ? "This score is final, and all related factors have been taken into account."
                            : "This score is preliminary and might change as you answer other related questions."
                          }
                        >
                          {scores[q.id]}
                        </span>
                  </div>

                      {explanations[q.id] && (
                        <button 
                          onClick={() => toggleExplanation(q.id)} 
                          style={{ 
                            marginLeft: 10, 
                            padding: '4px 10px', 
                            fontSize: '12px', 
                            backgroundColor: 'white', 
                            color: 'black', 
                            border: '1px solid transparent', // Use transparent border to maintain size
                            boxShadow: '0 0 0 1px black', // Use box-shadow for a smoother border
                            borderRadius: '12px', 
                      cursor: 'pointer',
                            transition: 'background-color 0.2s, color 0.2s'
                          }}
                          onMouseEnter={(e) => { e.target.style.backgroundColor = '#f0f0f0'; }}
                          onMouseLeave={(e) => { e.target.style.backgroundColor = 'white'; }}
                        >
                          {expandedExplanations[q.id] ? 'Collapse' : 'Explain'}
                        </button>
                      )}
                    </div>
                  )}
                </div>
                {expandedExplanations[q.id] && explanations[q.id] && (
                  <div style={{ marginTop: '16px', padding: '12px', backgroundColor: '#f8f9fa', border: '1px solid #e9ecef', borderRadius: '6px', fontSize: '14px', color: '#2c3e50', lineHeight: '1.6' }}>
                    {explanations[q.id]}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
};

export default QuestionSection;