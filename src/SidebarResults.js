import React, { useContext, useMemo, useState, useEffect } from 'react';
import { AppContext } from './App';

/**
 * @brief Sidebar results component for desktop layout
 * 
 * Displays evaluation results in a compact sidebar format for desktop users.
 * Shows overall risk assessment, key statistics, and section scores in a
 * space-efficient layout that stays visible while scrolling through questions.
 * 
 * @function SidebarResults
 * @returns {JSX.Element} Compact sidebar results interface
 * 
 * @context {AppContext} - Global application state and functions
 * @context {Array} sections - Questions grouped by cluster/section
 * @context {Object} answers - User answers to questions
 * @context {Object} scores - AI evaluation scores
 * @context {Array} calculations - Calculation rules for derived scores
 * 
 * @state {Object} computedScores - Calculated scores from calculation rules
 * @state {Object} overallStats - Overall statistics and risk assessment
 * 
 * @dependencies {AppContext} - Global state management
 * 
 * @architecture {Component Hierarchy} - Sidebar results display component
 * @architecture {Responsive Design} - Desktop-only layout
 * @architecture {Data Processing} - Computes overall statistics and risk levels
 * 
 * @role {Results Display} - Shows compact evaluation results
 * @role {Statistics Calculator} - Computes overall risk statistics
 * @role {Risk Assessor} - Categorizes overall risk level
 * @role {Sidebar UI} - Provides fixed sidebar interface
 */
