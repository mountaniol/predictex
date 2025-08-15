import React, { useState, useEffect } from 'react';
import './App.css';
import SettingsPanel from './components/SettingsPanel';
import QuestionEditor from './components/QuestionEditor';
import QuestionPreview from './components/QuestionPreview';

// Backend API base URL - Using specific IP address
const API_BASE_URL = 'http://192.168.1.50:3004';

interface QuestionData {
  id: string;
  text: string;
  hint?: string;
  info?: string;
  cluster_name: string;
  position_in_cluster: number;
  question_type: string;
  ui?: string;
  options?: Array<{code: string, label: string}>;
  with_other?: boolean;
  other_text_id?: string;
  max_selections?: number;
  ranked?: boolean;
  ai_context?: {
    include_answers?: string[];
    include_meta?: string[];
  };
  prompt_add?: string;
  score?: string;
}

interface AIProvider {
  name: string;
  models: string[];
}

function App() {
  const [currentFile, setCurrentFile] = useState<string>('untitled.json');
  const [questions, setQuestions] = useState<QuestionData[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState<QuestionData | null>(null);
  const [textInput, setTextInput] = useState<string>('');
  const [parseErrors, setParseErrors] = useState<string[]>([]);
  const [aiProviders, setAiProviders] = useState<AIProvider[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [aiScore, setAiScore] = useState<number | null>(null);
  const [aiExplanation, setAiExplanation] = useState<string>('');
  
  // Load available AI providers on component mount
  useEffect(() => {
    loadAIProviders();
  }, []);

  const loadAIProviders = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/providers`);
      const providers = await response.json();
      setAiProviders(providers);
      if (providers.length > 0) {
        setSelectedProvider(`${providers[0].name}:${providers[0].models[0]}`);
      }
    } catch (error) {
      console.error('Failed to load AI providers:', error);
    }
  };

  const parseTextToQuestion = async (text: string): Promise<QuestionData | null> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, provider: selectedProvider })
      });
      
      const result = await response.json();
      
      if (result.success) {
        setParseErrors([]);
        return result.question;
      } else {
        setParseErrors(result.errors || ['Unknown parsing error']);
        return null;
      }
    } catch (error) {
      setParseErrors(['Failed to connect to parser service']);
      return null;
    }
  };

  const evaluateQuestion = async (question: QuestionData) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, provider: selectedProvider })
      });
      
      const result = await response.json();
      
      if (result.success) {
        setAiScore(result.score);
        setAiExplanation(result.explanation);
      } else {
        setAiScore(null);
        setAiExplanation('Evaluation failed: ' + (result.error || 'Unknown error'));
      }
    } catch (error) {
      setAiScore(null);
      setAiExplanation('Failed to connect to evaluation service');
    }
  };

  const handleTextChange = async (text: string) => {
    setTextInput(text);
    
    if (text.trim()) {
      const parsed = await parseTextToQuestion(text);
      setCurrentQuestion(parsed);
    } else {
      setCurrentQuestion(null);
      setParseErrors([]);
    }
  };

  const handleSendToAI = async () => {
    if (currentQuestion && currentQuestion.score !== 'NO') {
      await evaluateQuestion(currentQuestion);
    }
  };

  const handleSaveQuestion = () => {
    if (currentQuestion) {
      setQuestions(prev => [...prev, currentQuestion]);
      setTextInput('');
      setCurrentQuestion(null);
      setAiScore(null);
      setAiExplanation('');
    }
  };

  return (
    <div className="app">
      <div className="app-layout">
        {/* Fixed left panel */}
        <div className="left-panel">
          <SettingsPanel
            currentFile={currentFile}
            onFileChange={setCurrentFile}
            questions={questions}
            onQuestionsChange={setQuestions}
            aiProviders={aiProviders}
            selectedProvider={selectedProvider}
            onProviderChange={setSelectedProvider}
          />
        </div>

        {/* Main content area */}
        <div className="main-content">
          <div className="content-row">
            {/* Question Editor */}
            <div className="question-editor-container">
              <QuestionEditor
                textInput={textInput}
                onTextChange={handleTextChange}
                parseErrors={parseErrors}
                aiScore={aiScore}
                aiExplanation={aiExplanation}
                onSendToAI={handleSendToAI}
                onSaveQuestion={handleSaveQuestion}
                canSendToAI={currentQuestion !== null && parseErrors.length === 0}
                canSave={currentQuestion !== null && parseErrors.length === 0}
              />
            </div>

            {/* Live Preview */}
            <div className="preview-container">
              <QuestionPreview
                question={currentQuestion}
                hasErrors={parseErrors.length > 0}
              />
            </div>
          </div>

          {/* Existing Questions */}
          <div className="questions-list">
            <h3>Questions in this questionnaire:</h3>
            {questions.map((q, index) => (
              <div key={index} className="question-item collapsed">
                <span>id: {q.id}, text: {q.text.substring(0, 50)}...</span>
              </div>
            ))}
            {questions.length === 0 && (
              <p className="no-questions">No questions yet. Create your first question above.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
