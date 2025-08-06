import { useState, useEffect } from 'react';

export const useLoadQuestions = (language) => {
  const [questions, setQuestions] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadQuestions = async () => {
      const fileName = language === 'en' ? 'questions2.json' : `questions2.${language}.json`;
      let questions;
      try {
        const res = await fetch(`/${fileName}`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        questions = await res.json();
        console.log(`Loaded ${fileName}`);
      } catch (err) {
        if (language !== 'en') {
          setError(`Could not load translation file ${fileName}. Falling back to default questions.`);
        }
        console.warn(`Falling back to /questions2.json because ${fileName} failed to load:`, err);
        questions = await fetch('/questions2.json').then(r => r.json());
      }
      setQuestions(questions);
    };

    loadQuestions();
  }, [language]);

  return { questions, error };
};