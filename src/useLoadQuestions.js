
import { useState, useEffect } from 'react';
import TOML from 'toml';
import { createDependencyReport } from './dependencyValidator.js';
import { FollowUpParser, FollowUpParserError } from './utils/followUpParser.js';

/**
 * Process TOML data to convert DSL follow-up rules to JSON format for compatibility
 * @param {Object} data - The loaded TOML data
 * @returns {Object} - The processed data with JSON-compatible follow-up rules
 */
async function processTOMLData(data) {
  const parser = new FollowUpParser();
  let processedCount = 0;
  
  if (data.questions) {
    for (const question of data.questions) {
      // Process follow-up rules from DSL to JSON format
      if (question.follow_up_rules && question.follow_up_rules.length > 0) {
        try {
          question.follow_ups = parser.rulesToJson(question.follow_up_rules);
          processedCount++;
          console.log(`[useLoadQuestions] Processed ${question.follow_up_rules.length} follow-up rules for question ${question.id}`);
          
          // Remove DSL rules to maintain JSON compatibility
          delete question.follow_up_rules;
        } catch (error) {
          if (error instanceof FollowUpParserError) {
            console.warn(`[useLoadQuestions] Failed to parse follow-up rules for question ${question.id}:`, error.message);
          } else {
            throw error;
          }
        }
      }
      
      // Process flattened AI context fields
      if (question.ai_context_include_answers) {
        question.ai_context = {
          include_answers: question.ai_context_include_answers
        };
        delete question.ai_context_include_answers;
      }
    }
  }
  
  // Process flattened analysis configuration
  if (data.analysis) {
    const analysisData = data.analysis;
    const sections = [];
    
    // Extract base configuration
    const loading_message = analysisData.loading_message || '';
    const base_prompt = analysisData.base_prompt || '';
    
    // Process each analysis section
    for (const [key, sectionData] of Object.entries(analysisData)) {
      if (key === 'loading_message' || key === 'base_prompt' || typeof sectionData !== 'object') {
        continue;
      }
      
      const section = {
        name: sectionData.name || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        model: sectionData.model || 'gpt-4o',
        web_search: {
          enabled: sectionData.web_search_enabled || false,
          max_searches: sectionData.web_search_max_searches || 3
        },
        ai_context: {
          include_answers: sectionData.ai_context_include_answers || [],
          include_scores: sectionData.ai_context_include_scores || false,
          include_overall_score: sectionData.ai_context_include_overall_score || false
        },
        specific_prompt: sectionData.specific_prompt || '',
        output_constraint: sectionData.output_constraint || '',
        model_config: sectionData.model_config || {}
      };
      sections.push(section);
    }
    
    // Replace with nested structure for backward compatibility
    data.final_analysis_config = {
      loading_message,
      base_prompt,
      sections
    };
    
    // Remove flattened analysis config
    delete data.analysis;
    
    console.log(`[useLoadQuestions] Processed ${sections.length} analysis sections from TOML format`);
  }
  
  if (processedCount > 0) {
    console.log(`[useLoadQuestions] Successfully processed follow-up rules for ${processedCount} questions`);
  }
  
  return data;
}

/**
 * @brief Custom hook to load all question data and application settings.
 * @description This hook fetches configuration files (TOML preferred, JSON fallback), which contains all sections,
 * questions, meta-questions, and AI configuration. It manages loading and error states.
 * This is the single source of truth for the application's question data.
 *
 * For TOML files, it processes follow_up_rules using the DSL parser to convert them
 * back to the original JSON format for backward compatibility.
 *
 * @returns {{
 *   sections: Array,
 *   loading: boolean,
 *   error: string,
 *   calculations: Array,
 *   aiPrompt: string,
 *   apiKey: string,
 *   labels: Object
 * }}
 */
