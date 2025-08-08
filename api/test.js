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

  res.json({ 
    message: 'API is working!',
    method: req.method,
    timestamp: new Date().toISOString(),
    env: {
      hasGptKey: !!process.env.REACT_APP_GPT_KEY,
      hasOpenAiKey: !!process.env.OPENAI_API_KEY
    }
  });
};
