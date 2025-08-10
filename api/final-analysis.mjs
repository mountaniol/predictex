import OpenAI from 'openai';
import fs from 'fs/promises';
import path from 'path';

const openai = new OpenAI({
  apiKey: process.env.REACT_APP_GPT_KEY,
  project: process.env.REACT_APP_PROJECT_ID,
});

async function readJsonFile(filePath) {
  const absolutePath = path.resolve(process.cwd(), filePath);
  const data = await fs.readFile(absolutePath, 'utf8');
  return JSON.parse(data);
}

// Helper to convert data into human-readable text
function formatDataForPrompt(questions, metaQuestions, answers, scores, calculations) {
    let metaText = '';
    metaQuestions.forEach(q => {
        if (answers[q.id]) {
            metaText += `- ${q.text}: ${answers[q.id]}\n`;
        }
    });

    let answersText = '';
    questions.forEach(q => {
        if (answers[q.id]) {
            const scoreText = scores[q.id] ? ` (Score: ${scores[q.id]})` : '';
            answersText += `- ${q.text}: ${answers[q.id]}${scoreText}\n`;
        }
    });

    let calculationsText = '';
    if (calculations) {
        Object.entries(calculations).forEach(([key, value]) => {
             if (scores[key]) {
                calculationsText += `- ${value.label || key}: ${scores[key]}\n`;
             }
        });
    }

    return { metaText, answersText, calculationsText };
}


export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Method Not Allowed' });
  }

  try {
    const { allAnswers, allScores, questionSetId } = req.body;

    if (!allAnswers || !allScores || !questionSetId) {
        return res.status(400).json({ message: 'Missing required body parameters.' });
    }

    const questionFile = `public/questions/${questionSetId}.json`;
    const questionData = await readJsonFile(questionFile);
    const { questions, meta_questions, calculations, final_analysis_config } = questionData;

    if (!final_analysis_config || !final_analysis_config.prompt_template) {
        return res.status(500).json({ message: 'Final analysis prompt template is not configured in the question set.' });
    }
    
    const systemPromptPath = path.resolve(process.cwd(), 'public/questions/ai-prompt.txt');
    const systemPrompt = await fs.readFile(systemPromptPath, 'utf8');

    const { metaText, answersText, calculationsText } = formatDataForPrompt(
        questions, 
        meta_questions, 
        allAnswers, 
        allScores,
        calculations
    );

    let finalPrompt = final_analysis_config.prompt_template;
    finalPrompt = finalPrompt.replace('{meta_text}', metaText || 'Not provided.');
    finalPrompt = finalPrompt.replace('{answers_text}', answersText || 'Not provided.');
    finalPrompt = finalPrompt.replace('{calculations_text}', calculationsText || 'Not provided.');

    const completion = await openai.chat.completions.create({
        model: 'gpt-4-turbo',
        response_format: { type: "json_object" },
        messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: finalPrompt },
        ],
        max_tokens: 4000,
        temperature: 0.5,
    });
    
    const rawContent = completion.choices[0].message.content;
    const jsonContent = JSON.parse(rawContent);
    const report = jsonContent.report;

    res.status(200).json({ report });

  } catch (error) {
    console.error('Error in final-analysis endpoint:', error);
    res.status(500).json({ 
      message: 'Internal Server Error', 
      error: error.message 
    });
  }
}
