import React, { useState, useEffect } from "react";

function App() {
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [scores, setScores] = useState({});
  const [loading, setLoading] = useState({});
  const [error, setError] = useState("");

  // Hardcoded API key
  const apiKey = "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"; // <-- Replace with your actual key

  // Load questions.json from public folder on mount
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
  const totalScore = Object.values(scores).reduce((a, b) => a + (b || 0), 0);
  const avgScore = questions.length ? (totalScore / questions.length).toFixed(2) : 0;

  return (
    <div style={{ maxWidth: 700, margin: "auto", fontFamily: "sans-serif" }}>
      <h2>Q&A Evaluator (No Backend)</h2>
      {error && <div style={{ color: "red", marginBottom: 16 }}>{error}</div>}
      {questions.length > 0 ? (
        <div>
          {questions.map((q, idx) => (
            <div key={idx} style={{ border: "1px solid #ccc", padding: 16, marginBottom: 16 }}>
              <div>
                <b>Q{idx + 1}:</b> {q.question}
              </div>
              <div style={{ fontSize: 13, color: "#555", marginBottom: 4 }}>
                <i>Prompt:</i> {q.prompt}
                <br />
                <i>Additional:</i> {q.additional_prompt}
              </div>
              <textarea
                rows={3}
                style={{ width: "100%" }}
                value={answers[idx] || ""}
                onChange={(e) => handleAnswerChange(idx, e.target.value)}
                disabled={!!scores[idx]}
                placeholder="Type your answer here..."
              />
              <div style={{ marginTop: 8 }}>
                <button
                  onClick={() => evaluateAnswer(idx)}
                  disabled={loading[idx] || !answers[idx] || !!scores[idx]}
                >
                  {loading[idx] ? "Evaluating..." : scores[idx] ? "Evaluated" : "Submit for Evaluation"}
                </button>
                {scores[idx] !== undefined && (
                  <span style={{ marginLeft: 16, fontWeight: "bold" }}>
                    Score: {scores[idx]}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div>Loading questions...</div>
      )}
      {allAnswered && (
        <div style={{ borderTop: "2px solid #333", marginTop: 32, paddingTop: 16 }}>
          <h3>All questions evaluated!</h3>
          <div>
            <b>Total Score:</b> {totalScore}
            <br />
            <b>Average Score:</b> {avgScore}
          </div>
        </div>
      )}
      <div style={{ marginTop: 32, fontSize: 13, color: "#888" }}>
        <div>
          <b>Note:</b> Your API key is only used in your browser. No data is sent to any server except OpenAI.
        </div>
      </div>
    </div>
  );
}

export default App;