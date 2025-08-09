import React, { useState, useEffect } from "react";
import useLoadQuestions from "./useLoadQuestions";
import LanguageSelector from "./LanguageSelector";
import "./App.css";
import QuestionSection from "./QuestionSection";

import SidebarResults from "./SidebarResults";
import Header from "./Header";
import Footer from "./Footer";
import { useCallback } from "react";

/**
 * @brief React Context for global application state management
 * 
 * Provides centralized state management for the QnA Evaluator application.
 * Contains all shared state including questions, answers, scores, and configuration.
 * 
 * @context {Object} AppContext - Global application context
 * @context {Array} sections - Grouped questions by cluster/section
 * @context {Array} metaQuestions - Meta questions for basic information
 * @context {string} aiPrompt - System prompt for AI evaluation
 * @context {string} apiKey - API endpoint URL for evaluation
 * @context {Object} labels - UI labels for yes/no options
 * @context {boolean} loading - Loading state for questions
 * @context {string} error - Error message if loading fails
 * @context {Array} calculations - Calculation rules for derived scores
 * @context {string} currentLanguage - Current language setting
 * @context {Object} answers - User answers to questions
 * @context {Function} setAnswers - Function to update answers
 * @context {Object} scores - AI evaluation scores
 * @context {Function} setScores - Function to update scores
 */
export const AppContext = React.createContext(null);

/**
 * @brief Main application component for QnA Evaluator
 * 
 * Root component that orchestrates the entire application. Manages global state
 * through React Context, handles language switching, and renders the main UI
 * components including header, language selector, question sections, and footer.
 * 
 * @function App
 * @returns {JSX.Element} The complete application UI
 * 
 * @state {string} currentLanguage - Current language setting (en/ru/de)
 * @state {Object} answers - User answers to all questions
 * @state {Object} scores - AI evaluation scores for questions
 * 
 * @dependencies {useLoadQuestions} - Custom hook for loading questions and configuration
 * @dependencies {AppContext} - Global state context provider
 * @dependencies {LanguageSelector} - Component for language switching
 * @dependencies {QuestionSection} - Main questions rendering component
 * @dependencies {Header} - Application header component
 * @dependencies {Footer} - Application footer component
 * 
 * @architecture {Frontend} - React-based single page application
 * @architecture {State Management} - React Context API for global state
 * @architecture {Data Flow} - Top-down props, bottom-up callbacks
 * @architecture {Internationalization} - Multi-language support via language switching
 * 
 * @role {Orchestrator} - Coordinates all application components and state
 * @role {State Provider} - Provides global state through Context API
 * @role {Layout Manager} - Manages overall application layout and styling
 */
