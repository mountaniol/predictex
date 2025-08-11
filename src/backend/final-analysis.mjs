import OpenAI from 'openai';

console.log('===== OpenAI Configuration =====');
console.log('API Key exists:', !!process.env.REACT_APP_GPT_KEY);
console.log('API Key length:', process.env.REACT_APP_GPT_KEY?.length);
console.log('Project ID exists:', !!process.env.REACT_APP_PROJECT_ID);
console.log('Project ID:', process.env.REACT_APP_PROJECT_ID);
console.log('================================');

const openai = new OpenAI({
  apiKey: process.env.REACT_APP_GPT_KEY,
  project: process.env.REACT_APP_PROJECT_ID,
  timeout: 300 * 1000, // 5 minutes timeout
});

function formatDataForPrompt(sections, answers, calculations, aiContext) {
    const allQuestions = sections.flatMap(s => s.questions || []);
    const questionMap = new Map(allQuestions.map(q => [q.id, q]));

    let allAnswersText = '';

    // Determine which questions to include based on ai_context
    let questionsToInclude = allQuestions;
    if (aiContext.include_answers && !aiContext.include_answers.includes("all")) {
        questionsToInclude = allQuestions.filter(q => aiContext.include_answers.includes(q.id));
    }

    // Iterate through selected questions
    questionsToInclude.forEach(question => {
        const questionId = question.id;
        let answer = answers[questionId];

        // Handle custom text input override
        if (question.custom_text_input && answers[question.custom_text_input.id]) {
            answer = answers[question.custom_text_input.id];
        }

        if (answer !== undefined && answer !== null && answer !== '') {
            let answerText = answer;

            // For choice questions, find the label if it's not a custom input
            if (!question.custom_text_input || !answers[question.custom_text_input.id]) {
                 if (question.options && typeof answer === 'string') {
                    const option = question.options.find(opt => opt.code === answer);
                    if (option) {
                        answerText = option.label;
                    }
                }
            }
            
            let lineText = `- ${question.text}: ${answerText}`;
            
            // Add score if requested
            if (aiContext.include_scores) {
                const score = calculations[questionId];
                if (score !== undefined && score !== null) {
                    lineText += ` (Risk Score: ${score}/100)`;
                }
            }
            
            allAnswersText += lineText + '\n';
        }
    });

    return { allAnswersText };
}

function extractStructuredData(sections, answers, calculations, aiContext) {
    // Extract only the data needed for structured analysis
    const structuredData = {
        location: answers['MET.LOC'] || 'Unknown',
        industry: answers['MET.IND'] || 'Unknown',
        annual_revenue: answers['MET.REV'] || 'Unknown',
        fte: answers['MET.FTE'] || 'Unknown',
        risk_items: {}
    };

    // Map specific questions to risk flags
    const riskMappings = {
        'SG01': 'business_age',
        'SG02': 'revenue_model_duration', 
        'SG03': 'gross_margin',
        'SG04': 'escrow_payment',
        'SG05': 'pilot_test_drive',
        'SG06': 'revenue_trend',
        'SG07': 'monthly_drops_30',
        'SG08': 'seasonality_wc',
        'SG09': 'deep_discounts',
        'SG10': 'bad_debt_writeoffs',
        'SG11': 'loans_liens',
        'SG12': 'top5_customer_share',
        'SG13': 'customer_contracts_transfer',
        'SG14': 'client_loss_10',
        'SG15': 'inventory_issues',
        'SG16': 'equipment_maintenance',
        'SG17': 'lease_transferability',
        'SG18': 'insurance_policies',
        'SG19': 'transition_support',
        'SG20': 'owner_hours_gt_30h',
        'SG21': 'owner_many_tasks',
        'SG22': 'can_run_without_owner'
    };

    // Only include questions specified in ai_context
    const questionsToInclude = aiContext.include_answers.includes("all")
        ? Object.keys(riskMappings) 
        : aiContext.include_answers;

    questionsToInclude.forEach(questionId => {
        if (riskMappings[questionId]) {
            const answer = answers[questionId];
            if (answer !== undefined && answer !== null && answer !== '') {
                structuredData.risk_items[riskMappings[questionId]] = answer;
            }
        }
    });

    return structuredData;
}

