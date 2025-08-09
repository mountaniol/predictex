
import { useState, useEffect } from 'react';

/**
 * @brief Custom hook to load all question data and application settings.
 * @description This hook fetches the main `q4.json` file, which contains all sections,
 * questions, meta-questions, and AI configuration. It manages loading and error states.
 * This is the single source of truth for the application's question data.
 *
 * @returns {{
 *   sections: Array,
 *   metaQuestions: Array,
 *   loading: boolean,
 *   error: string,
 *   calculations: Array,
 *   aiPrompt: string,
 *   apiKey: string,
 *   labels: Object
 * }}
 */
const useLoadQuestions = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sections, setSections] = useState([]);
  const [metaQuestions, setMetaQuestions] = useState([]);
  const [aiPrompt, setAiPrompt] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [labels, setLabels] = useState({ yes: 'Yes', no: 'No' });
  const [calculations, setCalculations] = useState([]);

  useEffect(() => {
    const loadData = async () => {
      console.log('[useLoadQuestions] Starting data load...');
      setLoading(true);
      try {
        const response = await fetch('/questions/q4.json');
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`);
        }
        const data = await response.json();
        console.log('[useLoadQuestions] Data fetched successfully.', data);

        // Group questions by cluster_name to create sections
        const questions = data.questions || [];
        const clusterOrder = new Map();
        const groupedQuestions = questions.reduce((acc, question, index) => {
          const clusterName = question.cluster_name || 'Other';
          if (!acc[clusterName]) {
            acc[clusterName] = [];
            clusterOrder.set(clusterName, index); // Preserve original order of clusters
          }
          acc[clusterName].push(question);
          return acc;
        }, {});

        // Sort questions within each cluster by position
        Object.keys(groupedQuestions).forEach(clusterName => {
          groupedQuestions[clusterName].sort((a, b) => 
            (a.position_in_cluster || 0) - (b.position_in_cluster || 0)
          );
        });

        // Create the final sections array, respecting the original order
        const sectionsArray = Array.from(clusterOrder.entries())
          .sort((a, b) => a[1] - b[1])
          .map(([clusterName]) => ({
            title: clusterName,
            questions: groupedQuestions[clusterName]
          }));

        setSections(sectionsArray);
        setMetaQuestions(data.meta_questions || []);
        setCalculations(data.calculations || []);
        setAiPrompt(data.system_prompt || '');
        setApiKey(data.api_key || '');
        setLabels(data.labels || { yes: 'Yes', no: 'No' });
        console.log('[useLoadQuestions] State updated with loaded data.');

      } catch (e) {
        console.error('[useLoadQuestions] Error loading questions:', e);
        setError(`Failed to load or parse questions: ${e.message}`);
      } finally {
        setLoading(false);
        console.log('[useLoadQuestions] Loading finished.');
      }
    };

    loadData();
  }, []);

  return { sections, metaQuestions, loading, error, calculations, aiPrompt, apiKey, labels };
};

export default useLoadQuestions;