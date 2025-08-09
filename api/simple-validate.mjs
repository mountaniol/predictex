import axios from 'axios';

export default async (req, res) => {
  // CORS Headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { validation_prompt, answer } = req.body;

    if (!validation_prompt || answer === undefined) {
      return res.status(400).json({ error: 'Missing required fields: validation_prompt, answer' });
    }

    const openaiApiKey = process.env.REACT_APP_GPT_KEY || process.env.OPENAI_API_KEY;
    if (!openaiApiKey) {
      return res.status(500).json({ error: 'OpenAI API key not configured' });
    }

    const fullPrompt = validation_prompt.replace('{answer}', JSON.stringify(answer));

    const openaiResponse = await axios.post(
      'https://api.openai.com/v1/chat/completions',
      {
        model: 'gpt-4',
        messages: [
          {
            role: 'system',
            content: 'You are a helpful assistant. Your task is to rephrase or summarize the user input based on the provided prompt. Be concise and helpful.'
          },
          {
            role: 'user',
            content: fullPrompt
          }
        ],
        temperature: 0.2,
        max_tokens: 250
      },
      {
        headers: {
          'Authorization': `Bearer ${openaiApiKey}`,
          'Content-Type': 'application/json'
        }
      }
    );

    const summary = openaiResponse.data.choices[0].message.content.trim();
    
    res.json({ summary });

  } catch (error) {
    console.error('Validation error:', error.response ? error.response.data : error.message);
    res.status(500).json({
      error: 'Failed to get validation from AI.',
      details: error.message
    });
  }
};
