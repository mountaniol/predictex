import React, { useContext, useState } from 'react';
import { AppContext } from './App';
import AnswerInput from './AnswerInput';
import MetaQuestionsSection from './MetaQuestionsSection';

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

  const qKey = (si, qi) => `${si}-${qi}`;

  const handleAnswerChange = (si, qi, value) => {
    const question = sections[si]?.questions[qi];
    if (!question) return;

    // Handle follow-up data
    if (value && typeof value === 'object' && value.followUpData) {
      // This is follow-up data, update both main answer and follow-up
      setAnswers(prev => ({
        ...prev,
        [question.id]: value.mainValue,
        ...value.followUpData
      }));
    } else {
      // Regular answer change
      setAnswers(prev => ({
        ...prev,
        [question.id]: value
      }));
    }

    // Clear dependency warning for this question when answer changes
    if (depWarnings[question.id]) {
      setDepWarnings(prev => ({
        ...prev,
        [question.id]: undefined
      }));
    }
  };

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

      console.log('Sending payload to AI:', payload);

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
      console.log('AI response:', data);

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
                  <strong>{q.id}:</strong> {q.text}
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