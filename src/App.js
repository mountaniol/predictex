import React, { useState } from "react";
import useLoadQuestions from "./useLoadQuestions";
import LanguageSelector from "./LanguageSelector";
import QuestionSection from "./QuestionSection";

function App() {
  const [currentLanguage, setCurrentLanguage] = useState("en");
  const { sections, aiPrompt, apiKey, loading, error } = useLoadQuestions(currentLanguage);

  // Helper to get a unique key for each question
  return (
    <div style={{
      minHeight: "100vh",
      background: "#f8f9fb",
      fontFamily: "'Segoe UI', 'Roboto', 'Arial', sans-serif",
      padding: 0,
      margin: 0
    }}>
      <LanguageSelector
        currentLanguage={currentLanguage}
        onChange={setCurrentLanguage}
        translating={loading}
      />
      <div style={{
        maxWidth: 700,
        margin: "0 auto",
        padding: "32px 16px 0 16px"
      }}>
        <QuestionSection
          sections={sections}
          aiPrompt={aiPrompt}
          apiKey={apiKey}
          loading={loading}
          error={error}
        />
      </div>
    </div>
  );
}

export default App;