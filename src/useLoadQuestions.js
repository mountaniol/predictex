
import { useState, useEffect } from 'react';
import { createDependencyReport } from './dependencyValidator.js';

/**
 * @brief Custom hook to load all question data and application settings.
 * @description This hook fetches the main `q4.json` file, which contains all sections,
 * questions, meta-questions, and AI configuration. It manages loading and error states.
 * This is the single source of truth for the application's question data.
 *
 * @returns {{
 *   sections: Array,
 *   loading: boolean,
 *   error: string,
 *   calculations: Array,
 *   aiPrompt: string,
 *   apiKey: string,
 *   labels: Object
 * }}
 */
const useLoadQuestions = (questionSetId) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sections, setSections] = useState([]);
  const [calculations, setCalculations] = useState(null);
  const [labels, setLabels] = useState(null);
  const [finalAnalysisConfig, setFinalAnalysisConfig] = useState(null);

  useEffect(() => {
    if (!questionSetId) {
      setLoading(false);
      return;
    }

    const loadData = async () => {
      console.log(`[useLoadQuestions] Starting data load for ${questionSetId}...`);
      setLoading(true);
      try {
        const response = await fetch(`/questions/${questionSetId}.json`);
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`);
        }
        const data = await response.json();
        console.log('[useLoadQuestions] Data fetched successfully.', data);

        // Group questions by cluster_name
        const sectionsMap = {};
        data.questions.forEach(q => {
          const clusterName = q.cluster_name || 'Other';
          if (!sectionsMap[clusterName]) {
            sectionsMap[clusterName] = {
              title: clusterName,
              questions: []
            };
          }
          sectionsMap[clusterName].questions.push(q);
        });

        const sections = Object.values(sectionsMap);
        sections.sort((a, b) => a.position - b.position);
        sections.forEach(s => s.questions.sort((a,b) => a.position_in_cluster - b.position_in_cluster));
        
        // This was the source of the infinite loop. The hook should not
        // change its own trigger ID based on the content of the loaded file.
        // The questionSetId is the source of truth for which file to load.
        // setQuestionSetId(data.version || 'unknown'); 
        
        // Validate dependency graph before setting sections
        console.log('[useLoadQuestions] Validating dependency graph...');
        const dependencyReport = createDependencyReport(data.questions);
        
        if (!dependencyReport.validation.isValid) {
          console.error('[useLoadQuestions] Dependency validation failed:', dependencyReport);
          const errorMessages = dependencyReport.validation.errors.join('; ');
          throw new Error(`Dependency validation failed: ${errorMessages}`);
        }
        
        if (dependencyReport.validation.warnings.length > 0) {
          console.warn('[useLoadQuestions] Dependency warnings:', dependencyReport.validation.warnings);
        }
        
        console.log('[useLoadQuestions] Dependency validation passed:', {
          totalQuestions: dependencyReport.validation.stats.totalQuestions,
          questionsWithDeps: dependencyReport.validation.stats.questionsWithDeps,
          maxDepth: dependencyReport.validation.stats.maxDepthFound,
          forwardReferences: dependencyReport.validation.stats.forwardReferences
        });

        setSections(sections);
        setCalculations(data.calculations || null);
        setLabels(data.settings.labels || null);
        setFinalAnalysisConfig(data.final_analysis_config || null);

      } catch (error) {
        console.error("Error loading or parsing questions:", error);
        setError("Could not load question data.");
      } finally {
        setLoading(false);
        console.log('[useLoadQuestions] Loading finished.');
      }
    };

    loadData();
  }, [questionSetId]);

  return { loading, error, sections, calculations, labels, finalAnalysisConfig };
};

export default useLoadQuestions;