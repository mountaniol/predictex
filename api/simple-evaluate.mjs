import axios from 'axios';

/**
 * @brief Vercel serverless function for AI-powered answer evaluation
 * 
 * Main API endpoint that evaluates user answers using OpenAI's GPT-4 model.
 * Processes evaluation requests, validates input data, calls OpenAI API,
 * and returns numerical scores. Handles CORS, error states, and response
 * formatting for the QnA evaluation system.
 * 
 * @function default
 * @param {Object} req - HTTP request object from Vercel
 * @param {Object} res - HTTP response object from Vercel
 * @returns {Promise<void>} Async function that sends JSON response
 * 
 * @input {Object} req.body - Request payload with evaluation data
 * @input {string} req.body.system - System prompt for AI evaluation
 * @input {string} req.body.prompt_add - Additional prompt context
 * @input {Object} req.body.meta - Meta information for context
 * @input {Object} req.body.question - Question configuration and text
 * @input {Object} req.body.answer - User's answer data
 * @input {Object} req.body.answers_ctx - Context from other answers
 * 
 * @output {Object} res - HTTP response with evaluation result
 * @output {number} res.json.score - Numerical score from 0-100
 * @output {string} res.json.error - Error message if evaluation fails
 * 
 * @environment {Vercel} - Serverless function environment
 * @environment {OpenAI} - OpenAI API for GPT-4 evaluation
 * @environment {CORS} - Cross-origin resource sharing headers
 * 
 * @dependencies {axios} - HTTP client for OpenAI API calls
 * @dependencies {process.env.REACT_APP_GPT_KEY} - OpenAI API key
 * @dependencies {process.env.OPENAI_API_KEY} - Fallback API key
 * 
 * @architecture {Serverless} - Vercel serverless function
 * @architecture {API Gateway} - Handles HTTP requests and responses
 * @architecture {AI Integration} - OpenAI GPT-4 integration
 * @architecture {Error Handling} - Comprehensive error management
 * 
 * @role {API Endpoint} - Main evaluation API for the application
 * @role {AI Evaluator} - Orchestrates AI-powered answer evaluation
 * @role {Data Validator} - Validates input data and API configuration
 * @role {Response Formatter} - Formats evaluation results for frontend
 * @role {Error Handler} - Manages errors and provides user feedback
 * 
 * @workflow {1} Sets up CORS headers and handles preflight requests
 * @workflow {2} Validates HTTP method (POST only)
 * @workflow {3} Validates required input fields
 * @workflow {4} Checks OpenAI API key availability
 * @workflow {5} Builds evaluation prompt with context
 * @workflow {6} Calls OpenAI GPT-4 API
 * @workflow {7} Parses AI response and extracts score
 * @workflow {8} Returns formatted response or error
 * 
 * @security {API Key} - Uses environment variables for OpenAI API key
 * @security {CORS} - Configures cross-origin access
 * @security {Validation} - Validates all input data
 * @security {Error Handling} - Prevents sensitive data leakage
 */
export default async (req, res) => {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // Handle preflight requests
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  // Only allow POST requests
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { system, prompt_add, meta, question, answer, answers_ctx } = req.body;

    // Validate required fields
    if (!system || !question || !answer) {
      return res.status(400).json({
        error: 'Missing required fields: system, question, answer'
      });
    }

    // Check if API key is available
    const openaiApiKey = process.env.REACT_APP_GPT_KEY || process.env.OPENAI_API_KEY;
    if (!openaiApiKey) {
      return res.status(500).json({
        error: 'OpenAI API key not configured'
      });
    }

    // Build the prompt
    let fullPrompt = system;
    if (prompt_add) fullPrompt += `\n\n${prompt_add}`;
    fullPrompt += `\n\nQuestion: ${question.text}`;
    fullPrompt += `\nAnswer: ${answer.value}`;
    fullPrompt += '\n\nPlease evaluate this answer and return a score from 0 to 100, where 0 is extremely high risk and 100 is extremely low risk. Return only a JSON object with a "score" field.';

    // Call OpenAI API
    const openaiResponse = await axios.post(
      'https://api.openai.com/v1/chat/completions',
      {
        model: 'gpt-4',
        messages: [
          {
            role: 'system',
            content: 'You are an expert business evaluator. Return only a JSON object with a "score" field.'
          },
          {
            role: 'user',
            content: fullPrompt
          }
        ],
        temperature: 0.1,
        max_tokens: 150
      },
      {
        headers: {
          'Authorization': `Bearer ${openaiApiKey}`,
          'Content-Type': 'application/json'
        }
      }
    );

    const aiResponse = openaiResponse.data.choices[0].message.content;
    
    // Parse the score
    let score;
    try {
      const jsonMatch = aiResponse.match(/\{.*\}/);
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0]);
        score = parsed.score;
      } else {
        const numberMatch = aiResponse.match(/\b\d+\b/);
        score = numberMatch ? parseInt(numberMatch[0]) : null;
      }
    } catch (parseError) {
      score = null;
    }

    if (score === null || score === undefined || isNaN(score)) {
      return res.status(500).json({
        error: 'Failed to extract valid score from AI response'
      });
    }

    score = Math.max(0, Math.min(100, score));
    res.json({ score: score });

  } catch (error) {
    console.error('Evaluation error:', error);
    res.status(500).json({
      error: 'Failed to evaluate answer. Please try again.'
    });
  }
};

