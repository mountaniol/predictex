import express from 'express';
import cors from 'cors';
import { default as evaluateHandler } from './api/simple-evaluate.mjs';
import { default as validateHandler } from './api/simple-validate.mjs';

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
  const module = await import('./api/final-analysis.mjs');
  await module.default(req, res);
});

app.listen(port, () => {
  console.log(`Local API server listening at http://localhost:${port}`);
});

