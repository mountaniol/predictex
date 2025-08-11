import express from 'express';
import cors from 'cors';
import { default as evaluateHandler } from './simple-evaluate.mjs';
import { config } from 'dotenv';
import fs from 'fs';
import path from 'path';

// --- Config Loading ---
let _appConfig = null;

function loadAppConfig() {
  if (_appConfig) {
    return _appConfig;
  }
  try {
    const configPath = path.resolve(process.cwd(), 'public', 'app.config.json');
    const configData = fs.readFileSync(configPath, 'utf-8');
    _appConfig = JSON.parse(configData);
    console.log('[Config] app.config.json loaded successfully.');
  } catch (error) {
    console.error('CRITICAL: Could not load app.config.json. Falling back to defaults.', error);
    _appConfig = {}; // Fallback to avoid crashes
  }
  return _appConfig;
}
// --- End Config Loading ---

// Load environment variables from .env file
config();

console.log('===== Local API Server Environment =====');
console.log('REACT_APP_GPT_KEY exists:', !!process.env.REACT_APP_GPT_KEY);
console.log('REACT_APP_PROJECT_ID exists:', !!process.env.REACT_APP_PROJECT_ID);
console.log('========================================');

const app = express();

app.use(cors());
app.use(express.json());

app.all('/api/simple-evaluate.mjs', async (req, res) => {
  console.log(`[Local API Server] Received ${req.method} request for /api/simple-evaluate.mjs`);
  try {
    // Inject config into the request object for the handler to use
    req.appConfig = loadAppConfig();
    await evaluateHandler(req, res);
  } catch (error) {
    console.error('[Local API Server] Error executing evaluate handler:', error);
    res.status(500).send('Internal Server Error');
  }
});

app.post('/api/final-analysis.mjs', async (req, res) => {
  console.log(`[Local API Server] Received POST request for /api/final-analysis.mjs`);
  try {
    // Inject config into the request object
    req.appConfig = loadAppConfig();
    const module = await import('./final-analysis.mjs');
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

const appConfig = loadAppConfig();
const port = appConfig?.Backend?.local_api_port || 3001;

app.listen(port, () => {
  console.log(`Local API server listening at http://localhost:${port}`);
});

