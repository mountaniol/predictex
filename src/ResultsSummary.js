import React, { useContext, useMemo } from 'react';
import { AppContext } from './App';

/**
 * @brief Results summary component for completed evaluations
 * 
 * Displays comprehensive evaluation results including individual scores,
 * calculated scores, overall assessment, and risk categorization.
 * Shows when user has completed answering and evaluating all questions.
 * 
 * @function ResultsSummary
 * @returns {JSX.Element} Complete results summary interface
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
 * @dependencies {applyCalculations} - Function to apply calculation rules
 * 
 * @architecture {Component Hierarchy} - Results display component
 * @architecture {Data Processing} - Computes overall statistics and risk levels
 * @architecture {Visual Design} - Clean, informative results presentation
 * 
 * @role {Results Display} - Shows comprehensive evaluation results
 * @role {Statistics Calculator} - Computes overall risk statistics
 * @role {Risk Assessor} - Categorizes overall risk level
 * @role {Data Visualizer} - Presents results in user-friendly format
 */
const ResultsSummary = () => {
  const { sections, answers, scores, calculations, questionStates } = useContext(AppContext);

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
      riskDescription = 'Excellent condition, low risk';
    } else if (averageScore >= 60) {
      riskLevel = 'Moderate Risk';
      riskColor = '#ffc107';
      riskDescription = 'Good condition with some concerns';
    } else if (averageScore >= 40) {
      riskLevel = 'High Risk';
      riskColor = '#fd7e14';
      riskDescription = 'Significant concerns identified';
    } else if (averageScore >= 20) {
      riskLevel = 'Very High Risk';
      riskColor = '#dc3545';
      riskDescription = 'Critical issues, proceed with extreme caution';
    } else {
      riskLevel = 'Critical Risk';
      riskColor = '#721c24';
      riskDescription = 'Extremely high risk, do not proceed';
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

  // Check if user has completed the evaluation
  const hasCompletedEvaluation = Object.keys(answers).length > 0 && 
    Object.keys(computedScores).length > 0;

  if (!hasCompletedEvaluation) {
    return null;
  }

  // Only show on mobile devices
  const isMobile = window.innerWidth < 1024;
  if (!isMobile) {
    return null;
  }

  return (
    <div style={{
      marginTop: 40,
      padding: 24,
      backgroundColor: 'white',
      borderRadius: 12,
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      border: '1px solid #e9ecef'
    }}>
      <h2 style={{
        margin: '0 0 24px 0',
        fontSize: 24,
        fontWeight: 600,
        color: '#2c3e50',
        textAlign: 'center'
      }}>
        Evaluation Results Summary
      </h2>

      {/* Overall Risk Assessment */}
      <div style={{
        textAlign: 'center',
        marginBottom: 32,
        padding: 20,
        backgroundColor: '#f8f9fa',
        borderRadius: 8,
        border: `2px solid ${overallStats.riskColor}`
      }}>
        <div style={{
          fontSize: 28,
          fontWeight: 700,
          color: overallStats.riskColor,
          marginBottom: 8
        }}>
          {overallStats.riskLevel}
        </div>
        <div style={{
          fontSize: 18,
          color: '#6c757d',
          marginBottom: 12
        }}>
          {overallStats.riskDescription}
        </div>
        <div style={{
          fontSize: 36,
          fontWeight: 700,
          color: overallStats.riskColor
        }}>
          {overallStats.averageScore}/100
        </div>
        <div style={{
          fontSize: 14,
          color: '#6c757d',
          marginTop: 8
        }}>
          Average Score
        </div>
      </div>

      {/* Statistics */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: 16,
        marginBottom: 32
      }}>
        <div style={{
          textAlign: 'center',
          padding: 16,
          backgroundColor: '#e3f2fd',
          borderRadius: 8
        }}>
          <div style={{ fontSize: 24, fontWeight: 600, color: '#1976d2' }}>
            {overallStats.evaluatedQuestions}
          </div>
          <div style={{ fontSize: 14, color: '#6c757d' }}>
            Questions Evaluated
          </div>
        </div>
        <div style={{
          textAlign: 'center',
          padding: 16,
          backgroundColor: '#f3e5f5',
          borderRadius: 8
        }}>
          <div style={{ fontSize: 24, fontWeight: 600, color: '#7b1fa2' }}>
            {overallStats.totalQuestions}
          </div>
          <div style={{ fontSize: 14, color: '#6c757d' }}>
            Total Questions
          </div>
        </div>
        <div style={{
          textAlign: 'center',
          padding: 16,
          backgroundColor: '#e8f5e8',
          borderRadius: 8
        }}>
          <div style={{ fontSize: 24, fontWeight: 600, color: '#27ae60' }}>
            {overallStats.fullyEvaluated}
          </div>
          <div style={{ fontSize: 14, color: '#6c757d' }}>
            Fully Evaluated
          </div>
        </div>
        <div style={{
          textAlign: 'center',
          padding: 16,
          backgroundColor: '#fff3cd',
          borderRadius: 8
        }}>
          <div style={{ fontSize: 24, fontWeight: 600, color: '#f39c12' }}>
            {overallStats.partlyEvaluated}
          </div>
          <div style={{ fontSize: 14, color: '#6c757d' }}>
            Partly Evaluated
          </div>
        </div>
        <div style={{
          textAlign: 'center',
          padding: 16,
          backgroundColor: '#e8f5e8',
          borderRadius: 8
        }}>
          <div style={{ fontSize: 24, fontWeight: 600, color: '#388e3c' }}>
            {Math.round((overallStats.evaluatedQuestions / overallStats.totalQuestions) * 100)}%
          </div>
          <div style={{ fontSize: 14, color: '#6c757d' }}>
            Completion Range
          </div>
        </div>
      </div>

      {/* Individual Scores by Section */}
      <div>
        <h3 style={{
          margin: '0 0 16px 0',
          fontSize: 18,
          fontWeight: 600,
          color: '#2c3e50'
        }}>
          Scores by Section
        </h3>
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
              marginBottom: 16,
              padding: 16,
              backgroundColor: '#f8f9fa',
              borderRadius: 8,
              border: `1px solid ${sectionRiskColor}`
            }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <div style={{
                    fontSize: 16,
                    fontWeight: 600,
                    color: '#2c3e50'
                  }}>
                    {section.title}
                  </div>
                  <div style={{
                    fontSize: 14,
                    color: '#6c757d'
                  }}>
                    {sectionScores.length} questions evaluated
                  </div>
                </div>
                <div style={{
                  fontSize: 20,
                  fontWeight: 700,
                  color: sectionRiskColor
                }}>
                  {Math.round(sectionAverage * 10) / 10}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Recommendations */}
      <div style={{
        marginTop: 32,
        padding: 20,
        backgroundColor: '#fff3cd',
        borderRadius: 8,
        border: '1px solid #ffeaa7'
      }}>
        <h3 style={{
          margin: '0 0 12px 0',
          fontSize: 16,
          fontWeight: 600,
          color: '#856404'
        }}>
          Recommendations
        </h3>
        <div style={{
          fontSize: 14,
          color: '#856404',
          lineHeight: 1.5
        }}>
          {overallStats.averageScore >= 80 ? (
            <p>This business appears to be in excellent condition with low risk factors. Consider proceeding with standard due diligence procedures.</p>
          ) : overallStats.averageScore >= 60 ? (
            <p>This business shows good fundamentals with some areas of concern. Conduct thorough due diligence focusing on identified risk areas.</p>
          ) : overallStats.averageScore >= 40 ? (
            <p>Significant risk factors have been identified. Consider additional investigation and risk mitigation strategies before proceeding.</p>
          ) : overallStats.averageScore >= 20 ? (
            <p>Critical risk factors present. Proceed with extreme caution and consider professional risk assessment before any investment.</p>
          ) : (
            <p>Extremely high risk factors identified. Strongly recommend against proceeding without major risk mitigation and professional consultation.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default ResultsSummary;
