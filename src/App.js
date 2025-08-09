import React, { useState, useEffect } from "react";
import useLoadQuestions from "./useLoadQuestions";
import LanguageSelector from "./LanguageSelector";
import "./App.css";
import QuestionSection from "./QuestionSection";

import SidebarResults from "./SidebarResults";
import Header from "./Header";
import Footer from "./Footer";

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
  const { sections, metaQuestions, loading, error, calculations, aiPrompt, apiKey, labels } = useLoadQuestions();
  
  // Load saved data from localStorage on component mount
  const [answers, setAnswers] = useState(() => {
    try {
      const savedAnswers = localStorage.getItem('qna-evaluator-answers');
      return savedAnswers ? JSON.parse(savedAnswers) : {};
    } catch (error) {
      console.warn('Failed to load answers from localStorage:', error);
      return {};
    }
  });
  
  const [scores, setScores] = useState(() => {
    try {
      const savedScores = localStorage.getItem('qna-evaluator-scores');
      return savedScores ? JSON.parse(savedScores) : {};
    } catch (error) {
      console.warn('Failed to load scores from localStorage:', error);
      return {};
    }
  });
  
  const [questionStates, setQuestionStates] = useState(() => {
    try {
      const storedStates = localStorage.getItem('qna-evaluator-questionStates');
      return storedStates ? JSON.parse(storedStates) : {};
    } catch (e) {
      console.error("Failed to parse question states from localStorage", e);
      return {};
    }
  });

  // Log context values
  useEffect(() => {
    console.log('[App.js] Context Provider value updated:', {
      loading,
      sectionsCount: sections?.length,
      metaQuestionsCount: metaQuestions?.length,
      answersCount: Object.keys(answers).length,
      scoresCount: Object.keys(scores).length,
      statesCount: Object.keys(questionStates).length,
    });
  }, [loading, sections, metaQuestions, answers, scores, questionStates]);

  // Save data to localStorage whenever it changes
  useEffect(() => {
    try {
      localStorage.setItem('qna-evaluator-answers', JSON.stringify(answers));
    } catch (error) {
      console.warn('Failed to save answers to localStorage:', error);
    }
  }, [answers]);

  useEffect(() => {
    try {
      localStorage.setItem('qna-evaluator-scores', JSON.stringify(scores));
    } catch (error) {
      console.warn('Failed to save scores to localStorage:', error);
    }
  }, [scores]);

  useEffect(() => {
    try {
      localStorage.setItem('qna-evaluator-questionStates', JSON.stringify(questionStates));
    } catch (error) {
      console.warn('Failed to save question states to localStorage:', error);
    }
  }, [questionStates]);

  // Add event listener to save data before page unload
  useEffect(() => {
    const handleBeforeUnload = () => {
      try {
        localStorage.setItem('qna-evaluator-answers', JSON.stringify(answers));
        localStorage.setItem('qna-evaluator-scores', JSON.stringify(scores));
        localStorage.setItem('qna-evaluator-questionStates', JSON.stringify(questionStates));
      } catch (error) {
        console.warn('Failed to save data before unload:', error);
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [answers, scores, questionStates]);

  return (
    <AppContext.Provider value={{
      sections,
      metaQuestions,
      aiPrompt,
      apiKey,
      labels,
      loading,
      error,
      calculations,
      currentLanguage,
      answers,
      setAnswers,
      scores,
      setScores,
      questionStates,
      setQuestionStates
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
          
          {/* Layout - 2x2 CSS Grid for perfect alignment */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '280px 1fr',
            gridTemplateRows: 'auto 1fr',
            gap: '0 24px', // 0px row gap, 24px column gap
            alignItems: 'start',
          }}>
            {/* Top-left cell (empty) */}
            <div></div>

            {/* Top-right cell (Basic Information Title) */}
            <div>
              {metaQuestions && metaQuestions.length > 0 && (
                <h2 style={{
                  fontSize: '24px',
                  fontWeight: 'bold',
                  marginBottom: '20px',
                  color: '#2c3e50',
                  marginTop: 0 // Align with top
                }}>
                  Basic Information
                </h2>
              )}
            </div>
            
            {/* Bottom-left cell (Sidebar) */}
            <div style={{
              position: 'sticky',
              top: '20px',
            }}>
              <SidebarResults />
            </div>

            {/* Bottom-right cell (Questions) */}
            <div>
              <QuestionSection />
            </div>
          </div>
          
          <Footer />
        </div>
      </div>
    </AppContext.Provider>
  );
}

export default App;