
import { useState, useEffect } from 'react';

// Reusable JSON loader: returns { questions, settings }
const loadJson = async (filename) => {
  const res = await fetch(`/${filename}`);
  if (!res.ok) {
    throw new Error(`File ${filename} not found (HTTP ${res.status})`);
  }
  const data = await res.json();

  const settings = Array.isArray(data) ? {} : (data.settings || {});
  const questions = Array.isArray(data) ? data : (data.questions || []);

  return { questions, settings };
};

const useLoadQuestions = (language) => {
  const [sections, setSections] = useState([]);
  const [aiPrompt, setAiPrompt] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [labels, setLabels] = useState({ yes: 'Yes', no: 'No' });

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        // 1) Attempt to load a pre-translated file
        const fileName = language === 'en'
          ? 'questions2.json'
          : `questions2.${language}.json`;
        let questions = [];
        let settings  = {};
        try {
          ({ questions, settings } = await loadJson(fileName));
        } catch (err) {
          console.warn(err.message + ' – falling back to default file');
          ({ questions, settings } = await loadJson('questions2.json'));
        }
        // Initialize labels (and other future settings)
        setLabels(settings.labels || { yes: 'Yes', no: 'No' });

        // Group by cluster_name
        const map = {};
        questions.forEach(q => {
          map[q.cluster_name] = map[q.cluster_name] || [];
          map[q.cluster_name].push(q);
        });
        const sectionArr = Object.entries(map).map(([name, qs]) => ({
          section: name,
          questions: qs.sort((a, b) => a.position_in_cluster - b.position_in_cluster),
        }));
        setSections(sectionArr);

        // Load aiPrompt
        const promptTxt = await fetch('/aiprompt.txt').then(r => r.text());
        setAiPrompt(promptTxt);

        // Load API key
        let key = process.env.REACT_APP_GPT_KEY;
        if (!key) {
          key = await fetch('/key.txt').then(r => r.text());
        }
        setApiKey(key.trim());
      } catch (e) {
        console.error('Error loading questions:', e);
        setError('Failed to load questions');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [language]);

  return { sections, aiPrompt, apiKey, loading, error, labels };
};

export default useLoadQuestions;