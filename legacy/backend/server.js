const express = require('express');
const cors = require('cors');
const axios = require('axios');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'OK', timestamp: new Date().toISOString() });
});

// Main evaluation endpoint
app.post('/api/evaluate', async (req, res) => {
  try {
    const { system, prompt_add, meta, question, answer, answers_ctx } = req.body;

    // Validate required fields
    if (!system || !question || !answer) {
      return res.status(400).json({ 
        error: 'Missing required fields: system, question, answer' 
      });
    }

    // Build the prompt for OpenAI
    let fullPrompt = system;
    
    // Add prompt_add if provided
    if (prompt_add) {
      fullPrompt += `\n\n${prompt_add}`;
    }

    // Add meta information
    if (meta && Object.keys(meta).length > 0) {
      fullPrompt += '\n\nMeta Information:';
      Object.entries(meta).forEach(([key, value]) => {
        fullPrompt += `\n${key}: ${value}`;
      });
    }

    // Add context answers
    if (answers_ctx && Object.keys(answers_ctx).length > 0) {
      fullPrompt += '\n\nContext Answers:';
      Object.entries(answers_ctx).forEach(([key, value]) => {
        fullPrompt += `\n${key}: ${value}`;
      });
    }

    // Add the main question and answer
    fullPrompt += `\n\nQuestion: ${question.text}`;
    fullPrompt += `\nAnswer: ${answer.value}`;

    // Add extra information if provided
    if (answer.extra && Object.keys(answer.extra).length > 0) {
      fullPrompt += '\n\nAdditional Information:';
      Object.entries(answer.extra).forEach(([key, value]) => {
        fullPrompt += `\n${key}: ${value}`;
      });
    }

    if (answer.other_text) {
      fullPrompt += `\n\nOther: ${answer.other_text}`;
    }

    // Add instruction for score format
    fullPrompt += '\n\nPlease evaluate this answer and return a score from 0 to 100, where 0 is extremely high risk and 100 is extremely low risk. Return only a JSON object with a "score" field.';

    console.log('Sending to OpenAI:', {
      system: system.substring(0, 100) + '...',
      prompt_add: prompt_add?.substring(0, 100) + '...',
      question: question.text,
      answer: answer.value,
      metaKeys: Object.keys(meta || {}),
      contextKeys: Object.keys(answers_ctx || {})
    });

    // Call OpenAI API
    const openaiResponse = await axios.post(
      'https://api.openai.com/v1/chat/completions',
      {
        model: 'gpt-4',
        messages: [
          {
            role: 'system',
            content: 'You are an expert business evaluator. Analyze the provided information and return a score from 0 to 100, where 0 is extremely high risk and 100 is extremely low risk. Return only a JSON object with a "score" field.'
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
          'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
          'Content-Type': 'application/json'
        }
      }
    );

    const aiResponse = openaiResponse.data.choices[0].message.content;
    console.log('OpenAI response:', aiResponse);

    // Parse the score from the response
    let score;
    try {
      // Try to extract JSON from the response
      const jsonMatch = aiResponse.match(/\{.*\}/);
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0]);
        score = parsed.score;
      } else {
        // Fallback: try to extract a number from the response
        const numberMatch = aiResponse.match(/\b\d+\b/);
        score = numberMatch ? parseInt(numberMatch[0]) : null;
      }
    } catch (parseError) {
      console.error('Error parsing AI response:', parseError);
      score = null;
    }

    if (score === null || score === undefined || isNaN(score)) {
      return res.status(500).json({ 
        error: 'Failed to extract valid score from AI response',
        aiResponse: aiResponse
      });
    }

    // Ensure score is within 0-100 range
    score = Math.max(0, Math.min(100, score));

    res.json({ score: score });

  } catch (error) {
    console.error('Evaluation error:', error);

    if (error.response?.status === 401) {
      return res.status(500).json({ 
        error: 'Invalid API key. Please check your OpenAI API key configuration.' 
      });
    }

    if (error.response?.status === 429) {
      return res.status(500).json({ 
        error: 'Rate limit exceeded. Please try again later.' 
      });
    }

    res.status(500).json({ 
      error: 'Failed to evaluate answer. Please try again.',
      details: error.message
    });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/api/health`);
  console.log(`Evaluation endpoint: http://localhost:${PORT}/api/evaluate`);
}); 