const axios = require('axios');

module.exports = async (req, res) => {
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

