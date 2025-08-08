import React, { useContext } from 'react';
import { AppContext } from './App';
import AnswerInput from './AnswerInput';

const MetaQuestionsSection = () => {
  const context = useContext(AppContext);
  const { metaQuestions, answers, setAnswers, labels } = context || {};

  if (!metaQuestions || metaQuestions.length === 0) {
    return null;
  }

  const handleAnswerChange = (questionId, value) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: value
    }));
  };

  return (
    <div style={{ marginBottom: 32 }}>
      <h2 style={{
        fontSize: '24px',
        fontWeight: 'bold',
        marginBottom: '20px',
        color: '#2c3e50'
      }}>
        Basic Information
      </h2>
      
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
              <strong style={{ color: '#2c3e50' }}>{question.id}:</strong>
              <span style={{ marginLeft: 8 }}>{question.text}</span>
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
            />
          </div>
        );
      })}
    </div>
  );
};

export default MetaQuestionsSection;
