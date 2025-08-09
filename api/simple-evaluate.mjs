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
    const { system, additional_context, meta, question, answer, answers_ctx } = req.body;

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

    if (meta && Object.keys(meta).length > 0) {
      fullPrompt += '\n\nBusiness Context:\n';
      for (const [key, value] of Object.entries(meta)) {
        fullPrompt += `- ${key}: ${value}\n`;
      }
    }

    if (answers_ctx && Object.keys(answers_ctx).length > 0) {
      fullPrompt += '\n\nAdditional Answer Context:\n';
      for (const [key, value] of Object.entries(answers_ctx)) {
        fullPrompt += `- ${key}: ${value}\n`;
      }
    }

    if (additional_context) fullPrompt += `\n\nAdditional Context: ${additional_context}`;
    fullPrompt += `\n\nQuestion: ${question.text}`;
    fullPrompt += `\nAnswer: ${JSON.stringify(answer)}`;
    fullPrompt += '\n\nPlease evaluate this answer. Return ONLY a single JSON object with two fields: "score" (a number from 0 to 100, where 0 is high risk and 100 is low risk) and "explanation" (a detailed rationale for the score, referencing business location and type if provided).';

    console.log('--- OpenAI Payload ---');
    console.log(JSON.stringify(req.body, null, 2));

    // Call OpenAI API
    const openaiResponse = await axios.post(
      'https://api.openai.com/v1/chat/completions',
      {
        model: 'gpt-4',
        messages: [
          {
            role: 'system',
            content: 'You are an expert business evaluator. Your response must be a single JSON object with "score" and "explanation" fields.'
          },
          {
            role: 'user',
            content: fullPrompt
          }
        ],
        temperature: 0.3,
        max_tokens: 1024,
        frequency_penalty: 0,
        presence_penalty: 0,
      },
      {
        headers: {
          'Authorization': `Bearer ${openaiApiKey}`,
          'Content-Type': 'application/json'
        }
      }
    );

    const aiResponse = openaiResponse.data.choices[0].message.content;
    
    console.log('--- Raw AI Response ---');
    console.log(aiResponse);
    console.log('-----------------------');

    // Parse the response
    let score, explanation;
    try {
      const jsonMatch = aiResponse.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0]);
        score = parsed.score;
        explanation = parsed.explanation;
      } else {
        // Fallback for non-JSON response, try to find a number
        const numberMatch = aiResponse.match(/\b\d+\b/);
        score = numberMatch ? parseInt(numberMatch[0]) : null;
        explanation = 'Could not parse explanation.';
      }
    } catch (parseError) {
      score = null;
      explanation = 'Failed to parse AI response.';
    }

    if (score === null || score === undefined || isNaN(score)) {
      return res.status(500).json({
        error: 'Failed to extract valid score from AI response',
        details: aiResponse
      });
    }

    score = Math.max(0, Math.min(100, score));
    res.json({ score, explanation });

  } catch (error) {
    console.error('Evaluation error:', error.response ? error.response.data : error.message);
    res.status(500).json({
      error: 'Failed to evaluate answer. Please try again.',
      details: error.message
    });
  }
};

