import React, { useState } from 'react';

const QuestionSection = ({ sections, aiPrompt, apiKey }) => {
  const [answers, setAnswers] = useState({});
  const [scores, setScores] = useState({});
  const [loading, setLoading] = useState({});
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState({});

  const qKey = (si, qi) => `${si}-${qi}`;

  const handleAnswerChange = (si, qi, value) => {
    setAnswers(prev => ({ ...prev, [qKey(si, qi)]: value }));
  };

  const getLocationAnswer = () => {
    if (sections.length && sections[0].questions.length) {
      return answers[qKey(0, 0)] || '';
    }
    return '';
  };

  const evaluateAnswer = async (si, qi) => {
    const key = qKey(si, qi);
    setLoading(prev => ({ ...prev, [key]: true }));
    setError('');
    try {
      const q = sections[si].questions[qi];
      const ans = answers[key];
      let userPrompt = `Question: ${q.text}\n`;
      if (q.question_type === 'yes-no' || q.question_type === 'numeric') {
        userPrompt += `answer = ${ans}`;
      } else {
        userPrompt += `Answer: ${ans}`;
      }

      let systemPrompt = aiPrompt;
      if (q.prompt) {
        systemPrompt = q.prompt;
      } else if (q.prompt_add) {
        systemPrompt = `${aiPrompt} ${q.prompt_add}`;
      }

      const loc = getLocationAnswer();
      if (loc && si > 0) {
        systemPrompt = `Location context: ${loc}. ${systemPrompt}`;
      }

      const resp = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model: 'gpt-4o-mini',
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: userPrompt },
          ],
          max_tokens: 20,
        }),
      });
      const data = await resp.json();
      if (data.error) throw new Error(data.error.message);

      let score;
      if (q.question_type === 'yes-no') {
        score = ans === 'yes' ? 100 : 0;
      } else {
        const content = data.choices[0].message.content;
        const m = content.match(/\d{1,3}/);
        score = m ? Math.min(100, Math.max(0, parseInt(m[0], 10))) : null;
      }
      setScores(prev => ({ ...prev, [key]: score }));
    } catch (e) {
      console.error('Evaluation error:', e);
      setError(e.message);
    } finally {
      setLoading(prev => ({ ...prev, [key]: false }));
    }
  };

  const toggleSection = idx => {
    setExpanded(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  // Подсчёт прогресса
  const total = sections.reduce((sum, s) => sum + s.questions.length, 0);
  const allDone = total > 0 && Object.keys(scores).length === total;
  const avg = total
    ? (Object.values(scores).reduce((a, b) => a + (b || 0), 0) / total).toFixed(2)
    : 0;

  return (
    <>
      {error && (
        <div style={{ color: 'red', margin: '10px 0' }}>{error}</div>
      )}
      {sections.map((sec, si) => (
        <div key={si} style={{ marginBottom: 32 }}>
          <div
            onClick={() => toggleSection(si)}
            style={{
              cursor: 'pointer',
              background: '#f0f3fa',
              padding: 12,
              borderRadius: 8,
            }}
          >
            <strong>
              {expanded[si] ? '▼' : '►'} {sec.section}
            </strong>
          </div>
          {expanded[si] &&
            sec.questions.map((q, qi) => {
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
                    <strong>Q{qi + 1}:</strong> {q.text}
                  </div>
                  <AnswerInput
                    q={q}
                    value={answers[key] || ''}
                    onChange={v => handleAnswerChange(si, qi, v)}
                  />
                  <button
                    disabled={loading[key] || !answers[key]}
                    onClick={() => evaluateAnswer(si, qi)}
                    style={{ marginTop: 8 }}
                  >
                    {loading[key]
                      ? 'Evaluating...'
                      : scores[key]
                      ? 'Re-evaluate'
                      : 'Submit'}
                  </button>
                  {scores[key] !== undefined && (
                    <span style={{ marginLeft: 16 }}>
                      Score: {scores[key]}
                    </span>
                  )}
                </div>
              );
            })}
        </div>
      ))}
      {allDone && (
        <div style={{ textAlign: 'center', marginTop: 32 }}>
          <h3>All questions evaluated!</h3>
          <p>Average Score: {avg}</p>
        </div>
      )}
    </>
  );
};

const AnswerInput = ({ q, value, onChange }) => {
  if (q.question_type === 'yes-no') {
    return (
      <div>
        <label>
          <input
            type="radio"
            checked={value === 'yes'}
            onChange={() => onChange('yes')}
          />{' '}
          Yes
        </label>
        <label style={{ marginLeft: 8 }}>
          <input
            type="radio"
            checked={value === 'no'}
            onChange={() => onChange('no')}
          />{' '}
          No
        </label>
      </div>
    );
  } else if (q.question_type === 'numeric') {
    return (
      <input
        type="number"
        value={value}
        onChange={e => onChange(e.target.value)}
      />
    );
  }
  return (
    <textarea
      rows={3}
      value={value}
      onChange={e => onChange(e.target.value)}
    />
  );
};

export default QuestionSection;