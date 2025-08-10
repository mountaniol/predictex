import React, { useContext, useState, useEffect, useCallback, useRef } from 'react';
import { AppContext } from './App';
import AnswerInput from './AnswerInput';

const getQuestionDependencies = (question) => {
  return question.ai_context?.include_answers || [];
};

const QuestionSection = () => {
  const context = useContext(AppContext);
  const { 
    sections, calculations,
    answers, setAnswers, scores, setScores, questionStates, setQuestionStates,
    explanations, setExplanations, loading: contextLoading, labels
  } = context || {};

  const [depWarnings, setDepWarnings] = useState({});
  const [submissionTrigger, setSubmissionTrigger] = useState(null);
  const startupCheckHasRun = useRef(false);

  const handleAnswerChange = useCallback((questionId, value) => {
    setAnswers(prev => ({ ...prev, [questionId]: value }));
  }, [setAnswers]);

  const handleScoreChange = useCallback((questionId, value) => {
    setScores(prev => ({ ...prev, [questionId]: value }));
  }, [setScores]);

  const handleExplanationChange = useCallback((questionId, value) => {
    setExplanations(prev => ({ ...prev, [questionId]: value }));
  }, [setExplanations]);

  const handleQuestionStateChange = useCallback((questionId, value) => {
    setQuestionStates(prev => ({ ...prev, [questionId]: value }));
  }, [setQuestionStates]);

  const handleSubmission = useCallback(() => {
    setSubmissionTrigger({});
  }, [setSubmissionTrigger]);

  const runStartupCheck = useCallback(async () => {
    let currentScores = { ...scores };
    let currentStates = computeAllStates(currentScores, questionStates);
    // ... existing code ...
  }, [scores, questionStates]);

  useEffect(() => {
    if (answers[question.id]) {
      setSubmissionTrigger({ question });
    }
  }, [answers]);

  useEffect(() => {
    if (!contextLoading && sections?.length > 0 && !startupCheckHasRun.current) {
      runStartupCheck();
      startupCheckHasRun.current = true;
    }
  }, [contextLoading, sections, runStartupCheck]);

  // --- END: LIFECYCLE HOOKS ---

  return (
    <div>
      {sections.map((section, si) => (
        <div key={si} style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '20px', color: '#2c3e50' }}>
            {section.title}
          </h2>
          {section.questions.map((question, qi) => (
            <div key={qi} style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '10px', color: '#34495e' }}>
                {question.title}
              </h3>
              <AnswerInput
                question={question}
                answer={answers[question.id]}
                onAnswerChange={handleAnswerChange}
                score={scores[question.id]}
                onScoreChange={handleScoreChange}
                explanation={explanations[question.id]}
                onExplanationChange={handleExplanationChange}
                questionState={questionStates[question.id]}
                onQuestionStateChange={handleQuestionStateChange}
                depWarnings={depWarnings[question.id]}
                labels={labels}
              />
            </div>
          ))}
        </div>
      ))}
      <button onClick={handleSubmission} disabled={Object.keys(answers).length === 0 || contextLoading}>
        Submit Answers
      </button>
    </div>
  );
};

export default QuestionSection;
