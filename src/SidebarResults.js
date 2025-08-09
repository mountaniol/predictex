import React, { useContext, useMemo } from 'react';
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
  const { sections, answers, scores, calculations } = useContext(AppContext);

  // Apply calculation rules to get computed scores
  const computedScores = useMemo(() => {
    if (!calculations || calculations.length === 0) {
      return scores;
    }

    // Import applyCalculations function logic
    const applyCalculations = (base, calcArr) => {
      const res = { ...base };
      const idRegex = /\b([A-Z][0-9]+)\b/g;

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
        riskLevel: 'Unknown',
        riskColor: '#999',
        riskDescription: 'No evaluations completed'
      };
    }

    const averageScore = allScores.reduce((sum, score) => sum + score, 0) / allScores.length;
    const totalQuestions = sections.reduce((sum, section) => sum + section.questions.length, 0);
    const evaluatedQuestions = allScores.length;

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
      riskLevel,
      riskColor,
      riskDescription
    };
  }, [computedScores, sections]);

  // Check if user has completed the evaluation
  const hasCompletedEvaluation = Object.keys(answers).length > 0 && 
    Object.keys(computedScores).length > 0;

  if (!hasCompletedEvaluation) {
    return null;
  }

  return (
    <div style={{
      position: 'sticky',
      top: 20,
      width: 280,
      backgroundColor: 'white',
      borderRadius: 12,
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      border: '1px solid #e9ecef',
      padding: 20,
      marginBottom: 20,
      maxHeight: 'calc(100vh - 40px)',
      overflowY: 'auto'
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

      {/* Overall Risk Assessment */}
      <div style={{
        textAlign: 'center',
        marginBottom: 20,
        padding: 16,
        backgroundColor: '#f8f9fa',
        borderRadius: 8,
        border: `2px solid ${overallStats.riskColor}`
      }}>
        <div style={{
          fontSize: 20,
          fontWeight: 700,
          color: overallStats.riskColor,
          marginBottom: 4
        }}>
          {overallStats.riskLevel}
        </div>
        <div style={{
          fontSize: 14,
          color: '#6c757d',
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
      </div>

      {/* Statistics */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 12,
        marginBottom: 20
      }}>
        <div style={{
          textAlign: 'center',
          padding: 12,
          backgroundColor: '#e3f2fd',
          borderRadius: 6
        }}>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#1976d2' }}>
            {overallStats.evaluatedQuestions}
          </div>
          <div style={{ fontSize: 12, color: '#6c757d' }}>
            Evaluated
          </div>
        </div>
        <div style={{
          textAlign: 'center',
          padding: 12,
          backgroundColor: '#f3e5f5',
          borderRadius: 6
        }}>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#7b1fa2' }}>
            {overallStats.totalQuestions}
          </div>
          <div style={{ fontSize: 12, color: '#6c757d' }}>
            Total
          </div>
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
              backgroundColor: '#f8f9fa',
              borderRadius: 6,
              border: `1px solid ${sectionRiskColor}`
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
      <div style={{
        marginTop: 16,
        padding: 12,
        backgroundColor: '#fff3cd',
        borderRadius: 6,
        border: '1px solid #ffeaa7'
      }}>
        <div style={{
          fontSize: 12,
          fontWeight: 600,
          color: '#856404',
          marginBottom: 6
        }}>
          Recommendation
        </div>
        <div style={{
          fontSize: 11,
          color: '#856404',
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
      </div>
    </div>
  );
};

export default SidebarResults;
