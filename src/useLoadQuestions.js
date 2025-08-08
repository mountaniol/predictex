
import { useState, useEffect } from 'react';

const loadJson = async (fileName) => {
  try {
    const response = await fetch(`/${fileName}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    
    // Handle new q3.json format
    if (data.version && data.meta_questions) {
      console.log(`[loadJson] loaded q3 format with ${data.meta_questions.length} meta questions and ${data.questions.length} regular questions`);
      return {
        meta_questions: data.meta_questions || [],
        questions: data.questions || [],
        settings: data.settings || {},
        calculations: data.calculations || []
      };
    }
    
    // Handle legacy format
    const settings = Array.isArray(data) ? {} : (data.settings || {});
    const questions = Array.isArray(data) ? data : (data.questions || []);
    const calculations = Array.isArray(data) ? [] : (data.calculations || []);
    console.log(`[loadJson] loaded legacy format with ${questions.length} questions and ${calculations.length} calculation rules`);
    return { questions, settings, calculations, meta_questions: [] };
  } catch (error) {
    console.error(`[loadJson] Error loading ${fileName}:`, error);
    throw error;
  }
};

const useLoadQuestions = (currentLanguage) => {
  const [sections, setSections] = useState([]);
  const [metaQuestions, setMetaQuestions] = useState([]);
  const [aiPrompt, setAiPrompt] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [labels, setLabels] = useState({});
  const [calculations, setCalculations] = useState([]);

  useEffect(() => {
    const loadQuestions = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // Try to load q3.json first (new format)
        let fileName = 'q3.json';
        if (currentLanguage !== 'en') {
          fileName = `q3.${currentLanguage}.json`;
        }
        
        let metaQuestions = [];
        let questions = [];
        let settings = {};
        let calculations = [];
        
        try {
          const result = await loadJson(fileName);
          metaQuestions = result.meta_questions || [];
          questions = result.questions || [];
          settings = result.settings || {};
          calculations = result.calculations || [];
        } catch (err) {
          console.warn(err.message + ' – falling back to legacy format');
          // Fallback to legacy format
          fileName = currentLanguage === 'en' ? 'questions2.json' : `questions2.${currentLanguage}.json`;
          const result = await loadJson(fileName);
          questions = result.questions || [];
          settings = result.settings || {};
          calculations = result.calculations || [];
        }

        // Group questions by cluster_name
        const groupedQuestions = questions.reduce((acc, question) => {
          const clusterName = question.cluster_name || 'Other';
          if (!acc[clusterName]) {
            acc[clusterName] = [];
          }
          acc[clusterName].push(question);
          return acc;
        }, {});

        // Sort questions within each cluster by position_in_cluster
        Object.keys(groupedQuestions).forEach(clusterName => {
          groupedQuestions[clusterName].sort((a, b) => 
            (a.position_in_cluster || 0) - (b.position_in_cluster || 0)
          );
        });

        // Convert to sections format
        const sectionsArray = Object.keys(groupedQuestions).map(clusterName => ({
          title: clusterName,
          questions: groupedQuestions[clusterName]
        }));

        setSections(sectionsArray);
        setMetaQuestions(metaQuestions);
        setLabels(settings.labels || { yes: 'Yes', no: 'No' });
        setCalculations(calculations);
        console.log(`[useLoadQuestions] loaded ${metaQuestions.length} meta questions, ${questions.length} regular questions, and ${calculations.length} calculation rules`);
        
        // Load AI prompt
        try {
          const promptResponse = await fetch('/ai-prompt.txt');
          if (promptResponse.ok) {
            const promptText = await promptResponse.text();
            setAiPrompt(promptText.trim());
          } else {
            setAiPrompt('You are an expert business evaluator. Analyze the provided information and return a score from 0 to 100, where 0 is extremely high risk and 100 is extremely low risk.');
          }
        } catch (promptError) {
          console.warn('Failed to load AI prompt:', promptError);
          setAiPrompt('You are an expert business evaluator. Analyze the provided information and return a score from 0 to 100, where 0 is extremely high risk and 100 is extremely low risk.');
        }
        
        // Use Vercel API endpoint
        setApiKey('/api/simple-evaluate');
      } catch (err) {
        console.error('Failed to load questions:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadQuestions();
  }, [currentLanguage]);

  return { sections, metaQuestions, aiPrompt, apiKey, loading, error, labels, calculations };
};

export default useLoadQuestions;