// This is a new handler for our multi-step process.
// It receives a single prompt template and executes it.
export default async function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(405).json({ message: 'Method Not Allowed' });
    }

    try {
        const config = req.appConfig || {};
        console.log('===== API Request Received =====');
        console.log('Request body keys:', Object.keys(req.body));
        
        const {
            section_index, // Index of the section to process
            sections, // All sections from the question set
            answers,
            calculations,
            sections_markdown, // Markdown from previous steps
            overall_score,     // Final score
            final_analysis_config // New config structure
        } = req.body;

        console.log('Extracted parameters:');
        console.log('- section_index:', section_index);
        console.log('- sections length:', sections?.length);
        console.log('- answers keys:', Object.keys(answers || {}));
        console.log('- calculations keys:', Object.keys(calculations || {}));
        console.log('- final_analysis_config keys:', Object.keys(final_analysis_config || {}));
        console.log('================================');

        if (section_index === undefined || !sections || !answers || !calculations || !final_analysis_config) {
            console.log('Validation failed:');
            console.log('- section_index === undefined:', section_index === undefined);
            console.log('- !sections:', !sections);
            console.log('- !answers:', !answers);
            console.log('- !calculations:', !calculations);
            console.log('- !final_analysis_config:', !final_analysis_config);
            return res.status(400).json({ message: 'Missing required parameters for prompt execution.' });
        }

        const sectionConfig = final_analysis_config.sections[section_index];
        if (!sectionConfig) {
            console.log(`Section config not found for index ${section_index}`);
            console.log('Available sections:', final_analysis_config.sections?.map((s, i) => `${i}: ${s.name}`));
            return res.status(400).json({ message: `Section index ${section_index} not found in configuration.` });
        }

        console.log(`Processing section: ${sectionConfig.name}`);
        console.log('Section config:', JSON.stringify(sectionConfig, null, 2));
        
        let requestBody;
        
        // Build the prompt based on configuration
        const basePrompt = final_analysis_config.base_prompt;
        const specificPrompt = sectionConfig.specific_prompt;
        const outputConstraint = sectionConfig.output_constraint;
        
        let fullPrompt = `${basePrompt}\n\n${specificPrompt}\n\n`;
        
        // Add context based on ai_context configuration
        if (sectionConfig.ai_context.format === "structured_json") {
            const structuredData = extractStructuredData(sections, answers, calculations, sectionConfig.ai_context);
            fullPrompt += `Data(JSON): ${JSON.stringify(structuredData)}\n\n`;
        } else {
            const { allAnswersText } = formatDataForPrompt(sections, answers, calculations, sectionConfig.ai_context);
            const location = answers['MET.LOC'] || 'Unknown location';
            
            fullPrompt += `Inputs (verbatim; do not reinterpret):\nAll Answers & Scores:\n${allAnswersText || 'Not provided.'}\n\n`;
            
            if (sectionConfig.ai_context.include_overall_score) {
                fullPrompt += `(Optional) Overall risk score 0–100:\n${overall_score || 'N/A'}\n\n`;
            }
            
            if (sectionConfig.ai_context.include_previous_sections && sections_markdown) {
                fullPrompt = fullPrompt.replace('{sections_markdown}', sections_markdown);
                fullPrompt = fullPrompt.replace('{overall_score}', overall_score || 'N/A');
                fullPrompt = fullPrompt.replace('{location}', location);
            }
        }
        
        fullPrompt += `Output constraint: ${outputConstraint}`;

        const maxRetries = 3;
        let lastError = null;

        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                console.log(`===== [Attempt ${attempt}/${maxRetries}] Sending ${sectionConfig.name} Request to OpenAI =====`);
                
                const modelConfigFromJson = sectionConfig.model_config || {};
                const openaiConfigFromApp = config?.Backend?.openai || {};

                const requestPayload = {
                    model: sectionConfig.model,
                    input: [{ role: "user", content: fullPrompt }],
                    tools: sectionConfig.web_search.enabled ? [{ type: "web_search" }] : undefined,
                    tool_choice: sectionConfig.web_search.enabled ? "auto" : "none",
                    max_output_tokens: modelConfigFromJson.max_output_tokens || openaiConfigFromApp.default_max_tokens || 800,
                    temperature: modelConfigFromJson.temperature || openaiConfigFromApp.default_temperature || 0.3,
                };

                console.log('REQUEST BODY:');
                console.log(JSON.stringify(requestPayload, null, 2));
                console.log("===================================================================");

                const resp = await openai.responses.create(requestPayload);
                
                console.log('FULL OPENAI RESPONSE:');
                console.log(JSON.stringify(resp, null, 2));
                console.log("===================================================================");
                
                const rawContent = resp.output_text;
                
                console.log(`===== [Attempt ${attempt}/${maxRetries}] Received Response from OpenAI =====`);
                console.log('RESPONSE CONTENT:');
                console.log(rawContent);
                console.log("===================================================================");
                
                if (!rawContent) {
                    console.error('No content received from OpenAI API');
                    throw new Error('No content received from OpenAI API');
                }
                
                let report = '';
                let isValidJson = false;

                // Robust parsing
                try {
                    const jsonContent = JSON.parse(rawContent);
                    // Extract content from any key in the JSON (handling any key name)
                    const keys = Object.keys(jsonContent);
                    if (keys.length > 0) {
                        // Take the first key's value, or if it's an object, stringify it
                        const firstKey = keys[0];
                        const content = jsonContent[firstKey];

                        // CRITICAL FIX: Ensure nested objects in the report are stringified
                        if (typeof content === 'string') {
                            report = content;
                        } else {
                            // If the content is an object, it's likely the nested JSON we want to avoid.
                            // We stringify it to see it, but the prompt is what needs fixing.
                            report = JSON.stringify(content, null, 2); 
                        }
                        isValidJson = true;
                    }
                } catch (e) {
                    const jsonMatch = rawContent.match(/```json\s*([\s\S]*?)\s*```/);
                    if (jsonMatch && jsonMatch[1]) {
                        try {
                            const parsed = JSON.parse(jsonMatch[1]);
                            // Extract content from any key in the JSON (handling any key name)
                            const keys = Object.keys(parsed);
                            if (keys.length > 0) {
                                // Take the first key's value, or if it's an object, stringify it
                                const firstKey = keys[0];
                                const content = parsed[firstKey];
                                
                                // CRITICAL FIX: Ensure nested objects in the report are stringified
                                if (typeof content === 'string') {
                                    report = content;
                                } else {
                                    report = JSON.stringify(content, null, 2);
                                }
                                isValidJson = true;
                            }
                        } catch (e2) {
                           // Still not valid
                        }
                    }
                }
                
                if (isValidJson) {
                    console.log(`===== Successfully extracted report for ${sectionConfig.name} =====`);
                    console.log('EXTRACTED REPORT:');
                    console.log(report);
                    console.log("===================================================================");
                    return res.status(200).json({ report });
                } else {
                    console.error("Invalid JSON received from OpenAI:", rawContent);
                    // If JSON is invalid/incomplete, treat it as an error to trigger a retry
                    throw new Error("Invalid or incomplete JSON response from OpenAI.");
                }

            } catch (error) {
                lastError = error;
                console.warn(`[Attempt ${attempt}/${maxRetries}] Request failed with status ${error.status}: ${error.message}`);

                // --- Retry Logic ---
                if (attempt < maxRetries) {
                    const status = error.status;
                    let delay = 0;

                    if (status === 429) { // Too Many Requests
                        const retryAfter = error.headers?.['retry-after'];
                        if (retryAfter) {
                            delay = parseInt(retryAfter, 10) * 1000;
                        } else {
                            delay = (5000 * attempt); // 5s, 10s
                        }
                    } else if (status === 503) { // Service Unavailable
                        delay = 10000; // 10s fixed
                    } else if ([500, 502, 504].includes(status)) { // Server errors
                        delay = (2000 * attempt) + (Math.random() * 1000); // 2s, 4s + jitter
                    } else if (error.message.includes("Invalid or incomplete JSON")) {
                        console.log("Response was not valid JSON. Retrying...");
                        delay = 1000; // Short delay before retrying on content error
                    } else {
                        // For critical errors (400, 401, 403, 404), break immediately
                        console.error('Critical error, not retrying.');
                        break; 
                    }

                    if (delay > 0) {
                        console.log(`Retrying after ${delay.toFixed(0)}ms...`);
                        await new Promise(resolve => setTimeout(resolve, delay));
                        continue;
                    }
                }
                // --- End Retry Logic ---
            }
        }
        
        // If all retries fail
        console.error('All retries failed. Final error:', lastError);
        return res.status(lastError?.status || 500).json({ 
            message: `Error generating analysis after ${maxRetries} attempts`, 
            error: lastError?.message 
        });

    } catch (error) {
        // This outer catch is for errors outside the retry loop (e.g., initial setup)
        console.error('Error in final-analysis endpoint setup:', error);
        res.status(500).json({ message: 'Error generating analysis', error: error.message });
    }
}