function App() {
  const [currentLanguage, setCurrentLanguage] = useState("en");
  
  const initialQuestionSetId = new URLSearchParams(window.location.search).get('q') || 'q4';
  const { 
    loading, error, questionSetId, setQuestionSetId, sections, metaQuestions, calculations, labels
  } = useLoadQuestions(initialQuestionSetId);
  
  const [answers, setAnswers] = useState({});
  const [scores, setScores] = useState({});
  const [questionStates, setQuestionStates] = useState({});
  const [explanations, setExplanations] = useState({});
  const [metaSummaries, setMetaSummaries] = useState({});

  useEffect(() => {
    if (!questionSetId) return;
    try {
      const savedAnswers = localStorage.getItem(`qna-evaluator-answers-${questionSetId}`);
      setAnswers(savedAnswers ? JSON.parse(savedAnswers) : {});

      const savedScores = localStorage.getItem(`qna-evaluator-scores-${questionSetId}`);
      setScores(savedScores ? JSON.parse(savedScores) : {});

      const storedStates = localStorage.getItem(`qna-evaluator-questionStates-${questionSetId}`);
      setQuestionStates(storedStates ? JSON.parse(storedStates) : {});

      const savedExplanations = localStorage.getItem(`qna-evaluator-explanations-${questionSetId}`);
      setExplanations(savedExplanations ? JSON.parse(savedExplanations) : {});

      const savedSummaries = localStorage.getItem(`qna-evaluator-metaSummaries-${questionSetId}`);
      setMetaSummaries(savedSummaries ? JSON.parse(savedSummaries) : {});

    } catch (error) {
      console.warn('Failed to load data from localStorage on question set change:', error);
    }
  }, [questionSetId]);

  // A new function to dynamically load a question set and apply new state
  const loadAndApplyState = useCallback((newState) => {
    if (newState.questionSetId) {
      // Trigger the data load for the new question set
      setQuestionSetId(newState.questionSetId);
      
      // We need a way to apply the state AFTER the new questions are loaded.
      // A simple (but not perfect) way is to use a timeout. A better way would
      // be a more robust state machine, but this is a good first step.
      setTimeout(() => {
        setAnswers(newState.answers || {});
        setScores(newState.scores || {});
        setQuestionStates(newState.questionStates || {});
        setExplanations(newState.explanations || {});
        setMetaSummaries(newState.metaSummaries || {});
        console.log(`State for ${newState.questionSetId} has been applied.`);
      }, 500); // Wait 500ms for questions to load
    }
  }, [setQuestionSetId]);


  // Log context values
  useEffect(() => {
    console.log('[App.js] Context Provider value updated:', {
      loading,
      sectionsCount: sections?.length,
      metaQuestionsCount: metaQuestions?.length,
      answersCount: Object.keys(answers).length,
      scoresCount: Object.keys(scores).length,
      statesCount: Object.keys(questionStates).length,
      explanationsCount: Object.keys(explanations).length,
      metaSummariesCount: Object.keys(metaSummaries).length,
    });
  }, [loading, sections, metaQuestions, answers, scores, questionStates, explanations, metaSummaries]);

  // Save data to localStorage whenever it changes
  useEffect(() => {
    if (questionSetId) {
      try {
        localStorage.setItem(`qna-evaluator-answers-${questionSetId}`, JSON.stringify(answers));
      } catch (error) {
        console.warn('Failed to save answers to localStorage:', error);
      }
    }
  }, [answers, questionSetId]);

  useEffect(() => {
    if (questionSetId) {
      try {
        localStorage.setItem(`qna-evaluator-scores-${questionSetId}`, JSON.stringify(scores));
      } catch (error) {
        console.warn('Failed to save scores to localStorage:', error);
      }
    }
  }, [scores, questionSetId]);

  useEffect(() => {
    if (questionSetId) {
      try {
        localStorage.setItem(`qna-evaluator-questionStates-${questionSetId}`, JSON.stringify(questionStates));
      } catch (error) {
        console.warn('Failed to save question states to localStorage:', error);
      }
    }
  }, [questionStates, questionSetId]);

  useEffect(() => {
    if (questionSetId) {
      try {
        localStorage.setItem(`qna-evaluator-explanations-${questionSetId}`, JSON.stringify(explanations));
      } catch (error) {
        console.warn('Failed to save explanations to localStorage:', error);
      }
    }
  }, [explanations, questionSetId]);

  useEffect(() => {
    if (questionSetId) {
      try {
        localStorage.setItem(`qna-evaluator-metaSummaries-${questionSetId}`, JSON.stringify(metaSummaries));
      } catch (error) {
        console.warn('Failed to save metaSummaries to localStorage:', error);
      }
    }
  }, [metaSummaries, questionSetId]);

  // Add event listener to save data before page unload
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (questionSetId) {
        try {
          localStorage.setItem(`qna-evaluator-answers-${questionSetId}`, JSON.stringify(answers));
          localStorage.setItem(`qna-evaluator-scores-${questionSetId}`, JSON.stringify(scores));
          localStorage.setItem(`qna-evaluator-questionStates-${questionSetId}`, JSON.stringify(questionStates));
          localStorage.setItem(`qna-evaluator-explanations-${questionSetId}`, JSON.stringify(explanations));
          localStorage.setItem(`qna-evaluator-metaSummaries-${questionSetId}`, JSON.stringify(metaSummaries));
        } catch (error) {
          console.warn('Failed to save data before unload:', error);
        }
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [answers, scores, questionStates, explanations, metaSummaries, questionSetId]);

  return (
    <AppContext.Provider value={{
      questionSetId,
      sections,
      metaQuestions,
      loading,
      error,
      calculations,
      currentLanguage,
      answers,
      setAnswers,
      scores,
      setScores,
      questionStates,
      setQuestionStates,
      explanations,
      setExplanations,
      metaSummaries,
      setMetaSummaries,
      labels,
      loadAndApplyState // Expose the new function
    }}>
      <div style={{
        minHeight: "100vh",
        background: "#f8f9fb",
        fontFamily: "'Segoe UI', 'Roboto', 'Arial', sans-serif",
        padding: 0,
        margin: 0
      }}>
        <div style={{
          maxWidth: 1200,
          margin: "0 auto",
          padding: "32px 16px 0 16px"
        }}>
          <Header />
          <LanguageSelector
            currentLanguage={currentLanguage}
            onChange={setCurrentLanguage}
            translating={loading}
          />

          {metaQuestions && metaQuestions.length > 0 && (
            <h2 style={{
              fontSize: '24px',
              fontWeight: 'bold',
              marginTop: '20px',
              marginBottom: '20px',
              color: '#2c3e50',
              // Position the title as if it's in the second column
              marginLeft: '304px', // 280px (sidebar) + 24px (gap)
            }}>
              Basic Information
            </h2>
          )}

          <div style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '24px',
          }}>
            {/* Column 1: Sticky Sidebar */}
            <div style={{
              width: '280px',
              flexShrink: 0, // Prevents the sidebar from shrinking
              position: 'sticky',
              top: '20px',
            }}>
              <SidebarResults />
            </div>

            {/* Column 2: Main Content */}
            <div style={{
              flex: 1 // Takes up the remaining space
            }}>
              <QuestionSection />
            </div>
          </div>
        </div>
        <Footer />
      </div>
    </AppContext.Provider>
  );
}

export default App;