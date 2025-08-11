import React from 'react';
import AnswerInput from './AnswerInput';

const MetaQuestionsSection = ({ questions, answers, onAnswerChange }) => {
  if (!questions || questions.length === 0) {
    return null;
  }

  return (
    <div className="meta-questions-section">
      {questions.map((question) => (
        <AnswerInput
          key={question.id}
          question={question}
          // Meta questions don't belong to a numbered section, so pass a special value or null
          sectionIndex={-1} 
        />
      ))}
    </div>
  );
};

export default MetaQuestionsSection;
