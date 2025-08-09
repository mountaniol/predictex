import express from 'express';
import cors from 'cors';
import { default as handler } from './api/simple-evaluate.mjs';

const app = express();
const port = 3001;

app.use(cors());
app.use(express.json());

// This route will catch all requests to /api/simple-evaluate.mjs
app.all('/api/simple-evaluate.mjs', async (req, res) => {
  console.log(`[Local API Server] Received ${req.method} request for /api/simple-evaluate.mjs`);
  try {
    await handler(req, res);
  } catch (error) {
    console.error('[Local API Server] Error executing handler:', error);
    res.status(500).send('Internal Server Error');
  }
});

app.listen(port, () => {
  console.log(`[Local API Server] Running at http://localhost:${port}`);
});

