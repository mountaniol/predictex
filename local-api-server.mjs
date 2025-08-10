import express from 'express';
import cors from 'cors';
import { default as evaluateHandler } from './api/simple-evaluate.mjs';
import { default as validateHandler } from './api/simple-validate.mjs';
import { config } from 'dotenv';

// Load environment variables from .env file
config();

console.log('===== Local API Server Environment =====');
console.log('REACT_APP_GPT_KEY exists:', !!process.env.REACT_APP_GPT_KEY);
console.log('REACT_APP_PROJECT_ID exists:', !!process.env.REACT_APP_PROJECT_ID);
console.log('========================================');

const app = express();
const port = 3001;

app.use(cors());
app.use(express.json());

app.all('/api/simple-evaluate.mjs', async (req, res) => {
  console.log(`[Local API Server] Received ${req.method} request for /api/simple-evaluate.mjs`);
  try {
    await evaluateHandler(req, res);
  } catch (error) {
    console.error('[Local API Server] Error executing evaluate handler:', error);
    res.status(500).send('Internal Server Error');
  }
});

app.post('/api/simple-validate.mjs', async (req, res) => {
  const module = await import('./api/simple-validate.mjs');
  await module.default(req, res);
});

app.post('/api/final-analysis.mjs', async (req, res) => {
  console.log(`[Local API Server] Received POST request for /api/final-analysis.mjs`);
  try {
    const module = await import('./api/final-analysis.mjs');
    await module.default(req, res);
  } catch (error) {
    console.error('[Local API Server] Error executing final-analysis handler:', error);
    res.status(500).json({ 
      message: 'Internal Server Error', 
      error: error.message,
      stack: error.stack 
    });
  }
});

app.listen(port, () => {
  console.log(`Local API server listening at http://localhost:${port}`);
});

