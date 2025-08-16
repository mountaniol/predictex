import React, { useState } from 'react';

// Backend API base URL - Using specific IP address
const API_BASE_URL = 'http://192.168.1.50:3004';

interface QuestionData {
  id: string;
  text: string;
  cluster_name: string;
  position_in_cluster: number;
  question_type: string;
}

interface AIProvider {
  name: string;
  models: string[];
}

interface SettingsPanelProps {
  currentFile: string;
  onFileChange: (filename: string) => void;
  questions: QuestionData[];
  onQuestionsChange: (questions: QuestionData[]) => void;
  aiProviders: AIProvider[];
  selectedProvider: string;
  onProviderChange: (provider: string) => void;
  onExpandAll?: () => void;
  onCollapseAll?: () => void;
}

const SettingsPanel: React.FC<SettingsPanelProps> = ({
  currentFile,
  onFileChange,
  questions,
  onQuestionsChange,
  aiProviders,
  selectedProvider,
  onProviderChange,
  onExpandAll,
  onCollapseAll
}) => {
  const [sections, setSections] = useState<string[]>([]);
  const [newSection, setNewSection] = useState<string>('');
  const [showSectionInput, setShowSectionInput] = useState<boolean>(false);
  const [showFileDialog, setShowFileDialog] = useState(false);
  const [availableFiles, setAvailableFiles] = useState<string[]>([]);
  const [fileFilter, setFileFilter] = useState('');
  const [selectedFileInDialog, setSelectedFileInDialog] = useState('');
  const [overallScore, setOverallScore] = useState<number>(0);

  // Calculate overall score based on questions (mock calculation)
  React.useEffect(() => {
    if (questions.length > 0) {
      setOverallScore(Math.round(Math.random() * 100)); // Mock score
    }
  }, [questions]);

  // Initialize sections from questions
  React.useEffect(() => {
    if (questions.length > 0) {
      const sectionsSet = new Set(questions.map(q => q.cluster_name).filter(Boolean));
      const questionSections = Array.from(sectionsSet) as string[];
      setSections(questionSections);
    }
  }, [questions]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      try {
        const text = await file.text();
        const jsonData = JSON.parse(text);
        
        if (jsonData.questions && Array.isArray(jsonData.questions)) {
          onQuestionsChange(jsonData.questions);
          onFileChange(file.name);
          
          // Extract sections from loaded questions
          const sectionsSet = new Set(jsonData.questions.map((q: any) => q.cluster_name as string));
          const loadedSections = Array.from(sectionsSet) as string[];
          setSections(loadedSections);
        }
      } catch (error) {
        alert('Failed to load file. Please check the JSON format.');
      }
    }
  };

  const handleSaveToServer = async () => {
    try {
      const jsonData = {
        version: '1.2',
        settings: {
          labels: { yes: 'Yes', no: 'No', unknown: "I'm not sure", role: 'buyer' }
        },
        questions: questions,
        optional_questions: [],
        final_analysis_config: {}
      };

      const response = await fetch(`${API_BASE_URL}/api/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: currentFile, data: jsonData })
      });

      if (response.ok) {
        alert('File saved successfully!');
      } else {
        alert('Failed to save file to server.');
      }
    } catch (error) {
      alert('Failed to connect to server.');
    }
  };

  const handleDownload = () => {
    const jsonData = {
      version: '1.2',
      settings: {
        labels: { yes: 'Yes', no: 'No', unknown: "I'm not sure", role: 'buyer' }
      },
      questions: questions,
      optional_questions: [],
      final_analysis_config: {}
    };

    const blob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = currentFile;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleAddSection = () => {
    if (newSection.trim() && !sections.includes(newSection.trim())) {
      setSections([...sections, newSection.trim()]);
      setNewSection('');
      setShowSectionInput(false);
    }
  };

  const handleOpenFromServer = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/files`);
      const files = await response.json();
      setAvailableFiles(files);
      setShowFileDialog(true);
      setFileFilter('');
      setSelectedFileInDialog('');
    } catch (error) {
      alert('Failed to load files from server.');
    }
  };

  const handleFileSelect = async (filename: string) => {
    try {
      const fileResponse = await fetch(`${API_BASE_URL}/api/file/${filename}`);
      const jsonData = await fileResponse.json();
      
      onQuestionsChange(jsonData.questions || []);
      onFileChange(filename);
      
      // Extract sections
      const questionsArray = jsonData.questions?.map((q: any) => q.cluster_name as string) || [];
      const sectionsSet = new Set(questionsArray);
      const loadedSections = Array.from(sectionsSet) as string[];
      setSections(loadedSections);
      
      setShowFileDialog(false);
    } catch (error) {
      alert('Failed to load file from server.');
    }
  };

  const filteredFiles = availableFiles.filter(file => 
    file.toLowerCase().includes(fileFilter.toLowerCase())
  );

  return (
    <div className="settings-panel">
      <h2>Settings</h2>
      
      {/* File Information */}
      <div className="file-info">
        <div className="info-item">
          <label>Name:</label>
          <input
            type="text"
            value={currentFile}
            onChange={(e) => onFileChange(e.target.value)}
            className="file-name-input"
          />
        </div>
        <div className="info-item">
          <label>Overall Score:</label>
          <span className="score">{overallScore}</span>
        </div>
      </div>

      {/* File Operations */}
      <div className="file-operations">
        <button onClick={handleOpenFromServer} className="btn btn-secondary">
          Open on server
        </button>
        <button onClick={handleSaveToServer} className="btn btn-primary">
          Save on Server
        </button>
        <label className="btn btn-secondary upload-btn">
          Upload File
          <input
            type="file"
            accept=".json"
            onChange={handleFileUpload}
            style={{ display: 'none' }}
          />
        </label>
        <button onClick={handleDownload} className="btn btn-secondary">
          Download File
        </button>
      </div>

      {/* AI Provider Selection */}
      <div className="ai-provider-section">
        <h3>AI Provider</h3>
        <select
          value={selectedProvider}
          onChange={(e) => onProviderChange(e.target.value)}
          className="provider-select"
        >
          {aiProviders.map((provider) =>
            provider.models.map((model) => (
              <option key={`${provider.name}:${model}`} value={`${provider.name}:${model}`}>
                {provider.name}: {model}
              </option>
            ))
          )}
        </select>
      </div>

      {/* Sections Management */}
      <div className="sections-management">
        <h3>Sections</h3>
        <select className="sections-select" size={Math.min(sections.length + 1, 8)}>
          {sections.map((section, index) => (
            <option key={index} value={section}>
              {section}
            </option>
          ))}
        </select>
        
        {showSectionInput ? (
          <div className="new-section-input">
            <input
              type="text"
              value={newSection}
              onChange={(e) => setNewSection(e.target.value)}
              placeholder="Section name"
              onKeyPress={(e) => e.key === 'Enter' && handleAddSection()}
            />
            <button onClick={handleAddSection} className="btn btn-small">Add</button>
            <button onClick={() => setShowSectionInput(false)} className="btn btn-small">Cancel</button>
          </div>
        ) : (
          <button
            onClick={() => setShowSectionInput(true)}
            className="btn btn-secondary new-section-btn"
          >
            New Section
          </button>
        )}
      </div>

      {/* Statistics */}
      <div className="statistics">
        <div className="stat-item">
          <label>Questions:</label>
          <span>{questions.length}</span>
        </div>
        <div className="stat-item">
          <label>Sections:</label>
          <span>{sections.length}</span>
        </div>
      </div>

      {/* Question List Controls */}
      <div className="question-controls">
        <button
          onClick={onExpandAll}
          className="btn btn-secondary"
          title="Expand all questions in the list"
        >
          Expand All
        </button>
        <button
          onClick={onCollapseAll}
          className="btn btn-secondary"
          title="Collapse all questions in the list"
        >
          Collapse All
        </button>
      </div>

      {/* File Selection Dialog */}
      {showFileDialog && (
        <div className="file-dialog-overlay">
          <div className="file-dialog">
            <h3>Select a file from server</h3>
            <input
              type="text"
              placeholder="Filter files..."
              value={fileFilter}
              onChange={(e) => setFileFilter(e.target.value)}
              className="file-filter-input"
              autoFocus
            />
            <div className="file-list">
              {filteredFiles.map((file) => (
                <div
                  key={file}
                  className={`file-item ${selectedFileInDialog === file ? 'selected' : ''}`}
                  onClick={() => setSelectedFileInDialog(file)}
                  onDoubleClick={() => handleFileSelect(file)}
                >
                  {file}
                </div>
              ))}
              {filteredFiles.length === 0 && (
                <div className="no-files">No files match your filter</div>
              )}
            </div>
            <div className="dialog-buttons">
              <button 
                onClick={() => handleFileSelect(selectedFileInDialog)}
                disabled={!selectedFileInDialog}
                className="btn btn-primary"
              >
                Open
              </button>
              <button 
                onClick={() => setShowFileDialog(false)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SettingsPanel;