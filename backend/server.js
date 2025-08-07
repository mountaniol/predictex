const express = require('express');
const cors = require('cors');
const axios = require('axios');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());

// API Key from environment variables
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

// Check if API key exists
if (!OPENAI_API_KEY) {
  console.error('❌ OPENAI_API_KEY not found in environment variables');
  process.exit(1);
}

// Endpoint для оценки ответов
app.post('/api/evaluate', async (req, res) => {
  try {
    const { question, answer, systemPrompt, questionType } = req.body;

    // Validate input data
    if (!question || !answer || !systemPrompt) {
      return res.status(400).json({ 
        error: 'Missing required fields: question, answer, systemPrompt' 
      });
    }

    console.log(`[API] Evaluating question: ${question.substring(0, 50)}...`);

    // Build prompt for OpenAI
    let userPrompt = `Question: ${question}\n`;
    if (questionType === 'yes-no' || questionType === 'numeric') {
      userPrompt += `answer = ${answer}`;
    } else {
      userPrompt += `Answer: ${answer}`;
    }

    // Send request to OpenAI
    const response = await axios.post('https://api.openai.com/v1/chat/completions', {
      model: 'gpt-4o-mini',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      max_tokens: 20,
    }, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${OPENAI_API_KEY}`,
      },
    });

    // Extract result
    let score;
    if (questionType === 'yes-no') {
      score = answer === 'yes' ? 100 : 0;
    } else {
      const content = response.data.choices[0].message.content;
      const match = content.match(/\d{1,3}/);
      score = match ? Math.min(100, Math.max(0, parseInt(match[0], 10))) : null;
    }

    console.log(`[API] Score: ${score}`);

    res.json({ score });

  } catch (error) {
    console.error('[API] Error:', error.response?.data || error.message);
    
    if (error.response?.status === 401) {
      res.status(401).json({ error: 'Invalid API key' });
    } else if (error.response?.status === 429) {
      res.status(429).json({ error: 'Rate limit exceeded' });
    } else {
      res.status(500).json({ 
        error: 'Internal server error',
        details: error.response?.data?.error?.message || error.message
      });
    }
  }
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'OK', timestamp: new Date().toISOString() });
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 Backend server running on port ${PORT}`);
  console.log(`📊 Health check: http://localhost:${PORT}/api/health`);
  console.log(`🔑 API Key: ${OPENAI_API_KEY ? '✅ Loaded' : '❌ Missing'}`);
}); 