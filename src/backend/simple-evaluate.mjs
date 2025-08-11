import OpenAI from 'openai';
import fs from 'fs';
import path from 'path';

let questionsData = null;
let aiPrompt = '';

function loadQuestionsData(config) {
  if (questionsData) {
    return;
  }
  try {
    const questionFile = config?.Generic?.question_set_file || 'q4.json';
    const jsonPath = path.resolve(process.cwd(), 'public/questions', questionFile);
    const jsonData = fs.readFileSync(jsonPath, 'utf-8');
    questionsData = JSON.parse(jsonData);

    const promptFile = config?.Generic?.ai_prompt_file || 'ai-prompt.txt';
    const promptPath = path.resolve(process.cwd(), 'public/questions', promptFile);
    aiPrompt = fs.readFileSync(promptPath, 'utf-8');

  } catch (error) {
    console.error('Error loading questions data or prompt:', error);
    // In a real-world scenario, you might want to throw the error
    // and handle it in the calling function, so the server returns a 500 error.
    questionsData = { questions: [], meta_questions: [] };
    aiPrompt = 'You are a helpful assistant.'; // Fallback prompt
  }
}

// Helper function to find a question by its ID from the loaded data
function findQuestionById(id) {
  if (!questionsData || !Array.isArray(questionsData.questions)) return null;
  return questionsData.questions.find(q => q.id === id);
}

// Helper function to get readable answer text
function getReadableAnswer(question, answerValue) {
  if (!question || answerValue === undefined || answerValue === null || answerValue === '') return answerValue;
  if (question.question_type === 'yes-no') return answerValue === 'yes' ? 'Yes' : 'No';
  if (Array.isArray(answerValue) && question.options) {
    return answerValue.map(val => {
      const option = question.options.find(opt => opt.code === val);
      return option ? option.label : val;
    }).join(', ');
  }
  if (question.options) {
    const option = question.options.find(opt => opt.code === answerValue);
    return option ? option.label : answerValue;
  }
  return answerValue;
}


const openai = new OpenAI({
  apiKey: process.env.REACT_APP_GPT_KEY,
  project: process.env.REACT_APP_PROJECT_ID,
});

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Method Not Allowed' });
  }
  
  const config = req.appConfig || {};
  loadQuestionsData(config); // Ensure data is loaded

  const { questionId, allAnswers } = req.body;

  if (!questionId || !allAnswers) {
    return res.status(400).json({ message: 'Missing questionId or allAnswers in request body' });
  }

  const question = findQuestionById(questionId);

  if (!question) {
    return res.status(404).json({ message: `Question with ID ${questionId} not found.` });
  }

  // --- Start building the prompt ---
  const payload = {
    system: aiPrompt,
    additional_context: question.prompt_add || '',
    meta: {},
    question: { id: question.id, text: question.text },
    answer: getReadableAnswer(question, allAnswers[question.id]),
    answers_ctx: {}
  };

  if (question.ai_context?.include_meta) {
    question.ai_context.include_meta.forEach(metaId => {
      const metaQuestion = findQuestionById(metaId);
      if (metaQuestion && allAnswers[metaId]) {
        payload.meta[metaQuestion.text] = getReadableAnswer(metaQuestion, allAnswers[metaId]);
      }
    });
  }

  if (question.ai_context?.include_answers) {
    question.ai_context.include_answers.forEach(answerId => {
      const ctxQuestion = findQuestionById(answerId);
      if (ctxQuestion && allAnswers[answerId]) {
        payload.answers_ctx[ctxQuestion.text] = getReadableAnswer(ctxQuestion, allAnswers[answerId]);
      }
    });
  }
  // --- End building the prompt ---

  const fullPrompt = `
    Based on the following context, please evaluate the provided answer.
    
    System Instructions:
    ${payload.system}
    
    Additional Question Context:
    ${payload.additional_context}
    
    Business Meta-Information:
    ${Object.entries(payload.meta).map(([key, value]) => `- ${key}: ${value}`).join('\n')}
    
    Dependent Answers Context:
    ${Object.entries(payload.answers_ctx).map(([key, value]) => `- ${key}: ${value}`).join('\n')}
    
    Question:
    ${payload.question.text}
    
    User's Answer:
    ${payload.answer}
    
    Return ONLY a single JSON object with 'score' (0-100) and 'explanation' (string) keys.
  `;

  const openaiConfig = config?.Backend?.openai || {};
  const model = openaiConfig.simple_evaluate_model || "gpt-4-1106-preview";
  const temperature = openaiConfig.default_temperature || 0.3;
  const max_tokens = openaiConfig.default_max_tokens || 1024;

  const retryConfig = config?.Backend?.retry_logic || {};
  const maxAttempts = retryConfig.max_attempts || 3;
  const initialDelay = (retryConfig.initial_delay_seconds || 1) * 1000;
  const maxDelay = (retryConfig.max_delay_seconds || 30) * 1000;
  
  let attempt = 0;

  while (attempt < maxAttempts) {
    attempt++;
    try {
      const completion = await openai.chat.completions.create({
          messages: [
            { "role": "system", "content": payload.system },
            { "role": "user", "content": fullPrompt }
          ],
          model: model,
          response_format: { type: "json_object" },
          temperature: temperature,
          max_tokens: max_tokens,
          frequency_penalty: 0,
          presence_penalty: 0,
        });

      // On success, exit the loop and return the response
      return res.status(200).json(JSON.parse(completion.choices[0].message.content));

    } catch (error) {
      // Only retry on rate limit errors (status 429)
      if (error.status === 429) {
        if (attempt >= maxAttempts) {
          console.error(`Rate limit error on final attempt (${attempt}/${maxAttempts}). Failing.`);
          return res.status(500).json({ message: 'AI service is currently busy. Please try again later.' });
        }
        const apiRetryAfterMs = error.headers['retry-after-ms'] ? parseInt(error.headers['retry-after-ms'], 10) : 0;
        
        // Exponential backoff calculation
        const exponentialDelay = initialDelay * (2 ** (attempt - 1));
        
        // Add jitter to prevent thundering herd
        const jitter = Math.random() * 500;
        
        let waitTime = Math.min(exponentialDelay + jitter, maxDelay);
        waitTime = Math.max(waitTime, apiRetryAfterMs);

        console.warn(`Rate limit exceeded. Attempt ${attempt}/${maxAttempts}. Retrying in ${waitTime.toFixed(0)}ms...`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
      } else {
        // For any other non-retriable error, log it and return a generic 500 error
        console.error('Non-retriable error with OpenAI API:', error);
        return res.status(500).json({ message: 'Error processing your request with AI.' });
      }
    }
  }
  // This part is reached only if all retries for rate limit errors fail.
  return res.status(500).json({ message: 'Failed to get a response from AI service after multiple attempts.' });
}