const useLoadQuestions = (questionSetId) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sections, setSections] = useState([]);
  const [calculations, setCalculations] = useState(null);
  const [labels, setLabels] = useState(null);
  const [finalAnalysisConfig, setFinalAnalysisConfig] = useState(null);

  useEffect(() => {
    if (!questionSetId) {
      setLoading(false);
      return;
    }

    const loadData = async () => {
      console.log(`[useLoadQuestions] Starting data load for ${questionSetId}...`);
      
      // Validate that questionSetId doesn't contain file extensions
      if (questionSetId.includes('.')) {
        console.warn(`[useLoadQuestions] questionSetId contains extension: ${questionSetId}. This may cause double extension issues.`);
      }
      
      setLoading(true);
      try {
        // Try to load TOML format first, fall back to JSON
        let data;
        let format = 'unknown';
        
        try {
          // First, try to load TOML format
          console.log(`[useLoadQuestions] Attempting to load TOML format: /questions/${questionSetId}.toml`);
          const tomlResponse = await fetch(`/questions/${questionSetId}.toml`);
          
          if (tomlResponse.ok) {
            const tomlText = await tomlResponse.text();
            data = TOML.parse(tomlText);
            format = 'TOML';
            console.log('[useLoadQuestions] Successfully loaded TOML format');
            
            // Process TOML-specific features
            data = await processTOMLData(data);
          } else {
            throw new Error(`TOML not available, status: ${tomlResponse.status}`);
          }
        } catch (tomlError) {
          // Fall back to JSON format
          console.log(`[useLoadQuestions] TOML loading failed (${tomlError.message}), trying JSON format`);
          const jsonResponse = await fetch(`/questions/${questionSetId}.json`);
          
          if (!jsonResponse.ok) {
            const errorText = await jsonResponse.text();
            throw new Error(`Both TOML and JSON loading failed. JSON error - status: ${jsonResponse.status}, body: ${errorText}`);
          }
          
          data = await jsonResponse.json();
          format = 'JSON';
          console.log('[useLoadQuestions] Successfully loaded JSON format as fallback');
        }
        
        console.log(`[useLoadQuestions] Data fetched successfully using ${format} format.`, data);

        // Group questions by cluster_name
        const sectionsMap = {};
        data.questions.forEach(q => {
          const clusterName = q.cluster_name || 'Other';
          if (!sectionsMap[clusterName]) {
            sectionsMap[clusterName] = {
              title: clusterName,
              questions: []
            };
          }
          sectionsMap[clusterName].questions.push(q);
        });

        const sections = Object.values(sectionsMap);
        sections.sort((a, b) => a.position - b.position);
        sections.forEach(s => s.questions.sort((a,b) => a.position_in_cluster - b.position_in_cluster));
        
        // This was the source of the infinite loop. The hook should not
        // change its own trigger ID based on the content of the loaded file.
        // The questionSetId is the source of truth for which file to load.
        // setQuestionSetId(data.version || 'unknown'); 
        
        // Validate dependency graph before setting sections
        console.log('[useLoadQuestions] Validating dependency graph...');
        const dependencyReport = createDependencyReport(data.questions);
        
        if (!dependencyReport.validation.isValid) {
          console.error('[useLoadQuestions] Dependency validation failed:', dependencyReport);
          const errorMessages = dependencyReport.validation.errors.join('; ');
          throw new Error(`Dependency validation failed: ${errorMessages}`);
        }
        
        if (dependencyReport.validation.warnings.length > 0) {
          console.warn('[useLoadQuestions] Dependency warnings:', dependencyReport.validation.warnings);
        }
        
        console.log('[useLoadQuestions] Dependency validation passed:', {
          totalQuestions: dependencyReport.validation.stats.totalQuestions,
          questionsWithDeps: dependencyReport.validation.stats.questionsWithDeps,
          maxDepth: dependencyReport.validation.stats.maxDepthFound,
          forwardReferences: dependencyReport.validation.stats.forwardReferences
        });

        setSections(sections);
        setCalculations(data.calculations || null);
        setLabels(data.settings.labels || null);
        setFinalAnalysisConfig(data.final_analysis_config || null);

      } catch (error) {
        console.error("Error loading or parsing questions:", error);
        setError("Could not load question data.");
      } finally {
        setLoading(false);
        console.log('[useLoadQuestions] Loading finished.');
      }
    };

    loadData();
  }, [questionSetId]);

  return { loading, error, sections, calculations, labels, finalAnalysisConfig };
};

export default useLoadQuestions;