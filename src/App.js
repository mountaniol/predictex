import React, { useState } from "react";
import useLoadQuestions from "./useLoadQuestions";
import LanguageSelector from "./LanguageSelector";
import QuestionSection from "./QuestionSection";
import Header from "./Header";
import Footer from "./Footer";

export const AppContext = React.createContext(null);

function App() {
  const [currentLanguage, setCurrentLanguage] = useState("en");
  const { sections, aiPrompt, apiKey, loading, error, labels, calculations } = useLoadQuestions(currentLanguage);

  // Helper to get a unique key for each question
  return (
    <AppContext.Provider value={{
      sections,
      aiPrompt,
      apiKey,
      labels,
      loading,
      error,
      calculations,
      currentLanguage
    }}>
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
          <Header />
          <LanguageSelector
            currentLanguage={currentLanguage}
            onChange={setCurrentLanguage}
            translating={loading}
          />
          <QuestionSection
            sections={sections}
            aiPrompt={aiPrompt}
            apiKey={apiKey}
            loading={loading}
            error={error}
            labels={labels}
          />
          <Footer />
        </div>
      </div>
    </AppContext.Provider>
  );
}

export default App;