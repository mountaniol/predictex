import OpenAI from 'openai';
import fs from 'fs';
import path from 'path';

let questionsData = null;
let aiPrompt = '';

function loadQuestionsData() {
  if (questionsData) {
    return;
  }
  try {
    const jsonPath = path.resolve(process.cwd(), 'public/questions/q4.json');
    const jsonData = fs.readFileSync(jsonPath, 'utf-8');
    questionsData = JSON.parse(jsonData);

    const promptPath = path.resolve(process.cwd(), 'public/questions/ai-prompt.txt');
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
  if (!questionsData) return null;
  const allQuestions = [...questionsData.questions, ...questionsData.meta_questions];
  return allQuestions.find(q => q.id === id);
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

  loadQuestionsData(); // Ensure data is loaded

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

  try {
    const completion = await openai.chat.completions.create({
        messages: [
          { "role": "system", "content": payload.system },
          { "role": "user", "content": fullPrompt }
        ],
        model: "gpt-4-1106-preview",
        response_format: { type: "json_object" },
        temperature: 0.3,
        max_tokens: 1024,
        frequency_penalty: 0,
        presence_penalty: 0,
      });

    res.status(200).json(JSON.parse(completion.choices[0].message.content));
  } catch (error) {
    console.error('Error with OpenAI API:', error);
    res.status(500).json({ message: 'Error processing your request with AI.' });
  }
}

