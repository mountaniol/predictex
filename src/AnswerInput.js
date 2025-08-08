import React, { useState } from 'react';

const AnswerInput = ({ q, value, onChange, labels }) => {
  const [showOtherText, setShowOtherText] = useState(false);
  const [otherText, setOtherText] = useState('');

  // Handle follow-up questions
  const [followUpAnswers, setFollowUpAnswers] = useState({});

  const handleFollowUpChange = (followUpId, followUpValue) => {
    setFollowUpAnswers(prev => ({
      ...prev,
      [followUpId]: followUpValue
    }));
  };

  const shouldShowFollowUp = (followUp) => {
    if (!followUp.when || !followUp.when.in) return false;
    if (Array.isArray(value)) {
      return value.some(v => followUp.when.in.includes(v));
    }
    return followUp.when.in.includes(value);
  };

  const renderFollowUps = () => {
    if (!q.follow_ups) return null;

    return q.follow_ups.map((followUp, index) => {
      if (!shouldShowFollowUp(followUp)) return null;

      return (
        <div key={index} style={{ marginLeft: 20, marginTop: 12, paddingLeft: 12, borderLeft: '2px solid #e1e8ed' }}>
          <div style={{ fontSize: '14px', color: '#7f8c8d', marginBottom: 8 }}>
            {followUp.ask.question_type === 'text' && followUp.ask.placeholder}
          </div>
          {renderInput(followUp.ask, followUpAnswers[followUp.ask.id] || '', handleFollowUpChange)}
        </div>
      );
    });
  };

  const renderInput = (question, inputValue, inputOnChange) => {
    const questionType = question.question_type;
    const ui = question.ui;

    switch (questionType) {
      case 'yes-no':
        const yesLabel = labels?.yes || 'Yes';
        const noLabel = labels?.no || 'No';
        return (
          <div>
            <label style={{ marginRight: 16 }}>
              <input
                type="radio"
                checked={inputValue === 'yes'}
                onChange={() => inputOnChange('yes')}
              />
              {' '}{yesLabel}
            </label>
            <label>
              <input
                type="radio"
                checked={inputValue === 'no'}
                onChange={() => inputOnChange('no')}
              />
              {' '}{noLabel}
            </label>
          </div>
        );

      case 'choice-single':
        if (ui === 'dropdown') {
          return (
            <select
              value={inputValue}
              onChange={(e) => inputOnChange(e.target.value)}
              style={{ width: '100%', padding: 8, borderRadius: 4, border: '1px solid #ddd' }}
            >
              <option value="">Select an option</option>
              {question.options?.map((option) => (
                <option key={option.code} value={option.code}>
                  {option.label}
                </option>
              ))}
            </select>
          );
        } else {
          return (
            <div>
              {question.options?.map((option) => (
                <label key={option.code} style={{ display: 'block', marginBottom: 8 }}>
                  <input
                    type="radio"
                    checked={inputValue === option.code}
                    onChange={() => inputOnChange(option.code)}
                  />
                  {' '}{option.label}
                </label>
              ))}
            </div>
          );
        }

      case 'choice-multi':
        const currentValues = Array.isArray(inputValue) ? inputValue : [];
        
        const handleMultiChange = (optionCode, checked) => {
          let newValues;
          if (checked) {
            if (q.max_selections && currentValues.length >= q.max_selections) {
              // Remove oldest selection if max reached
              newValues = [...currentValues.slice(1), optionCode];
            } else {
              newValues = [...currentValues, optionCode];
            }
          } else {
            newValues = currentValues.filter(v => v !== optionCode);
          }
          
          // Handle "other" option
          if (optionCode === 'other') {
            setShowOtherText(checked);
            if (!checked) {
              setOtherText('');
            }
          }
          
          inputOnChange(newValues);
        };

        return (
          <div>
            {question.options?.map((option) => (
              <label key={option.code} style={{ display: 'block', marginBottom: 8 }}>
                <input
                  type="checkbox"
                  checked={currentValues.includes(option.code)}
                  onChange={(e) => handleMultiChange(option.code, e.target.checked)}
                />
                {' '}{option.label}
              </label>
            ))}
            
            {showOtherText && q.with_other && (
              <div style={{ marginTop: 12 }}>
                <input
                  type="text"
                  placeholder="Please specify..."
                  value={otherText}
                  onChange={(e) => setOtherText(e.target.value)}
                  style={{ width: '100%', padding: 8, borderRadius: 4, border: '1px solid #ddd' }}
                />
              </div>
            )}
          </div>
        );

      case 'number':
        return (
          <input
            type="number"
            value={inputValue}
            onChange={(e) => inputOnChange(e.target.value)}
            style={{ width: '100%', padding: 8, borderRadius: 4, border: '1px solid #ddd' }}
          />
        );

      case 'text':
        if (ui === 'textarea') {
          return (
            <textarea
              rows={3}
              value={inputValue}
              onChange={(e) => inputOnChange(e.target.value)}
              placeholder={question.placeholder}
              maxLength={question.max_chars}
              style={{ 
                width: '100%', 
                padding: 8, 
                borderRadius: 4, 
                border: '1px solid #ddd',
                resize: 'vertical'
              }}
            />
          );
        } else {
          return (
            <input
              type="text"
              value={inputValue}
              onChange={(e) => inputOnChange(e.target.value)}
              placeholder={question.placeholder}
              maxLength={question.max_chars}
              style={{ width: '100%', padding: 8, borderRadius: 4, border: '1px solid #ddd' }}
            />
          );
        }

      case 'textarea':
        return (
          <textarea
            rows={4}
            value={inputValue}
            onChange={(e) => inputOnChange(e.target.value)}
            placeholder={question.placeholder}
            maxLength={question.max_chars}
            style={{ 
              width: '100%', 
              padding: 8, 
              borderRadius: 4, 
              border: '1px solid #ddd',
              resize: 'vertical'
            }}
          />
        );

      default:
        return (
          <textarea
            rows={3}
            value={inputValue}
            onChange={(e) => inputOnChange(e.target.value)}
            style={{ 
              width: '100%', 
              padding: 8, 
              borderRadius: 4, 
              border: '1px solid #ddd',
              resize: 'vertical'
            }}
          />
        );
    }
  };

  return (
    <div>
      {renderInput(q, value, onChange)}
      {renderFollowUps()}
    </div>
  );
};

export default AnswerInput;
