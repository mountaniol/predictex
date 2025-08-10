import React, { useContext } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { AppContext } from './App';

function FinalReport() {
  const { finalReport } = useContext(AppContext);

  if (!finalReport) {
    return null;
  }

  return (
    <div style={{
      marginTop: '40px',
      padding: '20px',
      backgroundColor: '#fff',
      border: '1px solid #e0e0e0',
      borderRadius: '8px',
      boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
    }}>
      <h2 style={{
        fontSize: '24px',
        fontWeight: 'bold',
        marginBottom: '20px',
        color: '#2c3e50',
        borderBottom: '2px solid #e0e0e0',
        paddingBottom: '10px'
      }}>
        Final Analysis Report
      </h2>
      <div 
        className="markdown-body"
        style={{
          minHeight: '600px', // Примерно 30 строк (20px на строку)
          maxHeight: 'none', // Позволяет расти без ограничений
          overflow: 'auto', // Добавляет скролл если нужно
          lineHeight: '1.6',
          fontSize: '14px'
        }}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{finalReport}</ReactMarkdown>
      </div>
    </div>
  );
}

export default FinalReport;

