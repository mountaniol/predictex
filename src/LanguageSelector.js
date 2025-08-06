import React from 'react';

const languages = [
  { code: 'en', name: 'English' },
  { code: 'de', name: 'Deutsch' },
  { code: 'ru', name: 'Русский' },
];

const LanguageSelector = ({ currentLanguage, onChange, translating }) => (
  <div style={{
    position: 'fixed',
    top: 16,
    left: 16,
    zIndex: 1000,
    background: '#fff',
    borderRadius: 8,
    padding: '8px 12px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    border: '1px solid #e3e7ef',
  }}>
    <select
      value={currentLanguage}
      onChange={e => onChange(e.target.value)}
      disabled={translating}
      style={{
        border: 'none',
        background: 'transparent',
        fontSize: 14,
        fontWeight: 600,
        color: '#1a2340',
        cursor: 'pointer',
        outline: 'none',
      }}
    >
      {languages.map(lang => (
        <option key={lang.code} value={lang.code}>
          {lang.name}
        </option>
      ))}
    </select>
    {translating && (
      <span style={{ marginLeft: 8, fontSize: 12, color: '#666' }}>
        Translating...
      </span>
    )}
  </div>
);

export default LanguageSelector;