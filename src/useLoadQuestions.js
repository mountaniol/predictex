import { useState, useEffect } from 'react';

const useLoadQuestions = (language) => {
  const [sections, setSections] = useState([]);
  const [aiPrompt, setAiPrompt] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        // 1) Attempt to load a pre-translated file
        const fileName = language === 'en'
          ? 'questions2.json'
          : `questions2.${language}.json`;
        let questions;
        const res = await fetch(`/${fileName}`);
        if (res.ok) {
          questions = await res.json();
        } else {
          // 2) Fallback to original JSON if no translation file is found
          questions = await fetch('/questions2.json').then(r => r.json());
        }

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

  return { sections, aiPrompt, apiKey, loading, error };
};

export default useLoadQuestions;