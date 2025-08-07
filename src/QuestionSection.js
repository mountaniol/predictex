import React, { useState, useContext } from 'react';
import { AppContext } from './App';

const QuestionSection = () => {
  const context = useContext(AppContext);
  const [loading, setLoading] = useState({});
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState({});
  const [depWarnings, setDepWarnings] = useState({});

  if (!context) {
    return <div>Loading...</div>;
  }
  const { 
    sections, 
    aiPrompt, 
    apiKey, 
    labels: ctxLabels, 
    calculations = [], 
    loading: contextLoading, 
    error: contextError,
    answers,
    setAnswers,
    scores,
    setScores
  } = context;
  console.log(`[context] loaded ${calculations.length} calculation rules, ${Object.keys(answers).length} answers, ${Object.keys(scores).length} scores`);

  // labels come from AppContext; fall back to defaults
  const activeLabels = ctxLabels && ctxLabels.yes ? ctxLabels : { yes: 'Yes', no: 'No' };



  const qKey = (si, qi) => `${si}-${qi}`;

  const handleAnswerChange = (si, qi, value) => {
    const questionId = sections[si].questions[qi].id;
    setAnswers(prev => ({ ...prev, [questionId]: value }));
    // Clear warning for this question when answer changes
    setDepWarnings(prev => ({ ...prev, [questionId]: '' }));
  };

  const getLocationAnswer = () => {
    if (sections.length && sections[0].questions.length) {
      const locationQuestionId = sections[0].questions[0].id;
      return answers[locationQuestionId] || '';
    }
    return '';
  };

  // The 'evaluateAnswer' function uses the 'calculations' array from AppContext
  // to perform inter-question dependency checks.
  /**
   * Evaluate an answer for a given question.
   * @param {number} si - Section index
   * @param {number} qi - Question index within the section
   * Performs dependency checks, sends the answer to the AI API, parses the score,
   * applies any post-calculations, and updates component state accordingly.
   */
  const evaluateAnswer = async (si, qi) => {
    console.log(`[evaluateAnswer] called for section ${si}, question ${qi}`);
    console.log('[evaluateAnswer] context object:', context);
    console.log('[evaluateAnswer] global calculations:', calculations);
    console.log('[evaluateAnswer] total sections:', sections.length);
    if (sections[si]) console.log(`[evaluateAnswer] questions in section ${si}:`, sections[si].questions.map(q => q.id));
    setLoading(prev => ({ ...prev, [qKey(si, qi)]: true }));
    setError('');
    // Start evaluation: show loading spinner and clear previous error message
    try {
      // Fetch question object and user-provided answer from state
      const q = sections[si].questions[qi];
      const ans = answers[q.id];
      console.log('[evaluateAnswer] question object:', q);
      console.log('[evaluateAnswer] user answer:', ans);
      // Dependency guard: ensure all prerequisite questions have been answered
      setDepWarnings(prev => ({ ...prev, [q.id]: '' }));
      console.log('[deps] calculations array:', calculations);
      console.log('[deps] answers state before check:', answers, 'for question ID', q.id);
      if (calculations && calculations.length) {
        const lines = calculations.filter(line => line.trim().startsWith(q.id));
        console.log('[deps] filtered lines for', q.id, ':', lines);
        const deps = new Set();
        const idRegex = /\b([A-Z][0-9]+)\b/g;
        lines.forEach(line => {
          const rhs = line.split('=')[1] || '';
          let m;
          while ((m = idRegex.exec(rhs)) !== null) {
            const depId = m[1];
            if (depId !== q.id) deps.add(depId);
          }
        });
        console.log('[deps] deps set for', q.id, ':', Array.from(deps));
        const missingDeps = Array.from(deps).filter(depId => {
          // Check if the dependent question has been answered
          return !answers[depId];
        });
        console.log('[deps] missingDeps for', q.id, ':', missingDeps);
        if (missingDeps.length) {
          const msg = 'Please answer the following question(s) first: ' + missingDeps.join(', ');
          setDepWarnings(prev => ({ ...prev, [q.id]: msg }));
          setLoading(prev => ({ ...prev, [qKey(si, qi)]: false }));
          return;
        }
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
      // Send request to backend API
      const resp = await fetch(apiKey, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: q.text,
          answer: ans,
          systemPrompt: systemPrompt,
          questionType: q.question_type,
        }),
      });
      const data = await resp.json();
      if (data.error) throw new Error(data.error);

      // Extract score from backend response
      const score = data.score;
      console.debug('[score] raw score for', q.id, '=', score);
      setScores(prev => {
        // Update scores state and apply any post-answer calculations (e.g., inter-question dependencies)
        const baseById = { ...prev, [q.id]: score };

        // -------- dependency detection -----------------
        const missing = [];
        calculations
          .filter(line => line.trim().startsWith(q.id))      // rules where current question is target
          .forEach(line => {
            const rhs = line.split('=')[1] || '';
            const idRegex = /\b([A-Z][0-9]+)\b/g;
            let m;
            while ((m = idRegex.exec(rhs)) !== null) {
              const id = m[1];
              if (baseById[id] === undefined) missing.push(id);
            }
          });

        if (missing.length) {
          const msg =
            'Please answer the following question(s) first: ' +
            [...new Set(missing)].join(', ');
          setDepWarnings(prev => ({ ...prev, [q.id]: msg }));
          console.warn('[dep] ' + msg);
        } else {
          setDepWarnings(prev => ({ ...prev, [q.id]: '' }));
        }
        // -----------------------------------------------

        return calculations.length
          ? applyCalculations(baseById, calculations)
          : baseById;
      });
    } catch (e) {
      // On error, log it and display to the user
      console.error('Evaluation error:', e);
      setError(e.message);
    } finally {
      setLoading(prev => ({ ...prev, [qKey(si, qi)]: false }));
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

  if (contextLoading) {
    return <div style={{ textAlign: 'center', padding: '20px' }}>Loading questions...</div>;
  }

  if (contextError) {
    return <div style={{ color: 'red', margin: '10px 0' }}>{contextError}</div>;
  }

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
                    <strong>{q.id}:</strong> {q.text}
                  </div>
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
                    labels={activeLabels}
                  />
                  <button
                    disabled={loading[key] || !answers[q.id]}
                    onClick={() => evaluateAnswer(si, qi)}
                    style={{
                      ...buttonBaseStyle,
                      display: 'block',
                      margin: '16px auto 0',
                      width: 'fit-content',
                      background: '#000000', // force black even when disabled
                      cursor: loading[key] || !answers[q.id] ? 'default' : 'pointer',
                      opacity: loading[key] || !answers[q.id] ? 1 : 1, // no grey-out
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
      {allDone && (
        <div style={{ textAlign: 'center', marginTop: 32 }}>
          <h3>All questions evaluated!</h3>
          <p>Average Score: {avg}</p>
        </div>
      )}
    </>
  );
};

const buttonBaseStyle = {
  background: '#000000',   // solid black
  color: '#ffffff',
  padding: '8px 20px',     // slimmer vertical padding
  border: 'none',
  borderRadius: 6,
  fontWeight: 600,
  fontSize: 15,
  lineHeight: '20px',
  cursor: 'pointer',
  transition: 'opacity 0.2s ease',
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

const AnswerInput = ({ q, value, onChange, labels }) => {
  if (q.question_type === 'yes-no') {
    const yesLabel = labels && labels.yes ? labels.yes : 'Yes';
    const noLabel  = labels && labels.no  ? labels.no  : 'No';
    return (
      <div>
        <label>
          <input
            type="radio"
            checked={value === 'yes'}
            onChange={() => onChange('yes')}
          />{' '}
          {yesLabel}
        </label>
        <label style={{ marginLeft: 8 }}>
          <input
            type="radio"
            checked={value === 'no'}
            onChange={() => onChange('no')}
          />{' '}
          {noLabel}
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
      style={{ width: '100%', marginTop: 8 }}
      value={value}
      onChange={e => onChange(e.target.value)}
    />
  );
};

export default QuestionSection;