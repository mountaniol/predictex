import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: process.env.REACT_APP_GPT_KEY,
  project: process.env.REACT_APP_PROJECT_ID,
  timeout: 90 * 1000, // 90 seconds timeout
});

function formatDataForPrompt(meta, sections, answers, calculations) {
    let metaText = '';
    meta.forEach(q => {
        if (q.id === 'MET.SIZE' && answers['MET.SIZE_CUSTOM']) {
            metaText += `- ${q.text}: ${answers['MET.SIZE_CUSTOM']}\n`;
        } else if (answers[q.id]) {
            metaText += `- ${q.text}: ${answers[q.id]}\n`;
        }
    });

    let answersText = '';
    sections.forEach(s => {
        s.questions.forEach(q => {
            if (answers[q.id]) {
                const scoreText = calculations[q.id] ? ` (Score: ${calculations[q.id]})` : '';
                answersText += `- ${q.text}: ${answers[q.id]}${scoreText}\n`;
            }
        });
    });

    let calculationsText = '';
    if (calculations) {
        Object.entries(calculations).forEach(([key, value]) => {
             if (value) { // Check if value is not null or undefined
                calculationsText += `- ${value.label || key}: ${value}\n`;
             }
        });
    }

    return { metaText, answersText, calculationsText };
}

// This is a new handler for our multi-step process.
// It receives a single prompt template and executes it.
export default async function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(405).json({ message: 'Method Not Allowed' });
    }

    try {
        const {
            prompt_template, // A single prompt template string
            meta,
            sections,
            answers,
            calculations,
            sections_markdown, // Markdown from previous steps
            overall_score,     // Final score
        } = req.body;

        if (!prompt_template || !meta || !sections || !answers || !calculations) {
            return res.status(400).json({ message: 'Missing required parameters for prompt execution.' });
        }

        const { metaText, answersText, calculationsText } = formatDataForPrompt(meta, sections, answers, calculations);

        let finalPrompt = prompt_template;
        finalPrompt = finalPrompt.replace('{meta_text}', metaText || 'Not provided.');
        finalPrompt = finalPrompt.replace('{answers_text}', answersText || 'Not provided.');
        finalPrompt = finalPrompt.replace('{calculations_text}', calculationsText || 'Not provided.');
        finalPrompt = finalPrompt.replace('{sections_markdown}', sections_markdown || '');
        finalPrompt = finalPrompt.replace('{overall_score}', overall_score || 'N/A');

        console.log("===== Sending Prompt to OpenAI =====");
        console.log(finalPrompt.substring(0, 400) + "..."); // Log a snippet
        console.log("====================================");

        const resp = await openai.responses.create({
            model: "gpt-4o",
            input: [
                { role: "user", content: finalPrompt }
            ],
            tools: [ { type: "web_search" } ],
            tool_choice: { type: "web_search" },
        });

        console.log("===== Received Response from OpenAI =====");

        const rawContent = resp.output_text;
        let report = '';

        // The robust parsing is still useful as a fallback.
        try {
            const jsonContent = JSON.parse(rawContent);
            report = jsonContent.report;
        } catch (e) {
            const jsonMatch = rawContent.match(/```json\s*([\s\S]*?)\s*```/);
            if (jsonMatch && jsonMatch[1]) {
                try {
                    const parsed = JSON.parse(jsonMatch[1]);
                    report = parsed.report;
                } catch (e2) {
                    report = rawContent;
                }
            } else {
                report = rawContent;
            }
        }
        
        res.status(200).json({ report });

    } catch (error) {
        console.error('Error in final-analysis endpoint:', error);
        res.status(500).json({ message: 'Error generating analysis', error: error.message });
    }
}
