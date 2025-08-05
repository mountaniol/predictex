import React, { useState, useEffect } from "react";

function App() {
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [scores, setScores] = useState({});
  const [loading, setLoading] = useState({});
  const [error, setError] = useState("");

  const apiKey = "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"; // <-- Replace with your actual key

  useEffect(() => {
    fetch("/questions.json")
      .then((res) => res.json())
      .then(setQuestions)
      .catch(() => setError("Failed to load questions.json"));
  }, []);

  const handleAnswerChange = (idx, value) => {
    setAnswers((prev) => ({ ...prev, [idx]: value }));
  };

  const evaluateAnswer = async (idx) => {
    const q = questions[idx];
    const answer = answers[idx] || "";
    setLoading((prev) => ({ ...prev, [idx]: true }));
    setError("");
    try {
      const systemPrompt = q.prompt + " " + (q.additional_prompt || "");
      const userPrompt = `Question: ${q.question}\nAnswer: ${answer}`;
      const response = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model: "gpt-3.5-turbo",
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userPrompt },
          ],
          max_tokens: 20,
        }),
      });
      const data = await response.json();
      if (data.error) throw new Error(data.error.message);
      const content = data.choices[0].message.content;
      const match = content.match(/\d{1,3}/);
      let score = match ? Math.min(100, Math.max(1, parseInt(match[0], 10))) : null;
      setScores((prev) => ({ ...prev, [idx]: score }));
    } catch (err) {
      setError("Error: " + err.message);
    }
    setLoading((prev) => ({ ...prev, [idx]: false }));
  };

  const allAnswered = questions.length > 0 && Object.keys(scores).length === questions.length;
  const avgScore = questions.length ? (Object.values(scores).reduce((a, b) => a + (b || 0), 0) / questions.length).toFixed(2) : 0;

  return (
    <div style={{
      minHeight: "100vh",
      background: "#f8f9fb",
      fontFamily: "'Segoe UI', 'Roboto', 'Arial', sans-serif",
      padding: 0,
      margin: 0
    }}>
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
            Pretictex AI
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
        {questions.length > 0 ? (
          <div>
            {questions.map((q, idx) => (
              <div key={idx} style={{
                background: "#fff",
                borderRadius: 12,
                boxShadow: "0 2px 12px rgba(30,40,90,0.07)",
                padding: 24,
                marginBottom: 28,
                border: "1px solid #e3e7ef"
              }}>
                <div style={{ fontSize: 18, fontWeight: 600, color: "#1a2340", marginBottom: 8 }}>
                  Q{idx + 1}: {q.question}
                </div>
                <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 10 }}>
                  <i>Prompt:</i> {q.prompt}
                  <br />
                  <i>Additional:</i> {q.additional_prompt}
                </div>
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
                  value={answers[idx] || ""}
                  onChange={(e) => handleAnswerChange(idx, e.target.value)}
                  disabled={!!scores[idx]}
                  placeholder="Type your answer here..."
                />
                <div style={{ marginTop: 8, display: "flex", alignItems: "center" }}>
                  <button
                    onClick={() => evaluateAnswer(idx)}
                    disabled={loading[idx] || !answers[idx] || !!scores[idx]}
                    style={{
                      background: loading[idx] || !!scores[idx] ? "#e3e7ef" : "#1a2340",
                      color: loading[idx] || !!scores[idx] ? "#888" : "#fff",
                      border: "none",
                      borderRadius: 6,
                      padding: "8px 22px",
                      fontSize: 15,
                      fontWeight: 600,
                      cursor: loading[idx] || !!scores[idx] ? "not-allowed" : "pointer",
                      boxShadow: "0 1px 4px rgba(30,40,90,0.06)",
                      transition: "background 0.2s"
                    }}
                  >
                    {loading[idx] ? "Evaluating..." : scores[idx] ? "Evaluated" : "Submit for Evaluation"}
                  </button>
                  {scores[idx] !== undefined && (
                    <span style={{ marginLeft: 18, fontWeight: "bold", fontSize: 17, color: "#1a2340" }}>
                      Score: {scores[idx]}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ textAlign: "center", color: "#888", fontSize: 18, marginTop: 40 }}>Loading questions...</div>
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
            <b>Note:</b> Your API key is only used in your browser. No data is sent to any server except OpenAI.
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;