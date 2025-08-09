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
import MetaQuestionsSection from './MetaQuestionsSection';

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
    sections, metaQuestions, aiPrompt, calculations,
    answers, setAnswers, scores, setScores, questionStates, setQuestionStates,
    explanations, setExplanations, loading: contextLoading, labels
  } = context || {};

  const [depWarnings, setDepWarnings] = useState({});
  const [expandedExplanations, setExpandedExplanations] = useState({});
  const [submissionTrigger, setSubmissionTrigger] = useState(null);
  const startupCheckHasRun = useRef(false);

  // --- START: UTILITY AND HELPER FUNCTIONS ---

  const findQuestionById = useCallback((id) => {
    if (!sections || !metaQuestions) return null;
    for (const section of sections) {
      const question = section.questions.find(q => q.id === id);
      if (question) return question;
    }
    const metaQuestion = metaQuestions.find(q => q.id === id);
    if (metaQuestion) return metaQuestion;
    return null;
  }, [sections, metaQuestions]);

  const getReadableAnswer = useCallback((question, answerValue) => {
    if (!question || answerValue === undefined || answerValue === null || answerValue === '') return answerValue;
    if (question.question_type === 'yes-no') return answerValue === 'yes' ? 'Yes' : 'No';
    if (Array.isArray(answerValue) && question.options) {
      return answerValue.map(val => {
        const option = question.options.find(opt => opt.code === val);
        return option ? option.label : val;
      }).join(', ');
    }
    if (question.options) {
      const option = question.options.find(opt => opt.code === answerValue);
      return option ? option.label : answerValue;
    }
    return answerValue;
  }, []);

  const getQuestionState = useCallback((question, currentAnswers, currentScores, currentStates) => {
    const hasAnswer = currentAnswers[question.id] && currentAnswers[question.id] !== '';
    const hasScore = currentScores[question.id] !== undefined;
    const dependencies = getQuestionDependencies(question);
    
    if (!hasAnswer) return 'unanswered';
    if (dependencies.length === 0) return 'fully_answered';
    
    const allDependenciesFullyAnswered = dependencies.every(depId => currentStates[depId] === 'fully_answered');
    if (allDependenciesFullyAnswered && hasScore) return 'fully_answered';
    
    return 'partially_answered';
  }, []);

  const computeAllStates = useCallback((currentScores, currentStates) => {
    const newStates = { ...currentStates };
    for (const sec of sections) {
      for (const q of sec.questions) {
        newStates[q.id] = getQuestionState(q, answers, currentScores, newStates);
      }
    }
    return newStates;
  }, [sections, answers, getQuestionState]);

  const evaluateAnswer = useCallback(async (si, qi) => {
    const question = sections[si]?.questions[qi];
    if (!question) return null;

    try {
      const payload = {
        system: aiPrompt,
        additional_context: question.prompt_add || '',
        meta: {},
        question: { id: question.id, text: question.text },
        answer: getReadableAnswer(question, answers[question.id]),
        answers_ctx: {}
      };

      if (question.ai_context?.include_meta) {
        question.ai_context.include_meta.forEach(metaId => {
          const metaQuestion = findQuestionById(metaId);
          if (metaQuestion && answers[metaId]) {
            payload.meta[metaQuestion.text] = getReadableAnswer(metaQuestion, answers[metaId]);
          }
        });
      }

      if (question.ai_context?.include_answers) {
        question.ai_context.include_answers.forEach(answerId => {
          const ctxQuestion = findQuestionById(answerId);
          if (ctxQuestion && answers[answerId]) {
            payload.answers_ctx[ctxQuestion.text] = getReadableAnswer(ctxQuestion, answers[answerId]);
          }
        });
      }

      console.log('--- Frontend Payload ---');
      console.log(JSON.stringify(payload, null, 2));
      console.log('------------------------');

      const response = await fetch('/api/simple-evaluate.mjs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      return (data.score !== undefined && data.explanation !== undefined) ? data : null;

    } catch (error) {
      console.error('Error evaluating answer:', error);
      alert('Error evaluating answer. Please try again.');
      return null;
    } finally {
      // setLoading(prev => ({ ...prev, [key]: false })); // Removed unused loading state
    }
  }, [sections, answers, aiPrompt, getReadableAnswer, findQuestionById]);

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

    for(const {question, si, qi} of initialQuestions) {
      const result = await evaluateAnswer(si, qi);
      if (result) {
        currentScores[question.id] = result.score;
        currentExplanations[question.id] = result.explanation;
      }
    }

    let currentStates = computeAllStates(currentScores, questionStates);
    let reevaluatedInPass = true;
    let passes = 0;

    while (reevaluatedInPass && passes < 10) {
      passes++;
      reevaluatedInPass = false;
      const reevalInfo = findNextQuestionToReevaluate(currentStates);

      if (reevalInfo) {
        const { question: questionToReevaluate, si: reeval_si, qi: reeval_qi } = reevalInfo;
        const result = await evaluateAnswer(reeval_si, reeval_qi);
        if (result) {
          currentScores[questionToReevaluate.id] = result.score;
          currentExplanations[questionToReevaluate.id] = result.explanation;
          currentStates = computeAllStates(currentScores, currentStates);
          reevaluatedInPass = true;
        }
      }
    }

    console.log('[Orchestrator] Loop finished. Committing final state.');
    if (calculations && calculations.length > 0) {
      currentScores = applyCalculations(currentScores, calculations);
    }

    console.log('[Orchestrator] Final scores to commit:', currentScores);
    console.log('[Orchestrator] Final explanations to commit:', currentExplanations);
    console.log('[Orchestrator] Final states to commit:', currentStates);

    setScores(prev => ({...prev, ...currentScores}));
    setExplanations(prev => ({...prev, ...currentExplanations}));
    setQuestionStates(prev => ({...prev, ...currentStates}));
  }, [calculations, computeAllStates, evaluateAnswer, explanations, findNextQuestionToReevaluate, questionStates, scores, sections, setExplanations, setQuestionStates, setScores]);
  
  const handleAnswerChange = useCallback((question, answer, submitNow = false) => {
    console.log('[handleAnswerChange] Fired for:', question.id, 'with value:', answer, 'and submitNow:', submitNow);
    const newAnswers = {...answers, [question.id]: answer};
    setAnswers(newAnswers);

    if (depWarnings[question.id]) {
      setDepWarnings(prev => ({...prev, [question.id]: undefined }));
    }

    const newState = getQuestionState(question, newAnswers, scores, questionStates);
    setQuestionStates(prev => ({...prev, [question.id]: newState}));

    if (submitNow) {
      setSubmissionTrigger({ question });
    }
  }, [answers, depWarnings, getQuestionState, questionStates, scores, setAnswers, setQuestionStates]);

  const handleAnswerBlur = useCallback((question) => {
    console.log('[handleAnswerBlur] Fired for:', question.id);
    if (answers[question.id]) {
      setSubmissionTrigger({ question });
    }
  }, [answers]);

  const handleMetaChangeAndReevaluateDependents = useCallback((metaQuestionId) => {
    if (!sections) return;
    const allQuestions = sections.flatMap(sec => sec.questions);
    const dependentQuestions = allQuestions.filter(q =>
      q.ai_context?.include_meta?.includes(metaQuestionId) && answers[q.id]
    );

    if (dependentQuestions.length > 0) {
      handleSubmitAndResolveDependencies(null, null, dependentQuestions);
    }
  }, [sections, answers, handleSubmitAndResolveDependencies]);
  
  const runStartupCheck = useCallback(async () => {
    let currentScores = { ...scores };
    let currentStates = computeAllStates(currentScores, questionStates);

    let reevaluatedInPass = true;
    while (reevaluatedInPass) {
      reevaluatedInPass = false;
      const reevalInfo = findNextQuestionToReevaluate(currentStates);

      if (reevalInfo) {
        const { question: questionToReevaluate, si: reeval_si, qi: reeval_qi } = reevalInfo;
        const result = await evaluateAnswer(reeval_si, reeval_qi);
        if (result) {
          currentScores[questionToReevaluate.id] = result.score;
          currentStates = computeAllStates(currentScores, currentStates);
          reevaluatedInPass = true;
        }
      }
    }

    if (calculations && calculations.length > 0) {
      currentScores = applyCalculations(currentScores, calculations);
    }
    setScores(currentScores);
    setQuestionStates(currentStates);
  }, [calculations, computeAllStates, evaluateAnswer, findNextQuestionToReevaluate, questionStates, scores, setQuestionStates, setScores]);

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
    if (!contextLoading && sections?.length > 0 && metaQuestions?.length > 0 && !startupCheckHasRun.current) {
      runStartupCheck();
      startupCheckHasRun.current = true;
    }
  }, [contextLoading, sections, metaQuestions, runStartupCheck]);

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
      {metaQuestions && metaQuestions.length > 0 && (
        <MetaQuestionsSection onMetaChange={handleMetaChangeAndReevaluateDependents} />
      )}
      
      {sections.map((section, si) => (
        <div key={si} style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '20px', color: '#2c3e50' }}>
            {section.title}
          </h2>
          {section.questions.map((q, qi) => {
            const key = `q-${si}-${qi}`;
            return (
              <div
                key={key}
                style={{
                  background: '#fff', padding: '24px', marginBottom: '28px',
                  borderRadius: '12px', border: depWarnings[key] ? '2px solid #e74c3c' : '1px solid #e1e8ed'
                }}
              >
                <div style={{ marginBottom: '16px' }}>
                  <strong style={{ color: '#2c3e50' }}>{q.text}</strong>
                </div>
                {q.hint && <div style={{ fontSize: '14px', color: '#7f8c8d', marginTop: 8, marginBottom: 8, fontStyle: 'italic' }}>💡 {q.hint}</div>}
                <AnswerInput
                  q={q} value={answers[q.id] || ''}
                  onChange={(value, submitNow) => handleAnswerChange(q, value, submitNow)}
                  onBlur={() => handleAnswerBlur(q)}
                  labels={labels} answers={answers} setAnswers={setAnswers}
                />
                <div style={{ display: 'flex', alignItems: 'center', marginTop: 16 }}>
                  {scores[q.id] !== undefined && (
                    <div style={{ marginLeft: 0, display: 'flex', alignItems: 'center' }}>
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
                      {explanations[q.id] && (
                        <button onClick={() => toggleExplanation(q.id)} style={{ marginLeft: 10, padding: '2px 8px', fontSize: '12px', backgroundColor: '#ecf0f1', color: '#2c3e50', border: '1px solid #bdc3c7', borderRadius: '3px', cursor: 'pointer' }}>
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