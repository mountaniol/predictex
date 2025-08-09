
import { useState, useEffect } from 'react';

/**
 * @brief Loads and parses JSON configuration files for questions and settings
 * 
 * Fetches JSON files from the public directory and handles both new q3.json format
 * and legacy questions2.json format. Supports internationalization by loading
 * language-specific files (e.g., q3.ru.json, questions2.de.json).
 * 
 * @function loadJson
 * @param {string} fileName - Name of the JSON file to load (e.g., 'q3.json', 'q3.ru.json')
 * @returns {Promise<Object>} Parsed configuration object
 * @returns {Array} meta_questions - Meta questions for basic information
 * @returns {Array} questions - Main questions grouped by cluster
 * @returns {Object} settings - UI settings and labels
 * @returns {Array} calculations - Calculation rules for derived scores
 * 
 * @throws {Error} HTTP error if file cannot be loaded
 * @throws {Error} JSON parsing error if file is malformed
 * 
 * @environment {Public Directory} - Reads from /public/ directory
 * @environment {File System} - Accesses static JSON files
 * 
 * @format {q3.json} - New format with meta_questions, questions, settings, calculations
 * @format {questions2.json} - Legacy format with questions array and optional settings
 * @format {Internationalization} - Language-specific files with .{lang}.json suffix
 * 
 * @role {Data Loader} - Fetches configuration data from static files
 * @role {Format Handler} - Handles multiple JSON formats and versions
 * @role {Internationalization} - Supports multi-language configuration files
 */
const loadJson = async (fileName) => {
  try {
    const response = await fetch(`/questions/${fileName}`);
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

/**
 * @brief Custom React hook for loading and managing questions configuration
 * 
 * Main data loading hook that orchestrates the loading of questions, settings,
 * AI prompts, and API configuration. Handles internationalization, format
 * detection, and fallback mechanisms. Manages loading states and error handling.
 * 
 * @function useLoadQuestions
 * @param {string} currentLanguage - Current language setting (en/ru/de)
 * @returns {Object} Configuration and state object
 * @returns {Array} sections - Questions grouped by cluster/section
 * @returns {Array} metaQuestions - Meta questions for basic information
 * @returns {string} aiPrompt - System prompt for AI evaluation
 * @returns {string} apiKey - API endpoint URL for evaluation
 * @returns {boolean} loading - Loading state indicator
 * @returns {string} error - Error message if loading fails
 * @returns {Object} labels - UI labels for yes/no options
 * @returns {Array} calculations - Calculation rules for derived scores
 * 
 * @state {Array} sections - Questions organized by cluster_name
 * @state {Array} metaQuestions - Meta questions from q3.json format
 * @state {string} aiPrompt - AI system prompt loaded from /questions/ai-prompt.txt
 * @state {string} apiKey - API endpoint URL (hardcoded to '/api/simple-evaluate.mjs')
 * @state {boolean} loading - Loading state for async operations
 * @state {string} error - Error message for failed operations
 * @state {Object} labels - UI labels from settings
 * @state {Array} calculations - Calculation rules from configuration
 * 
 * @environment {File System} - Reads JSON files and text files from /public/
 * @environment {Network} - Fetches configuration files via HTTP
 * @environment {Vercel} - Uses Vercel API endpoint for evaluation
 * 
 * @dependencies {loadJson} - Function to load and parse JSON files
 * @dependencies {fetch} - Browser API for loading files
 * @dependencies {useState} - React hook for state management
 * @dependencies {useEffect} - React hook for side effects
 * 
 * @architecture {Data Loading} - Hierarchical loading with fallbacks
 * @architecture {Internationalization} - Language-specific file loading
 * @architecture {Format Compatibility} - Supports multiple JSON formats
 * @architecture {Error Handling} - Graceful degradation with fallbacks
 * 
 * @role {Data Orchestrator} - Coordinates loading of all configuration data
 * @role {State Manager} - Manages loading states and error handling
 * @role {Format Handler} - Handles multiple configuration formats
 * @role {Internationalization} - Supports multi-language configuration
 * 
 * @workflow {1} Attempts to load q3.{lang}.json (new format)
 * @workflow {2} Falls back to questions2.{lang}.json (legacy format)
 * @workflow {3} Groups questions by cluster_name into sections
 * @workflow {4} Loads AI prompt from /questions/ai-prompt.txt
 * @workflow {5} Sets API endpoint to Vercel function
 * @workflow {6} Updates state with loaded configuration
 */
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
          const promptResponse = await fetch('/questions/ai-prompt.txt');
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
        setApiKey('/api/simple-evaluate.mjs');
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