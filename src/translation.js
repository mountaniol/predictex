import { useState, useEffect } from 'react';

export const useLoadQuestions = (language) => {
  const [questions, setQuestions] = useState([]);
  const [error, setError] = useState(null);
  const [labels, setLabels] = useState({ yes: 'Yes', no: 'No' });

  useEffect(() => {
    const loadQuestions = async () => {
      const fileName = language === 'en' ? 'questions2.json' : `questions2.${language}.json`;
      let questions;
      try {
        const res = await fetch(`/${fileName}`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        console.log(`Loaded ${fileName}`);
        const settings = Array.isArray(data) ? {} : (data.settings || {});
        questions = Array.isArray(data) ? data : (data.questions || []);
        setLabels(settings.labels || { yes: 'Yes', no: 'No' });
      } catch (err) {
        if (language !== 'en') {
          setError(`Could not load translation file ${fileName}. Falling back to default questions.`);
        }
        console.warn(`Falling back to /questions2.json because ${fileName} failed to load:`, err);
        const raw = await fetch('/questions2.json').then(r => r.json());
        const settings = Array.isArray(raw) ? {} : (raw.settings || {});
        questions = Array.isArray(raw) ? raw : (raw.questions || []);
        setLabels(settings.labels || { yes: 'Yes', no: 'No' });
      }
      setQuestions(questions);
    };

    loadQuestions();
  }, [language]);

  return { questions, labels, error };
};