const SidebarResults = () => {
  const { questionSetId, sections, answers, scores, calculations, questionStates, setAnswers, setScores, setQuestionStates, explanations, setExplanations, loadAndApplyState } = useContext(AppContext);
  const [clearState, setClearState] = useState(0); // 0: idle, 1: first press, 2: second press
  const [clearTimer, setClearTimer] = useState(null);
  const [tooltip, setTooltip] = useState({ visible: false, text: '', id: null });
  const [tooltipTimer, setTooltipTimer] = useState(null);


  // Effect to clear the timer if the component unmounts
  useEffect(() => {
    return () => {
      if (clearTimer) {
        clearTimeout(clearTimer);
      }
    };
  }, [clearTimer]);

  const handleSaveToFile = () => {
    const dataToSave = {
      questionSetId,
      answers,
      scores,
      questionStates,
      explanations,
      savedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(dataToSave, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `qna-evaluator-state-${questionSetId}-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleLoadFromFile = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result);

        if (data.questionSetId !== questionSetId) {
          // If the question set is different, use the new central function
          // to load the correct question set and then apply the state.
          console.log(`Switching from question set ${questionSetId} to ${data.questionSetId}`);
          loadAndApplyState(data);
        } else {
          // If it's the same question set, just update the state directly.
          if (data.answers && data.scores && data.questionStates) {
            setAnswers(data.answers);
            setScores(data.scores);
            setQuestionStates(data.questionStates);
            setExplanations(data.explanations || {});
          } else {
            throw new Error('Invalid file format.');
          }
        }
      } catch (error) {
        alert(`Error loading file: ${error.message}`);
      }
    };
    reader.readAsText(file);
    // Reset the input value to allow loading the same file again
    event.target.value = null;
  };

  const handleMouseEnter = (text, id) => {
    if (tooltipTimer) clearTimeout(tooltipTimer);
    const timer = setTimeout(() => {
      setTooltip({ visible: true, text, id });
    }, 1000);
    setTooltipTimer(timer);
  };

  const handleMouseLeave = () => {
    if (tooltipTimer) clearTimeout(tooltipTimer);
    setTooltip({ visible: false, text: '', id: null });
  };

  const handleClearData = () => {
    if (clearTimer) {
      clearTimeout(clearTimer);
    }

    if (clearState === 0) {
      setClearState(1);
      const timer = setTimeout(() => {
        setClearState(0);
        console.log('Clear data confirmation timed out.');
      }, 5000);
      setClearTimer(timer);
    } else if (clearState === 1) {
      setClearState(2);
      const timer = setTimeout(() => {
        setClearState(0);
        console.log('Clear data confirmation timed out.');
      }, 5000);
      setClearTimer(timer);
    } else if (clearState === 2) {
      console.log('Clearing all data.');
      setAnswers({});
      setScores({});
      setQuestionStates({});
      setExplanations({});
      if (questionSetId) {
        localStorage.removeItem(`qna-evaluator-answers-${questionSetId}`);
        localStorage.removeItem(`qna-evaluator-scores-${questionSetId}`);
        localStorage.removeItem(`qna-evaluator-questionStates-${questionSetId}`);
        localStorage.removeItem(`qna-evaluator-explanations-${questionSetId}`);
      }
      setClearState(0);
      setClearTimer(null);
    }
  };


  // Apply calculation rules to get computed scores
  const computedScores = useMemo(() => {
    if (!calculations || calculations.length === 0) {
      return scores;
    }

    // This function is defined inside useMemo to re-run only when scores/calculations change.
    const applyCalculations = (base, calcArr) => {
      const res = { ...base };
      const idRegex = /\b([A-Z]+[0-9]+[A-Z]?)\b/g; // Regex for question IDs like SG01, SG03A etc.

      calcArr.forEach(line => {
        if (!line || typeof line !== 'string') return;

        const parts = line.split('=');
        if (parts.length !== 2) return;

        const target = parts[0].trim();
        let expr = parts[1].trim();

        // Collect referenced IDs
        const referenced = [];
        expr.replace(idRegex, (_, id) => {
          referenced.push(id);
          return _;
        });

        // Check that all referenced IDs exist
        const unknown = referenced.filter(id => res[id] === undefined);
        if (unknown.length) return;

        // Replace IDs with current values
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

    return applyCalculations(scores, calculations);
  }, [scores, calculations]);

  // Calculate overall statistics
  const overallStats = useMemo(() => {
    const allScores = Object.values(computedScores).filter(score => 
      typeof score === 'number' && !isNaN(score)
    );

    if (allScores.length === 0) {
      return {
        averageScore: 0,
        totalQuestions: 0,
        evaluatedQuestions: 0,
        fullyEvaluated: 0,
        partlyEvaluated: 0,
        riskLevel: 'Unknown',
        riskColor: '#999',
        riskDescription: 'No evaluations completed'
      };
    }

    const averageScore = allScores.reduce((sum, score) => sum + score, 0) / allScores.length;
    const totalQuestions = sections.reduce((sum, section) => sum + section.questions.length, 0);
    const evaluatedQuestions = allScores.length;
    
    // Calculate new metrics
    const fullyEvaluated = Object.values(questionStates).filter(state => state === 'fully_answered').length;
    const partlyEvaluated = Object.values(questionStates).filter(state => state === 'partially_answered').length;

    // Determine risk level
    let riskLevel, riskColor, riskDescription;
    if (averageScore >= 80) {
      riskLevel = 'Low Risk';
      riskColor = '#28a745';
      riskDescription = 'Excellent condition';
    } else if (averageScore >= 60) {
      riskLevel = 'Moderate Risk';
      riskColor = '#ffc107';
      riskDescription = 'Good with concerns';
    } else if (averageScore >= 40) {
      riskLevel = 'High Risk';
      riskColor = '#fd7e14';
      riskDescription = 'Significant concerns';
    } else if (averageScore >= 20) {
      riskLevel = 'Very High Risk';
      riskColor = '#dc3545';
      riskDescription = 'Critical issues';
    } else {
      riskLevel = 'Critical Risk';
      riskColor = '#721c24';
      riskDescription = 'Extremely high risk';
    }

    return {
      averageScore: Math.round(averageScore * 10) / 10,
      totalQuestions,
      evaluatedQuestions,
      fullyEvaluated,
      partlyEvaluated,
      riskLevel,
      riskColor,
      riskDescription
    };
  }, [computedScores, sections, questionStates]);

  return (
    <div style={{
      backgroundColor: 'white',
      borderRadius: 12,
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      border: '1px solid #e9ecef',
      padding: 20,
    }}>
      <h3 style={{
        margin: '0 0 16px 0',
        fontSize: 18,
        fontWeight: 600,
        color: '#2c3e50',
        textAlign: 'center'
      }}>
        Evaluation Results
      </h3>

        <>
          {/* Overall Risk Assessment */}
      <div 
        style={{
          textAlign: 'center',
          marginBottom: 20,
          padding: 16,
          backgroundColor: 'transparent',
          borderRadius: 8,
          border: '1px solid #e0e0e0',
          position: 'relative'
        }}
        onMouseEnter={() => handleMouseEnter("Overall risk score calculated from the average of all evaluated questions. The risk level (Low, Moderate, High) is determined based on this score.", 'overallRisk')}
        onMouseLeave={handleMouseLeave}
      >
        <div style={{
          fontSize: 20,
          fontWeight: 700,
          color: 'black',
          marginBottom: 4
        }}>
          {overallStats.riskLevel}
        </div>
        <div style={{
          fontSize: 14,
          color: 'black',
          marginBottom: 8
        }}>
          {overallStats.riskDescription}
        </div>
        <div style={{
          fontSize: 28,
          fontWeight: 700,
          color: overallStats.riskColor
        }}>
          {overallStats.averageScore}/100
        </div>
        {tooltip.visible && tooltip.id === 'overallRisk' && (
          <div style={{
            position: 'absolute',
            bottom: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            marginBottom: '5px',
            padding: '8px 12px',
            backgroundColor: '#343a40',
            color: 'white',
            borderRadius: '4px',
            fontSize: '12px',
            width: '250px',
            whiteSpace: 'normal',
            zIndex: 10,
            textAlign: 'center'
          }}>
            {tooltip.text}
          </div>
        )}
      </div>

      {/* Statistics */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 8,
        marginBottom: 20
      }}>
        <div 
          style={{
            textAlign: 'center',
            padding: 12,
            backgroundColor: 'transparent',
            border: '1px solid #e0e0e0',
            borderRadius: 6,
            position: 'relative'
          }}
          onMouseEnter={() => handleMouseEnter("This is the number of questions that are fully scored. Sometimes, a question's score can change as you answer other related questions. 'Fully' means the score for this question is now final.", 'fully')}
          onMouseLeave={handleMouseLeave}
        >
          <div style={{ fontSize: 18, fontWeight: 600, color: '#27ae60' }}>
            {overallStats.fullyEvaluated}
          </div>
          <div style={{ fontSize: 12, color: '#6c757d' }}>
            Fully
          </div>
          {tooltip.visible && tooltip.id === 'fully' && (
            <div style={{
              position: 'absolute',
              bottom: '100%',
              left: '50%',
              transform: 'translateX(-50%)',
              marginBottom: '5px',
              padding: '8px 12px',
              backgroundColor: '#343a40',
              color: 'white',
              borderRadius: '4px',
              fontSize: '12px',
              width: '250px',
              whiteSpace: 'normal',
              zIndex: 10,
              textAlign: 'center'
            }}>
              {tooltip.text}
            </div>
          )}
        </div>
        <div 
          style={{
            textAlign: 'center',
            padding: 12,
            backgroundColor: 'transparent',
            border: '1px solid #e0e0e0',
            borderRadius: 6,
            position: 'relative'
          }}
          onMouseEnter={() => handleMouseEnter("These are questions you've answered, but their score isn't final yet. It might be updated as you answer other related questions. The system will do this automatically.", 'partly')}
          onMouseLeave={handleMouseLeave}
        >
          <div style={{ fontSize: 18, fontWeight: 600, color: '#f39c12' }}>
            {overallStats.partlyEvaluated}
          </div>
          <div style={{ fontSize: 12, color: '#6c757d' }}>
            Partly
          </div>
          {tooltip.visible && tooltip.id === 'partly' && (
            <div style={{
              position: 'absolute',
              bottom: '100%',
              left: '50%',
              transform: 'translateX(-50%)',
              marginBottom: '5px',
              padding: '8px 12px',
              backgroundColor: '#343a40',
              color: 'white',
              borderRadius: '4px',
              fontSize: '12px',
              width: '250px',
              whiteSpace: 'normal',
              zIndex: 10,
              textAlign: 'center'
            }}>
              {tooltip.text}
            </div>
          )}
        </div>
        <div 
          style={{
            textAlign: 'center',
            padding: 12,
            backgroundColor: 'transparent',
            border: '1px solid #e0e0e0',
            borderRadius: 6,
            position: 'relative'
          }}
          onMouseEnter={() => handleMouseEnter("The total number of questions that have received a score from the AI, regardless of their dependency status.", 'evaluated')}
          onMouseLeave={handleMouseLeave}
        >
          <div style={{ fontSize: 18, fontWeight: 600, color: '#1976d2' }}>
            {overallStats.evaluatedQuestions}
          </div>
          <div style={{ fontSize: 12, color: '#6c757d' }}>
            Evaluated
          </div>
          {tooltip.visible && tooltip.id === 'evaluated' && (
            <div style={{
              position: 'absolute',
              bottom: '100%',
              left: '50%',
              transform: 'translateX(-50%)',
              marginBottom: '5px',
              padding: '8px 12px',
              backgroundColor: '#343a40',
              color: 'white',
              borderRadius: '4px',
              fontSize: '12px',
              width: '250px',
              whiteSpace: 'normal',
              zIndex: 10,
              textAlign: 'center'
            }}>
              {tooltip.text}
            </div>
          )}
        </div>
        <div 
          style={{
            textAlign: 'center',
            padding: 12,
            backgroundColor: 'transparent',
            border: '1px solid #e0e0e0',
            borderRadius: 6,
            position: 'relative'
          }}
          onMouseEnter={() => handleMouseEnter("The total number of questions in the current evaluation set.", 'total')}
          onMouseLeave={handleMouseLeave}
        >
          <div style={{ fontSize: 18, fontWeight: 600, color: '#7b1fa2' }}>
            {overallStats.totalQuestions}
          </div>
          <div style={{ fontSize: 12, color: '#6c757d' }}>
            Total
          </div>
          {tooltip.visible && tooltip.id === 'total' && (
            <div style={{
              position: 'absolute',
              bottom: '100%',
              left: '50%',
              transform: 'translateX(-50%)',
              marginBottom: '5px',
              padding: '8px 12px',
              backgroundColor: '#343a40',
              color: 'white',
              borderRadius: '4px',
              fontSize: '12px',
              whiteSpace: 'nowrap',
              zIndex: 10
            }}>
              {tooltip.text}
            </div>
          )}
        </div>
      </div>

      {/* Section Scores */}
      <div>
        <h4 style={{
          margin: '0 0 12px 0',
          fontSize: 14,
          fontWeight: 600,
          color: '#2c3e50'
        }}>
          Scores by Section
        </h4>
        {sections.map((section, si) => {
          const sectionScores = section.questions
            .map(q => computedScores[q.id])
            .filter(score => typeof score === 'number' && !isNaN(score));

          if (sectionScores.length === 0) return null;

          const sectionAverage = sectionScores.reduce((sum, score) => sum + score, 0) / sectionScores.length;
          const sectionRiskColor = sectionAverage >= 80 ? '#28a745' : 
                                  sectionAverage >= 60 ? '#ffc107' : 
                                  sectionAverage >= 40 ? '#fd7e14' : 
                                  sectionAverage >= 20 ? '#dc3545' : '#721c24';

          return (
            <div key={si} style={{
              marginBottom: 8,
              padding: 8,
              backgroundColor: 'transparent',
              borderRadius: 6,
              border: '1px solid #e0e0e0'
            }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div style={{
                  fontSize: 12,
                  fontWeight: 500,
                  color: '#2c3e50',
                  flex: 1
                }}>
                  {section.title}
                </div>
                <div style={{
                  fontSize: 16,
                  fontWeight: 700,
                  color: sectionRiskColor,
                  marginLeft: 8
                }}>
                  {Math.round(sectionAverage * 10) / 10}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Recommendations */}
      <div 
        style={{
          marginTop: 16,
          padding: 12,
          backgroundColor: 'transparent',
          borderRadius: 6,
          border: '1px solid #e0e0e0',
          position: 'relative'
        }}
        onMouseEnter={() => handleMouseEnter("This is a preliminary recommendation based only on the questions answered so far. It should not be used for final decisions until the entire form is complete, as the overall score can change significantly.", 'recommendation')}
        onMouseLeave={handleMouseLeave}
      >
        <div style={{
          fontSize: 12,
          fontWeight: 600,
          color: '#2c3e50',
          marginBottom: 6
        }}>
          Recommendation
        </div>
        <div style={{
          fontSize: 11,
          color: '#2c3e50',
          lineHeight: 1.4
        }}>
          {overallStats.averageScore >= 80 ? (
            'Proceed with standard due diligence.'
          ) : overallStats.averageScore >= 60 ? (
            'Conduct thorough due diligence on risk areas.'
          ) : overallStats.averageScore >= 40 ? (
            'Additional investigation recommended.'
          ) : overallStats.averageScore >= 20 ? (
            'Proceed with extreme caution.'
          ) : (
            'Strongly recommend against proceeding.'
          )}
        </div>
        {tooltip.visible && tooltip.id === 'recommendation' && (
          <div style={{
            position: 'absolute',
            bottom: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            marginBottom: '5px',
            padding: '8px 12px',
            backgroundColor: '#343a40',
            color: 'white',
            borderRadius: '4px',
            fontSize: '12px',
            width: '250px',
            whiteSpace: 'normal',
            zIndex: 10,
            textAlign: 'center'
          }}>
            {tooltip.text}
          </div>
        )}
      </div>

      {/* Data Management */}
      <div style={{
        marginTop: 20,
        paddingTop: 16,
        borderTop: '1px solid #e9ecef'
      }}>
        {Object.keys(answers).length > 0 && (
          <div style={{
            fontSize: '11px',
            color: '#28a745',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            marginBottom: 8
          }}>
            <span style={{ fontSize: '12px' }}>✓</span>
            Saved {Object.keys(answers).length} / {sections.reduce((sum, section) => sum + section.questions.length, 0)} questions
          </div>
        )}
        <button
          onClick={handleClearData}
          style={{
            padding: '6px 12px',
            fontSize: '11px',
            backgroundColor: 'white',
            color: 'black',
            border: '1px solid transparent',
            boxShadow: '0 0 0 1px black',
            borderRadius: '12px',
            cursor: 'pointer',
            transition: 'background-color 0.2s',
            width: '100%',
            marginBottom: '8px'
          }}
          onMouseEnter={(e) => { e.target.style.backgroundColor = '#f0f0f0'; }}
          onMouseLeave={(e) => { e.target.style.backgroundColor = 'white'; }}
        >
          {clearState === 0 && 'Clear All Data'}
          {clearState === 1 && 'Press 2 more times'}
          {clearState === 2 && 'Press 1 more time'}
        </button>
        <div style={{ position: 'relative' }}>
          <button
            onClick={handleSaveToFile}
            onMouseLeave={handleMouseLeave}
            style={{
              padding: '6px 12px',
              fontSize: '11px',
              backgroundColor: 'white',
              color: 'black',
              border: '1px solid transparent',
              boxShadow: '0 0 0 1px black',
              borderRadius: '12px',
              cursor: 'pointer',
              transition: 'background-color 0.2s',
              width: '100%',
              marginBottom: '8px'
            }}
            onMouseEnter={(e) => {
              e.target.style.backgroundColor = '#f0f0f0';
              handleMouseEnter('Save current form state to file, to restore later from this file', 'saveBtn');
            }}
          >
            Save to File
          </button>
          {tooltip.visible && tooltip.id === 'saveBtn' && (
            <div style={{
              position: 'absolute',
              bottom: '100%',
              left: '50%',
              transform: 'translateX(-50%)',
              marginBottom: '5px',
              padding: '8px 12px',
              backgroundColor: '#343a40',
              color: 'white',
              borderRadius: '4px',
              fontSize: '12px',
              whiteSpace: 'nowrap',
              zIndex: 10
            }}>
              {tooltip.text}
            </div>
          )}
        </div>
        <input
          type="file"
          id="loadFile"
          style={{ display: 'none' }}
          onChange={handleLoadFromFile}
          accept=".json"
        />
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => document.getElementById('loadFile').click()}
            onMouseLeave={handleMouseLeave}
            style={{
              padding: '6px 12px',
              fontSize: '11px',
              backgroundColor: 'white',
              color: 'black',
              border: '1px solid transparent',
              boxShadow: '0 0 0 1px black',
              borderRadius: '12px',
              cursor: 'pointer',
              transition: 'background-color 0.2s',
              width: '100%'
            }}
            onMouseEnter={(e) => {
              e.target.style.backgroundColor = '#f0f0f0';
              handleMouseEnter('Load the form from saved file', 'loadBtn');
            }}
          >
            Load from File
          </button>
          {tooltip.visible && tooltip.id === 'loadBtn' && (
            <div style={{
              position: 'absolute',
              bottom: '100%',
              left: '50%',
              transform: 'translateX(-50%)',
              marginBottom: '5px',
              padding: '8px 12px',
              backgroundColor: '#343a40',
              color: 'white',
              borderRadius: '4px',
              fontSize: '12px',
              whiteSpace: 'nowrap',
              zIndex: 10
            }}>
              {tooltip.text}
            </div>
          )}
        </div>
      </div>
    </>
    </div>
  );
};

export default SidebarResults;
