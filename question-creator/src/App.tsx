import React, { useState, useEffect } from 'react';
import './App.css';
import SettingsPanel from './components/SettingsPanel';
import QuestionEditor from './components/QuestionEditor';
import QuestionPreview from './components/QuestionPreview';
import { SortableQuestion } from './components/SortableQuestion';
import { getApiBaseUrl, debugLog } from './config';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy
} from '@dnd-kit/sortable';

// Backend API base URL from config
const API_BASE_URL = getApiBaseUrl();

// Log the API URL being used
if (typeof window !== 'undefined') {
  debugLog('API Base URL:', API_BASE_URL);
  debugLog('Current location:', {
    hostname: window.location.hostname,
    protocol: window.location.protocol,
    port: window.location.port,
  });
}

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
  const [collapsedQuestions, setCollapsedQuestions] = useState<Set<string>>(new Set());
  const [lastUsedId, setLastUsedId] = useState<string>('');
  const [questionsPanelHeight, setQuestionsPanelHeight] = useState<number>(300);
  const [leftPanelWidth, setLeftPanelWidth] = useState<number>(300);
  const [isResizingQuestions, setIsResizingQuestions] = useState<boolean>(false);
  const [isResizingLeft, setIsResizingLeft] = useState<boolean>(false);
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(null);
  const [previewAnswer, setPreviewAnswer] = useState<any>(null);
  
  // Setup drag and drop sensors
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );
  
  // Handle drag end
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    
    if (over && active.id !== over.id) {
      setQuestions((items) => {
        const oldIndex = items.findIndex(q => q.id === active.id);
        const newIndex = items.findIndex(q => q.id === over.id);
        return arrayMove(items, oldIndex, newIndex);
      });
    }
  };
  
  // Load available AI providers and config on component mount
  useEffect(() => {
    loadAIProviders();
    loadCurrentConfig();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadAIProviders = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/providers`);
      const providers = await response.json();
      setAiProviders(providers);
    } catch (error) {
      console.error('Failed to load AI providers:', error);
    }
  };

  const loadCurrentConfig = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/config`);
      const config = await response.json();
      if (config.current_selection) {
        setSelectedProvider(config.current_selection);
        console.log('Loaded current provider from config:', config.current_selection);
      }
    } catch (error) {
      console.error('Failed to load current config:', error);
      // Fallback to first provider if config loading fails
      if (aiProviders.length > 0) {
        setSelectedProvider(`${aiProviders[0].name}:${aiProviders[0].models[0]}`);
      }
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

  const evaluateQuestion = async (question: QuestionData, answer?: any) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          question, 
          answer: answer || previewAnswer,
          provider: selectedProvider 
        })
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


  const handleSendToAI = async () => {
    if (currentQuestion && currentQuestion.score !== 'NO') {
      await evaluateQuestion(currentQuestion, previewAnswer);
    }
  };

  const handleSaveQuestion = () => {
    if (currentQuestion) {
      if (editingQuestionId) {
        // Update existing question
        setQuestions(prev => prev.map(q => 
          q.id === editingQuestionId ? currentQuestion : q
        ));
        setEditingQuestionId(null);
      } else {
        // Add new question to bottom in order of creation
        setQuestions(prev => [...prev, currentQuestion]);
        // New questions start collapsed
        setCollapsedQuestions(prev => new Set(prev).add(currentQuestion.id));
      }
      setTextInput('');
      setCurrentQuestion(null);
      setAiScore(null);
      setAiExplanation('');
    }
  };

  const toggleQuestionCollapse = (questionId: string) => {
    setCollapsedQuestions(prev => {
      const newSet = new Set(prev);
      if (newSet.has(questionId)) {
        newSet.delete(questionId);
      } else {
        newSet.add(questionId);
      }
      return newSet;
    });
  };
  
  // Mouse move handler for resizing
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizingQuestions) {
        const newHeight = window.innerHeight - e.clientY;
        // Allow panel to resize freely, from 50px minimum to full screen
        setQuestionsPanelHeight(Math.max(newHeight, 50));
      }
      if (isResizingLeft) {
        setLeftPanelWidth(Math.min(Math.max(e.clientX, 200), window.innerWidth - 400));
      }
    };
    
    const handleMouseUp = () => {
      setIsResizingQuestions(false);
      setIsResizingLeft(false);
    };
    
    if (isResizingQuestions || isResizingLeft) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isResizingQuestions, isResizingLeft]);

  // Generate next ID based on last used ID
  const generateNextId = (): string => {
    if (!lastUsedId) {
      return 'QG01'; // Default first ID
    }

    // Extract prefix and number from ID like SG01, MET.LOC, etc.
    const match = lastUsedId.match(/^([A-Z.]+?)(\d*)$/);
    
    if (match) {
      const prefix = match[1];
      const numStr = match[2];
      
      if (numStr) {
        // Has number, increment it
        const num = parseInt(numStr, 10) + 1;
        const paddedNum = num.toString().padStart(numStr.length, '0');
        return `${prefix}${paddedNum}`;
      } else {
        // No number, add 01
        return `${prefix}01`;
      }
    }
    
    // Fallback
    return 'QG01';
  };

  // Template generators for each question type
  const getTemplate = (type: string): string => {
    const nextId = generateNextId();
    const templates: Record<string, string> = {
      text: `id: ${nextId}
text: What is your primary revenue source?
cluster: Business Basics
position: 1
type: text
hint: Main source of income
prompt: Evaluate based on revenue stability and market position
score: AUTO`,

      textarea: `id: ${nextId}
text: Describe your biggest business challenge
cluster: Risk Assessment
position: 1  
type: textarea
hint: Provide detailed explanation
prompt: Score based on severity and manageability of the challenge
score: AUTO`,

      number: `id: ${nextId}
text: How many employees do you have?
cluster: Company Size
position: 1
type: number
hint: Full-time equivalent employees
prompt: Consider business scale and operational complexity
score: AUTO`,

      'yes-no': `id: ${nextId}
text: Has revenue grown in the last 12 months?
cluster: Financial Health
position: 1
type: yes-no
hint: Compare to previous year
prompt: Score based on growth trajectory and market conditions
score: AUTO`,

      'choice-single': `id: ${nextId}
text: What is your biggest operational risk?
cluster: Risk Assessment
position: 1
type: choice-single
ui: radio
option: Staff shortage
option: Supply chain disruption
option: Technology failure
option: Regulatory changes
option: Other
hint: Select the most significant risk
prompt: Evaluate risk severity and company preparedness
score: AUTO`,

      'choice-multi': `id: ${nextId}
text: Which markets do you operate in?
cluster: Market Position
position: 1
type: choice-multi
option: Local/Regional
option: National
option: International
option: Online only
max_selections: 3
hint: Select all that apply
prompt: Consider market diversification and expansion risks
score: AUTO`
    };

    return templates[type] || templates.text;
  };

  const handleTemplateClick = (type: string) => {
    const template = getTemplate(type);
    setTextInput(template);
    handleTextChange(template);
  };

  // Load question into editor for editing
  const handleEditQuestion = (question: QuestionData) => {
    setEditingQuestionId(question.id);
    
    // Convert question to text format
    const questionText = questionToText(question);
    setTextInput(questionText);
    setCurrentQuestion(question);
    setParseErrors([]);
    setAiScore(null);
    setAiExplanation('');
  };

  // Convert question object to text format (matching the template format)
  const questionToText = (q: QuestionData): string => {
    // Use lowercase keywords to match the template format
    let text = `id: ${q.id}\n`;
    text += `text: ${q.text}\n`;
    text += `cluster: ${q.cluster_name}\n`;
    text += `position: ${q.position_in_cluster}\n`;
    text += `type: ${q.question_type}\n`;
    
    // Add UI if present
    if (q.ui) text += `ui: ${q.ui}\n`;
    
    // Add options in simple format (just the label)
    if (q.options && q.options.length > 0) {
      q.options.forEach(opt => {
        text += `option: ${opt.label}\n`;
      });
    }
    
    // Add max_selections for multi-choice
    if (q.question_type === 'choice-multi' && q.max_selections) {
      text += `max_selections: ${q.max_selections}\n`;
    }
    
    // Add optional fields
    if (q.hint) text += `hint: ${q.hint}\n`;
    if (q.info) text += `info: ${q.info}\n`;
    
    // Add AI context
    if (q.ai_context?.include_answers && q.ai_context.include_answers.length > 0) {
      text += `include: ${q.ai_context.include_answers.join(', ')}\n`;
    }
    
    if (q.ai_context?.include_meta && q.ai_context.include_meta.length > 0) {
      text += `include_meta: ${q.ai_context.include_meta.join(', ')}\n`;
    }
    
    // Add prompt
    if (q.prompt_add) {
      text += `prompt: ${q.prompt_add}\n`;
    }
    
    // Score at the end
    if (q.score) text += `score: ${q.score}\n`;
    
    return text;
  };

  // Expand all questions
  const expandAll = () => {
    setCollapsedQuestions(new Set());
  };

  // Collapse all questions
  const collapseAll = () => {
    const allIds = questions.map(q => q.id);
    setCollapsedQuestions(new Set(allIds));
  };

  // Track last used ID when text changes
  const handleTextChange = async (text: string) => {
    setTextInput(text);
    
    // Extract ID from text to track last used (support both uppercase and lowercase)
    const idMatch = text.match(/^id:\s*([A-Z][A-Z0-9.]*)/im);
    if (idMatch) {
      setLastUsedId(idMatch[1]);
    }
    
    if (text.trim()) {
      const parsed = await parseTextToQuestion(text);
      setCurrentQuestion(parsed);
    } else {
      setCurrentQuestion(null);
      setParseErrors([]);
    }
  };

  return (
    <div className="app">
      <div className="app-layout">
        {/* Resizable left panel */}
        <div className="left-panel" style={{ width: `${leftPanelWidth}px` }}>
          <SettingsPanel
            currentFile={currentFile}
            onFileChange={setCurrentFile}
            questions={questions}
            onQuestionsChange={setQuestions}
            aiProviders={aiProviders}
            selectedProvider={selectedProvider}
            onProviderChange={setSelectedProvider}
            onExpandAll={expandAll}
            onCollapseAll={collapseAll}
          />
          {/* Resize handle for left panel */}
          <div 
            className="resize-handle-vertical"
            onMouseDown={() => setIsResizingLeft(true)}
            title="Drag to resize panel"
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
                onTemplateClick={handleTemplateClick}
                canSendToAI={currentQuestion !== null && parseErrors.length === 0}
                canSave={currentQuestion !== null && parseErrors.length === 0}
              />
            </div>

            {/* Live Preview */}
            <div className="preview-container">
              <QuestionPreview
                question={currentQuestion}
                hasErrors={parseErrors.length > 0}
                onAnswerChange={setPreviewAnswer}
              />
            </div>
          </div>

          {/* Resizable Questions Panel */}
          <div 
            className="questions-list" 
            style={{ height: `${questionsPanelHeight}px` }}
          >
            {/* Resize handle for questions panel */}
            <div 
              className="resize-handle-horizontal"
              onMouseDown={() => setIsResizingQuestions(true)}
              title="Drag to resize panel"
            />
            <h3>Questions in this questionnaire:</h3>
            <div className="questions-container">
              <DndContext 
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={handleDragEnd}
              >
                <SortableContext 
                  items={questions.map(q => q.id)}
                  strategy={verticalListSortingStrategy}
                >
                  {questions.map((q) => (
                    <SortableQuestion
                      key={q.id}
                      question={q}
                      index={questions.indexOf(q)}
                      isCollapsed={collapsedQuestions.has(q.id)}
                      onToggle={() => toggleQuestionCollapse(q.id)}
                      onEdit={handleEditQuestion}
                    />
                  ))}
                </SortableContext>
              </DndContext>
              {questions.length === 0 && (
                <p className="no-questions">No questions yet. Create your first question above.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
