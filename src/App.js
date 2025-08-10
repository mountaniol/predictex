import React, { useState, useEffect, useRef, useLayoutEffect } from "react";
import useLoadQuestions from "./useLoadQuestions";
import LanguageSelector from "./LanguageSelector";
import "./App.css";
import QuestionSection from "./QuestionSection";

import SidebarResults from "./SidebarResults";
import Header from "./Header";
import Footer from "./Footer";
import FinalReport from "./FinalReport";

/**
 * @brief React Context for global application state management
 * 
 * Provides centralized state management for the QnA Evaluator application.
 * Contains all shared state including questions, answers, scores, and configuration.
 * 
 * @context {Object} AppContext - Global application context
 * @context {Array} sections - Grouped questions by cluster/section
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
    loading, error, questionSetId, sections, calculations, labels, finalAnalysisConfig
  } = useLoadQuestions(initialQuestionSetId);
  
  const [answers, setAnswers] = useState(() => {
    const saved = localStorage.getItem(`qna-evaluator-answers-${initialQuestionSetId}`);
    return saved ? JSON.parse(saved) : {};
  });
  const [scores, setScores] = useState(() => {
    const saved = localStorage.getItem(`qna-evaluator-scores-${initialQuestionSetId}`);
    return saved ? JSON.parse(saved) : {};
  });
  const [questionStates, setQuestionStates] = useState(() => {
    const saved = localStorage.getItem(`qna-evaluator-questionStates-${initialQuestionSetId}`);
    return saved ? JSON.parse(saved) : {};
  });
  const [explanations, setExplanations] = useState(() => {
    const saved = localStorage.getItem(`qna-evaluator-explanations-${initialQuestionSetId}`);
    return saved ? JSON.parse(saved) : {};
  });

  const [finalReport, setFinalReport] = useState(() => {
    const saved = localStorage.getItem(`qna-evaluator-finalReport-${initialQuestionSetId}`);
    return saved ? saved : null;
  });

  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [highlightUnanswered, setHighlightUnanswered] = useState(false);

  const topOfContentRef = useRef(null);
  const finalReportRef = useRef(null);
  const [contentOffset, setContentOffset] = useState(0);

  useLayoutEffect(() => {
    if (topOfContentRef.current) {
      const newHeight = topOfContentRef.current.offsetHeight;
      if (newHeight !== contentOffset) {
        setContentOffset(newHeight);
      }
    }
  }, [loading, contentOffset]); // Re-measure when loading state changes

  useEffect(() => {
    if (!questionSetId) return;
    try {
      const savedAnswers = localStorage.getItem(`qna-evaluator-answers-${questionSetId}`);
      if (savedAnswers) setAnswers(JSON.parse(savedAnswers));

      const savedScores = localStorage.getItem(`qna-evaluator-scores-${questionSetId}`);
      if (savedScores) setScores(JSON.parse(savedScores));

      const storedStates = localStorage.getItem(`qna-evaluator-questionStates-${questionSetId}`);
      if (storedStates) setQuestionStates(JSON.parse(storedStates));

      const savedExplanations = localStorage.getItem(`qna-evaluator-explanations-${questionSetId}`);
      if (savedExplanations) setExplanations(JSON.parse(savedExplanations));

      const savedReport = localStorage.getItem(`qna-evaluator-finalReport-${questionSetId}`);
      if (savedReport) setFinalReport(savedReport);

    } catch (error) {
      console.warn('Failed to load data from localStorage on question set change:', error);
    }
  }, [questionSetId]);

  useEffect(() => {
    if (questionSetId) {
      if (finalReport) {
        localStorage.setItem(`qna-evaluator-finalReport-${questionSetId}`, finalReport);
      } else {
        localStorage.removeItem(`qna-evaluator-finalReport-${questionSetId}`);
      }
    }
  }, [finalReport, questionSetId]);

  // Log context values
  useEffect(() => {
  }, [loading, sections, answers, scores, questionStates, explanations]);

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
    if (finalReport) {
      localStorage.setItem('finalReport', finalReport);
    } else {
      localStorage.removeItem('finalReport');
    }
  }, [finalReport]);

  // Add event listener to save data before page unload
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (questionSetId) {
        try {
          localStorage.setItem(`qna-evaluator-answers-${questionSetId}`, JSON.stringify(answers));
          localStorage.setItem(`qna-evaluator-scores-${questionSetId}`, JSON.stringify(scores));
          localStorage.setItem(`qna-evaluator-questionStates-${questionSetId}`, JSON.stringify(questionStates));
          localStorage.setItem(`qna-evaluator-explanations-${questionSetId}`, JSON.stringify(explanations));
          if (finalReport) {
            localStorage.setItem('finalReport', finalReport);
          } else {
            localStorage.removeItem('finalReport');
          }
        } catch (error) {
          console.warn('Failed to save data before unload:', error);
        }
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [answers, scores, questionStates, explanations, questionSetId, finalReport]);

  return (
    <AppContext.Provider
      value={{
        questionSetId,
        sections,
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
        labels,
        finalReport,
        setFinalReport,
        isGeneratingReport,
        setIsGeneratingReport,
        finalAnalysisConfig,
        finalReportRef,
        highlightUnanswered,
        setHighlightUnanswered
      }}
    >
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
          padding: "32px 16px 0 16px",
          display: 'flex',
          alignItems: 'flex-start',
          gap: '24px'
        }}>
          {/* Column 1: Sticky Sidebar */}
          <div style={{
            width: '280px',
            flexShrink: 0,
            position: 'sticky',
            top: '20px',
            paddingTop: `${contentOffset}px` // Dynamically apply the measured height
          }}>
            <SidebarResults />
          </div>

          {/* Column 2: Main Content */}
          <div style={{
            flex: 1
          }}>
            <div ref={topOfContentRef}> {/* This is the measurement wrapper */}
              <Header />
              <LanguageSelector
                currentLanguage={currentLanguage}
                onChange={setCurrentLanguage}
                translating={loading}
              />
            </div>
            <QuestionSection />
            <div ref={finalReportRef}>
              <FinalReport />
            </div>
          </div>
        </div>
        <Footer />
      </div>
    </AppContext.Provider>
  );
}

export default App;