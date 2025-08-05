import React, { useState, useEffect } from "react";

function App() {
  const [sections, setSections] = useState([]); // [{sectionName, questions: []}]
  const [answers, setAnswers] = useState({}); // {sectionIdx-questionIdx: answer}
  const [scores, setScores] = useState({});   // {sectionIdx-questionIdx: score}
  const [loading, setLoading] = useState({}); // {sectionIdx-questionIdx: bool}
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState({}); // {sectionIdx: bool}
  const [aiPrompt, setAiPrompt] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [projectId, setProjectId] = useState("");
  const [currentLanguage, setCurrentLanguage] = useState("en");
  const [translating, setTranslating] = useState(false);

  const languages = [
    { code: "en", name: "English" },
    { code: "de", name: "Deutsch" },
    { code: "ru", name: "Русский" }
  ];

  console.log("App component mounted");

  // Load questions, prompt, and API key
  useEffect(() => {
    console.log("useEffect triggered - loading data");
    
    // Debug: Log environment variables
    console.log("Environment variables:", {
      REACT_APP_GPT_KEY: process.env.REACT_APP_GPT_KEY,
      REACT_APP_PROJECT_ID: process.env.REACT_APP_PROJECT_ID,
      NODE_ENV: process.env.NODE_ENV,
      allEnvVars: process.env
    });

    Promise.all([
      loadQuestionsForLanguage(currentLanguage),
      fetch("/aiprompt.txt").then((res) => res.text()),
      // Try to get API key from environment variable first, then fall back to file
      Promise.resolve().then(() => {
        console.log("Checking for REACT_APP_GPT_KEY:", process.env.REACT_APP_GPT_KEY);
        if (process.env.REACT_APP_GPT_KEY) {
          console.log("Using environment variable for API key");
          const key = process.env.REACT_APP_GPT_KEY;
          const keyLength = key.length;
          const halfLength = Math.floor(keyLength / 2);
          console.log(`API key from env - Length: ${keyLength}, First half: ${key.substring(0, halfLength)}...`);
          console.log(`API key details - Start: "${key.substring(0, 10)}", End: "${key.substring(keyLength - 10)}"`);
          console.log(`API key contains spaces: ${key.includes(' ')}`);
          console.log(`API key contains newlines: ${key.includes('\n')}`);
          console.log("SOURCE: Environment Variable");
          return key;
        } else {
          console.log("Environment variable not found, falling back to key.txt file");
          return fetch("/key.txt").then((res) => {
            console.log("Loading key.txt file");
            return res.text();
          }).then(keyText => {
            console.log("SOURCE: key.txt file");
            return keyText;
          });
        }
      })
    ]).then(([questions, promptText, keyText]) => {
      console.log("All data loaded successfully");
      console.log("Questions count:", questions.length);
      console.log("Prompt length:", promptText.length);
      console.log("Loaded API key length:", keyText ? keyText.length : 0);
      
      if (keyText) {
        const keyLength = keyText.length;
        const halfLength = Math.floor(keyLength / 2);
        console.log(`API key loaded - Length: ${keyLength}, First half: ${keyText.substring(0, halfLength)}...`);
      }
      
      // Get project ID from environment or use default
      const projectId = process.env.REACT_APP_PROJECT_ID || "proj_1hNKc2pZ058vN4dqwCDO9o9T";
      console.log("Using project ID:", projectId);
      
      // Group by cluster_name
      const sectionMap = {};
      questions.forEach(q => {
        if (!sectionMap[q.cluster_name]) sectionMap[q.cluster_name] = [];
        sectionMap[q.cluster_name].push(q);
      });
      // Convert to array and sort questions in each section
      const sectionArr = Object.entries(sectionMap).map(([section, questions]) => ({
        section,
        questions: questions.sort((a, b) => a.position_in_cluster - b.position_in_cluster)
      }));
      console.log("Sections created:", sectionArr.length);
      setSections(sectionArr);
      // Set all sections to collapsed by default
      setExpanded(Object.fromEntries(sectionArr.map((_, idx) => [idx, false])));
      setAiPrompt(promptText);
      setApiKey(keyText.trim());
      setProjectId(projectId);
      console.log("State updated with loaded data");
      
      // Test API key with a simple call
      console.log("Testing API key...");
      fetch("https://api.openai.com/v1/models", {
        headers: {
          "Authorization": `Bearer ${keyText.trim()}`,
        },
      })
      .then(testResponse => {
        console.log("API test response status:", testResponse.status);
        if (testResponse.ok) {
          console.log("API key is valid!");
        } else {
          console.log("API key test failed:", testResponse.status, testResponse.statusText);
        }
      })
      .catch(err => {
        console.error("API test error:", err);
      });
    }).catch((err) => {
      console.error("Error loading data:", err);
      setError("Failed to load questions, prompt, or API key.");
    });
  }, [currentLanguage]);

  // Helper to get a unique key for each question
  const qKey = (sectionIdx, questionIdx) => `${sectionIdx}-${questionIdx}`;

  const handleAnswerChange = (sectionIdx, questionIdx, value) => {
    setAnswers((prev) => ({ ...prev, [qKey(sectionIdx, questionIdx)]: value }));
  };

  const evaluateAnswer = async (sectionIdx, questionIdx) => {
    console.log(`Evaluating answer for section ${sectionIdx}, question ${questionIdx}`);
    console.log("Current API key length:", apiKey.length);
    
    const q = sections[sectionIdx].questions[questionIdx];
    const key = qKey(sectionIdx, questionIdx);
    let answer = answers[key];
    let userPrompt = `Question: ${q.text}\n`;
    // Handle answer formatting by type
    if (q.question_type === "yes-no") {
      userPrompt += `answer = ${answer}`;
    } else if (q.question_type === "numeric") {
      userPrompt += `answer = ${answer}`;
    } else {
      userPrompt += `Answer: ${answer}`;
    }
    
    console.log("User prompt:", userPrompt);
    console.log("Question type:", q.question_type);
    
    setLoading((prev) => ({ ...prev, [key]: true }));
    setError("");
    try {
      // Determine which prompt to use
      let systemPrompt;
      if (q.prompt) {
        // Use custom prompt if provided
        systemPrompt = q.prompt;
        console.log("Using custom prompt from JSON");
      } else if (q.prompt_add) {
        // Use standard prompt + additional prompt
        systemPrompt = aiPrompt + " " + q.prompt_add;
        console.log("Using standard prompt + additional prompt");
      } else {
        // Use standard prompt
        systemPrompt = aiPrompt;
        console.log("Using standard prompt");
      }
      
      // Add location context to all prompts
      const locationAnswer = getLocationAnswer();
      let locationContext = "";
      if (locationAnswer && sectionIdx > 0) { // Skip location context for the location question itself
        locationContext = `Location context: ${locationAnswer}. `;
      }
      systemPrompt = locationContext + systemPrompt;
      
      console.log("Final system prompt length:", systemPrompt.length);
      console.log("Location context added:", locationContext);
      console.log("Making API call to OpenAI...");
      const response = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model: "gpt-4o-mini",
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userPrompt },
          ],
          max_tokens: 20,
        }),
      });
      const data = await response.json();
      console.log("OpenAI response received:", data);
      if (data.error) throw new Error(data.error.message);
      // For yes-no, set score directly
      if (q.question_type === "yes-no") {
        const score = answer === "yes" ? 100 : 0;
        console.log(`Yes/No question - Setting score to: ${score}`);
        setScores((prev) => ({ ...prev, [key]: score }));
      } else {
        // Try to extract a number from the response
        const content = data.choices[0].message.content;
        console.log("OpenAI response content:", content);
        const match = content.match(/\d{1,3}/);
        let score = match ? Math.min(100, Math.max(0, parseInt(match[0], 10))) : null;
        console.log(`Extracted score: ${score}`);
        setScores((prev) => ({ ...prev, [key]: score }));
      }
    } catch (err) {
      console.error("Error in evaluateAnswer:", err);
      setError("Error: " + err.message);
    }
    setLoading((prev) => ({ ...prev, [key]: false }));
  };

  // Count all questions
  const totalQuestions = sections.reduce((sum, sec) => sum + (sec.questions?.length || 0), 0);
  const allAnswered = totalQuestions > 0 && Object.keys(scores).length === totalQuestions;
  const avgScore = totalQuestions ? (Object.values(scores).reduce((a, b) => a + (b || 0), 0) / totalQuestions).toFixed(2) : 0;

  const toggleSection = (idx) => {
    setExpanded((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  // Get location answer from the first question
  const getLocationAnswer = () => {
    // Find the location question answer (first question in the first section)
    if (sections.length > 0 && sections[0].questions.length > 0) {
      const locationKey = qKey(0, 0); // First question in first section
      return answers[locationKey] || "";
    }
    return "";
  };

  // Translate JSON using ChatGPT
  const translateJSON = async (jsonData, targetLanguage) => {
    setTranslating(true);
    setError("");
    
    try {
      const languageNames = {
        "en": "English",
        "de": "German", 
        "ru": "Russian"
      };
      
      const prompt = `Translate the following JSON fields to ${languageNames[targetLanguage]}. Only translate the "id", "text", and "cluster" fields. Keep all other fields unchanged. Return only the JSON without any explanation or markdown formatting:

${JSON.stringify(jsonData, null, 2)}`;

      const response = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model: "gpt-4o-mini",
          messages: [
            { role: "system", content: "You are a JSON translator. Translate only the specified fields and return valid JSON. Do not add any explanations, markdown formatting, or extra text. Return only the JSON object." },
            { role: "user", content: prompt },
          ],
          max_tokens: 4000,
        }),
      });

      const data = await response.json();
      if (data.error) throw new Error(data.error.message);
      
      let translatedContent = data.choices[0].message.content.trim();
      
      // Clean up the response - remove markdown formatting if present
      if (translatedContent.startsWith('```json')) {
        translatedContent = translatedContent.replace(/^```json\s*/, '').replace(/\s*```$/, '');
      } else if (translatedContent.startsWith('```')) {
        translatedContent = translatedContent.replace(/^```\s*/, '').replace(/\s*```$/, '');
      }

      // Attempt to fix common JSON formatting issues: unquoted keys, single quotes, and trailing commas
      let cleanedContent = translatedContent
        // wrap unquoted property names in double quotes
        .replace(/([{,]\s*)([A-Za-z0-9_]+)\s*:/g, '$1"$2":')
        // convert single-quoted strings to double-quoted
        .replace(/'([^']*)'/g, '"$1"')
        // remove trailing commas before } or ]
        .replace(/,\s*(\}|])/g, '$1');

      // Remove stray newline characters that may break JSON strings
      cleanedContent = cleanedContent.replace(/[\r\n]+/g, ' ');

      // Ensure even number of double quotes for valid JSON
      const quoteMatches = cleanedContent.match(/"/g) || [];
      if (quoteMatches.length % 2 !== 0) {
        cleanedContent = cleanedContent.trim();
        if (!cleanedContent.endsWith('"')) {
          cleanedContent += '"';
        }
      }

      console.log("Raw ChatGPT response:", translatedContent.substring(0, 200) + "...");

      try {
        const translatedJSON = JSON.parse(cleanedContent);
        console.log("Translation completed for:", targetLanguage);
        return translatedJSON;
      } catch (parseError) {
        console.error("JSON parse error:", parseError);
        console.error("Failed to parse:", translatedContent);
        throw new Error(`JSON parsing failed: ${parseError.message}`);
      }
      
    } catch (err) {
      console.error("Translation error:", err);
      setError("Translation failed: " + err.message);
      return null;
    } finally {
      setTranslating(false);
    }
  };

  // Helper to deep-clone questions and translate only specific fields
  const translateFields = async (questionsArray, language) => {
    const cloned = JSON.parse(JSON.stringify(questionsArray));
    const uniqueValues = [
      ...new Set(cloned.flatMap(q => [q.text, q.cluster, q.cluster_name]))
    ];
    const translatedResults = await translateJSON(uniqueValues, language);
    const translationMap = uniqueValues.reduce((map, orig, idx) => {
      map[orig] = translatedResults[idx];
      return map;
    }, {});
    cloned.forEach(q => {
      if (translationMap[q.text]) q.text = translationMap[q.text];
      if (translationMap[q.cluster]) q.cluster = translationMap[q.cluster];
      if (translationMap[q.cluster_name]) q.cluster_name = translationMap[q.cluster_name];
    });
    return cloned;
  };

  // Helper to save JSON data as a file for reuse
  const saveJSONFile = (data, filename) => {
    const jsonStr = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  // Load questions for specific language
  const loadQuestionsForLanguage = async (language) => {
    try {
      // First try to load existing translated file
      const translatedFileName = language === "en" ? "questions2.json" : `questions2.${language}.json`;
      
      try {
        const response = await fetch(`/${translatedFileName}`);
        if (response.ok) {
          console.log(`Loading existing translated file: ${translatedFileName}`);
          const questions = await response.json();
          return questions;
        }
      } catch (err) {
        console.log(`No existing translated file found: ${translatedFileName}`);
      }

      // If no translated file exists, load original and translate only fields
      if (language !== "en") {
        console.log(`Translating specific fields to ${language}...`);
        const originalResponse = await fetch("/questions2.json");
        const originalQuestions = await originalResponse.json();
        const translatedQuestions = await translateFields(originalQuestions, language);
        // Save translated JSON file for future use
        saveJSONFile(translatedQuestions, translatedFileName);
        return translatedQuestions;
      }
      // Fallback to original English
      const response = await fetch("/questions2.json");
      return await response.json();
      
    } catch (err) {
      console.error("Error loading questions:", err);
      setError("Failed to load questions");
      return [];
    }
  };

  // Handle language change
  const handleLanguageChange = async (newLanguage) => {
    if (newLanguage === currentLanguage) return;
    
    setCurrentLanguage(newLanguage);
    setSections([]);
    setAnswers({});
    setScores({});
    setExpanded({});
    
    const questions = await loadQuestionsForLanguage(newLanguage);
    if (questions.length > 0) {
      // Group by cluster_name
      const sectionMap = {};
      questions.forEach(q => {
        if (!sectionMap[q.cluster_name]) sectionMap[q.cluster_name] = [];
        sectionMap[q.cluster_name].push(q);
      });
      // Convert to array and sort questions in each section
      const sectionArr = Object.entries(sectionMap).map(([section, questions]) => ({
        section,
        questions: questions.sort((a, b) => a.position_in_cluster - b.position_in_cluster)
      }));
      setSections(sectionArr);
      setExpanded(Object.fromEntries(sectionArr.map((_, idx) => [idx, false])));
    }
  };

  // Render input by question type
  const renderInput = (q, sectionIdx, questionIdx, key) => {
    if (q.question_type === "yes-no") {
      return (
        <div style={{ marginBottom: 8 }}>
          <label style={{ marginRight: 16 }}>
            <input
              type="radio"
              name={`yesno-${key}`}
              value="yes"
              checked={answers[key] === "yes"}
              onChange={() => handleAnswerChange(sectionIdx, questionIdx, "yes")}
            />
            Yes
          </label>
          <label>
            <input
              type="radio"
              name={`yesno-${key}`}
              value="no"
              checked={answers[key] === "no"}
              onChange={() => handleAnswerChange(sectionIdx, questionIdx, "no")}
            />
            No
          </label>
        </div>
      );
    } else if (q.question_type === "numeric") {
      return (
        <input
          type="number"
          style={{
            width: 120,
            borderRadius: 8,
            border: "1px solid #cfd8dc",
            padding: 8,
            fontSize: 15,
            fontFamily: "inherit",
            marginBottom: 8,
            background: "#f6f8fa"
          }}
          value={answers[key] || ""}
          onChange={e => handleAnswerChange(sectionIdx, questionIdx, e.target.value)}
          placeholder="Enter number"
        />
      );
    } else {
      // open-ended
      return (
        <textarea
          rows={3}
          style={{
            width: "100%",
            borderRadius: 8,
            border: "1px solid #cfd8dc",
            padding: 10,
            fontSize: 15,
            fontFamily: "inherit",
            marginBottom: 8,
            background: "#f6f8fa",
            resize: "vertical"
          }}
          value={answers[key] || ""}
          onChange={e => handleAnswerChange(sectionIdx, questionIdx, e.target.value)}
          placeholder="Type your answer here..."
        />
      );
    }
  };

  console.log("Rendering app with sections:", sections.length);

  return (
    <div style={{
      minHeight: "100vh",
      background: "#f8f9fb",
      fontFamily: "'Segoe UI', 'Roboto', 'Arial', sans-serif",
      padding: 0,
      margin: 0
    }}>
      {/* Language Selector */}
      <div style={{
        position: "fixed",
        top: 16,
        left: 16,
        zIndex: 1000,
        background: "#fff",
        borderRadius: 8,
        padding: "8px 12px",
        boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
        border: "1px solid #e3e7ef"
      }}>
        <select
          value={currentLanguage}
          onChange={(e) => handleLanguageChange(e.target.value)}
          disabled={translating}
          style={{
            border: "none",
            background: "transparent",
            fontSize: 14,
            fontWeight: 600,
            color: "#1a2340",
            cursor: "pointer",
            outline: "none"
          }}
        >
          {languages.map(lang => (
            <option key={lang.code} value={lang.code}>
              {lang.name}
            </option>
          ))}
        </select>
        {translating && (
          <span style={{ marginLeft: 8, fontSize: 12, color: "#666" }}>
            Translating...
          </span>
        )}
      </div>

      <div style={{
        maxWidth: 700,
        margin: "0 auto",
        padding: "32px 16px 0 16px"
      }}>
        {/* Logo and subtitle */}
        <div style={{
          textAlign: "center",
          marginBottom: 8
        }}>
          <div style={{
            fontSize: 36,
            fontWeight: 700,
            letterSpacing: 1,
            color: "#1a2340",
            fontFamily: "'Segoe UI', 'Roboto', 'Arial', sans-serif"
          }}>
            Predictex AI
          </div>
          <div style={{
            fontSize: 20,
            fontWeight: 400,
            color: "#3a4668",
            marginTop: 4,
            marginBottom: 32,
            letterSpacing: 0.5
          }}>
            SOHO Business Evaluation
          </div>
        </div>
        {error && <div style={{ color: "#b00020", background: "#fff0f0", border: "1px solid #ffd0d0", borderRadius: 6, padding: 10, marginBottom: 16 }}>{error}</div>}
        {sections.length > 0 ? (
          <div>
            {sections.map((section, sectionIdx) => (
              <div key={sectionIdx} style={{ marginBottom: 32 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    cursor: "pointer",
                    background: "#f0f3fa",
                    borderRadius: 8,
                    padding: "12px 18px",
                    fontSize: 20,
                    fontWeight: 600,
                    color: "#1a2340",
                    boxShadow: "0 1px 4px rgba(30,40,90,0.04)",
                    border: "1px solid #e3e7ef"
                  }}
                  onClick={() => toggleSection(sectionIdx)}
                >
                  <span style={{ marginRight: 12, fontSize: 22 }}>
                    {expanded[sectionIdx] ? "▼" : "►"}
                  </span>
                  {section.section}
                </div>
                {expanded[sectionIdx] && (
                  <div style={{ marginTop: 18 }}>
                    {section.questions.map((q, questionIdx) => {
                      const key = qKey(sectionIdx, questionIdx);
                      return (
                        <div key={key} style={{
                          background: "#fff",
                          borderRadius: 12,
                          boxShadow: "0 2px 12px rgba(30,40,90,0.07)",
                          padding: 24,
                          marginBottom: 28,
                          border: "1px solid #e3e7ef"
                        }}>
                          <div style={{ fontSize: 18, fontWeight: 600, color: "#1a2340", marginBottom: 8 }}>
                            Q{questionIdx + 1}: {q.text}
                          </div>
                          <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 10 }}>
                            <i>Type:</i> {q.question_type}
                            <br />
                            <i>Prompt:</i> {q.prompt ? "Custom" : q.prompt_add ? "Standard + Addition" : "Standard"}
                            {q.prompt && <span style={{ color: "#1a2340" }}> - {q.prompt.substring(0, 100)}...</span>}
                            {q.prompt_add && <span style={{ color: "#1a2340" }}> - {q.prompt_add.substring(0, 100)}...</span>}
                          </div>
                          {renderInput(q, sectionIdx, questionIdx, key)}
                          <div style={{ marginTop: 8, display: "flex", alignItems: "center" }}>
                            <button
                              onClick={() => evaluateAnswer(sectionIdx, questionIdx)}
                              disabled={loading[key] || !answers[key]}
                              style={{
                                background: loading[key] ? "#e3e7ef" : "#1a2340",
                                color: loading[key] ? "#888" : "#fff",
                                border: "none",
                                borderRadius: 6,
                                padding: "8px 22px",
                                fontSize: 15,
                                fontWeight: 600,
                                cursor: loading[key] ? "not-allowed" : "pointer",
                                boxShadow: "0 1px 4px rgba(30,40,90,0.06)",
                                transition: "background 0.2s"
                              }}
                            >
                              {loading[key] ? "Evaluating..." : scores[key] ? "Re-evaluate" : "Submit for Evaluation"}
                            </button>
                            {scores[key] !== undefined && (
                              <span style={{ marginLeft: 18, fontWeight: "bold", fontSize: 17, color: "#1a2340" }}>
                                Score: {scores[key]}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div style={{ textAlign: "center", color: "#888", fontSize: 18, marginTop: 40 }}>Translate and loading questions, please wait, it can take a couple of minutes...</div>
        )}
        {allAnswered && (
          <div style={{ borderTop: "2px solid #e3e7ef", marginTop: 32, paddingTop: 24, textAlign: "center" }}>
            <h3 style={{ fontSize: 24, color: "#1a2340", fontWeight: 700, marginBottom: 8 }}>All questions evaluated!</h3>
            <div style={{ fontSize: 20, color: "#3a4668", fontWeight: 500 }}>
              <b>Average Score:</b> {avgScore}
            </div>
          </div>
        )}
        <div style={{ marginTop: 40, fontSize: 13, color: "#b0b8c9", textAlign: "center" }}>
          <div>
            <b>Note:</b> Copyright Predictex AI 2025. All rights reserved. All questions are copyrighted by Predictex AI.
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;