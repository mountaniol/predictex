/**
 * Server-Driven App Context
 * 
 * Simplified React Context for Server-Driven UI architecture:
 * - Removes all business logic (moved to backend)
 * - Stores only UI state needed for rendering
 * - Integrates with ServerDrivenUIManager
 * - Maintains compatibility with existing components during transition
 */

import React, { createContext, useState, useEffect, useRef, useLayoutEffect } from 'react';
import ServerDrivenUIManager from './frontend/ServerDrivenUIManager.js';

// Create context
export const ServerDrivenAppContext = createContext(null);

/**
 * Server-Driven App Provider
 * 
 * Replaces the complex business logic in App.js with a thin UI state manager
 * that receives all instructions from the backend via Server-Driven UI protocol
 */
export function ServerDrivenAppProvider({ children }) {
  // UI-only state (no business logic)
  const [uiState, setUIState] = useState({
    // Rendering data (populated by backend commands)
    sections: [],
    answers: {},
    scores: {},
    explanations: {},
    questionStates: {},
    
    // UI-specific state
    loading: true,
    error: null,
    currentLanguage: 'en',
    highlightUnanswered: false,
    isGeneratingReport: false,
    
    // Configuration (minimal UI config only)
    appConfig: null,
    questionSetId: null,
    labels: {},
    
    // Report state
    finalReport: null,
    finalAnalysisConfig: null
  });

  // Server-Driven UI Manager
  const uiManagerRef = useRef(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [systemHealth, setSystemHealth] = useState(null);

  // Layout refs (preserved for existing components)
  const topOfContentRef = useRef(null);
  const finalReportRef = useRef(null);
  const [contentOffset, setContentOffset] = useState(0);

  /**
   * Initialize Server-Driven UI system
   */
  useEffect(() => {
    const initializeServerDrivenUI = async () => {
      try {
        console.log('[ServerDrivenAppProvider] Initializing Server-Driven UI...');
        
        // Load basic app configuration
        const config = await loadAppConfig();
        
        // Create UI Manager
        uiManagerRef.current = new ServerDrivenUIManager({
          sseEndpoint: config.sseEndpoint || '/api/sse',
          eventsEndpoint: config.eventsEndpoint || '/api',
          sessionId: config.sessionId || generateSessionId(),
          autoStart: true
        });

        // Setup event listeners
        setupUIManagerListeners();

        // Initialize the system with our state setter
        await uiManagerRef.current.initialize(setUIState);

        // Update UI state with initial config
        setUIState(prevState => ({
          ...prevState,
          appConfig: config,
          questionSetId: config.questionSetId,
          loading: false
        }));

        console.log('[ServerDrivenAppProvider] Server-Driven UI initialized successfully');

      } catch (error) {
        console.error('[ServerDrivenAppProvider] Initialization failed:', error);
        setUIState(prevState => ({
          ...prevState,
          loading: false,
          error: `Failed to initialize Server-Driven UI: ${error.message}`
        }));
      }
    };

    initializeServerDrivenUI();

    // Cleanup on unmount
    return () => {
      if (uiManagerRef.current) {
        uiManagerRef.current.shutdown();
      }
    };
  }, []);

  /**
   * Setup event listeners for UI Manager
   */
  const setupUIManagerListeners = () => {
    const uiManager = uiManagerRef.current;

    // Connection status updates
    uiManager.on('connectionStateChanged', (connected) => {
      setConnectionStatus(connected ? 'connected' : 'disconnected');
    });

    // System health monitoring
    uiManager.on('healthCheck', (health) => {
      setSystemHealth(health);
    });

    // Error handling
    uiManager.on('initializationFailed', (error) => {
      setUIState(prevState => ({
        ...prevState,
        error: `System initialization failed: ${error.message}`,
        loading: false
      }));
    });

    uiManager.on('commandError', (error) => {
      console.error('[ServerDrivenAppProvider] Command processing error:', error);
    });

    uiManager.on('sseError', (error) => {
      console.warn('[ServerDrivenAppProvider] SSE connection error:', error);
    });
  };

  /**
   * Load basic app configuration
   */
  const loadAppConfig = async () => {
    try {
      const response = await fetch('/app.config.json');
      const config = await response.json();
      
      // Extract basic configuration needed for UI
      const questionSetId = new URLSearchParams(window.location.search).get('q') || 
                           config?.Generic?.question_set_file?.replace(/\.(json|toml)$/, '') ||
                           'q4';

      return {
        ...config,
        questionSetId,
        sseEndpoint: config.Backend?.sse_endpoint || '/api/sse',
        eventsEndpoint: config.Backend?.events_endpoint || '/api'
      };
    } catch (error) {
      console.warn('[ServerDrivenAppProvider] Failed to load app.config.json:', error);
      
      // Fallback configuration
      return {
        questionSetId: new URLSearchParams(window.location.search).get('q') || 'q4',
        sseEndpoint: '/api/sse',
        eventsEndpoint: '/api'
      };
    }
  };

  /**
   * Generate unique session ID
   */
  const generateSessionId = () => {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  };

  /**
   * Handle user interactions - dispatch to backend
   */
  const dispatchUserEvent = async (eventType, eventData) => {
    if (!uiManagerRef.current) {
      console.warn('[ServerDrivenAppProvider] UI Manager not initialized');
      return false;
    }

    const event = {
      type: eventType,
      data: {
        sessionId: uiState.questionSetId,
        timestamp: Date.now(),
        ...eventData
      }
    };

    return await uiManagerRef.current.dispatchEvent(event);
  };

  /**
   * Layout effect for measuring content offset (preserved for compatibility)
   */
  useLayoutEffect(() => {
    if (topOfContentRef.current) {
      const newHeight = topOfContentRef.current.offsetHeight;
      if (newHeight !== contentOffset) {
        setContentOffset(newHeight);
      }
    }
  }, [uiState.loading, contentOffset]);

  /**
   * UI-only setters for compatibility with existing components
   * These will be replaced as components are refactored to be pure
   */
  const compatibilitySetters = {
    setAnswers: (answers) => {
      // During transition: maintain local state
      // Long-term: remove when components are pure
      setUIState(prevState => ({
        ...prevState,
        answers: typeof answers === 'function' ? answers(prevState.answers) : answers
      }));
    },
    
    setScores: (scores) => {
      setUIState(prevState => ({
        ...prevState,
        scores: typeof scores === 'function' ? scores(prevState.scores) : scores
      }));
    },
    
    setQuestionStates: (states) => {
      setUIState(prevState => ({
        ...prevState,
        questionStates: typeof states === 'function' ? states(prevState.questionStates) : states
      }));
    },
    
    setExplanations: (explanations) => {
      setUIState(prevState => ({
        ...prevState,
        explanations: typeof explanations === 'function' ? explanations(prevState.explanations) : explanations
      }));
    },
    
    setFinalReport: (report) => {
      setUIState(prevState => ({
        ...prevState,
        finalReport: typeof report === 'function' ? report(prevState.finalReport) : report
      }));
    },
    
    setIsGeneratingReport: (generating) => {
      setUIState(prevState => ({
        ...prevState,
        isGeneratingReport: generating
      }));
    },
    
    setHighlightUnanswered: (highlight) => {
      setUIState(prevState => ({
        ...prevState,
        highlightUnanswered: highlight
      }));
    }
  };

  /**
   * Context value combining UI state and Server-Driven UI functionality
   */
  const contextValue = {
    // UI State (read-only for pure components)
    ...uiState,
    
    // Layout refs (preserved for compatibility)
    topOfContentRef,
    finalReportRef,
    contentOffset,
    
    // Compatibility setters (to be removed as components become pure)
    ...compatibilitySetters,
    
    // Server-Driven UI functions
    dispatchUserEvent,
    connectionStatus,
    systemHealth,
    
    // System information
    isServerDriven: true,
    uiManagerStats: uiManagerRef.current?.getStats() || null,
    isConnected: uiManagerRef.current?.isConnected() || false,
    isHealthy: uiManagerRef.current?.isHealthy() || false
  };

  return (
    <ServerDrivenAppContext.Provider value={contextValue}>
      {children}
    </ServerDrivenAppContext.Provider>
  );
}

/**
 * Hook to access Server-Driven App Context
 */
export const useServerDrivenApp = () => {
  const context = React.useContext(ServerDrivenAppContext);
  
  if (!context) {
    throw new Error('useServerDrivenApp must be used within ServerDrivenAppProvider');
  }
  
  return context;
};

/**
 * Migration utility: provides backwards compatibility during transition
 */
export const withServerDrivenCompatibility = (Component) => {
  return function ServerDrivenCompatibleComponent(props) {
    const serverDrivenContext = useServerDrivenApp();
    
    // Map Server-Driven context to legacy context format
    const legacyContext = {
      // Direct mappings
      appConfig: serverDrivenContext.appConfig,
      questionSetId: serverDrivenContext.questionSetId,
      sections: serverDrivenContext.sections,
      loading: serverDrivenContext.loading,
      error: serverDrivenContext.error,
      currentLanguage: serverDrivenContext.currentLanguage,
      answers: serverDrivenContext.answers,
      scores: serverDrivenContext.scores,
      questionStates: serverDrivenContext.questionStates,
      explanations: serverDrivenContext.explanations,
      labels: serverDrivenContext.labels,
      finalReport: serverDrivenContext.finalReport,
      isGeneratingReport: serverDrivenContext.isGeneratingReport,
      finalAnalysisConfig: serverDrivenContext.finalAnalysisConfig,
      finalReportRef: serverDrivenContext.finalReportRef,
      highlightUnanswered: serverDrivenContext.highlightUnanswered,
      
      // Compatibility setters
      setAnswers: serverDrivenContext.setAnswers,
      setScores: serverDrivenContext.setScores,
      setQuestionStates: serverDrivenContext.setQuestionStates,
      setExplanations: serverDrivenContext.setExplanations,
      setFinalReport: serverDrivenContext.setFinalReport,
      setIsGeneratingReport: serverDrivenContext.setIsGeneratingReport,
      setHighlightUnanswered: serverDrivenContext.setHighlightUnanswered,
      
      // Server-Driven additions
      dispatchUserEvent: serverDrivenContext.dispatchUserEvent,
      connectionStatus: serverDrivenContext.connectionStatus,
      isServerDriven: true
    };
    
    return <Component {...props} context={legacyContext} />;
  };
};

export default ServerDrivenAppContext;