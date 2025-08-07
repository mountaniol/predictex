import React, { useContext } from 'react';
import { AppContext } from './App';

const languages = [
  { code: 'en', name: 'English' },
  { code: 'de', name: 'Deutsch' },
  { code: 'ru', name: 'Русский' },
];

const LanguageSelector = ({ onChange }) => {
  const context = useContext(AppContext);
  const { currentLanguage, loading } = context || { currentLanguage: 'en', loading: false };
  const translating = loading;

  return (
    <div style={{
      width: '100%',
      display: 'flex',
      justifyContent: 'center',
      margin: '4px 0 16px 0',
    }}>
      <select
        value={currentLanguage}
        onChange={e => onChange(e.target.value)}
        disabled={translating}
        style={{
          padding: '0 6px',
          fontSize: 12,
          lineHeight: '16px',
          border: 'none',
          background: 'transparent',
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
        <span style={{ marginLeft: 6, fontSize: 11, color: '#666' }}>
          Translating...
        </span>
      )}
    </div>
  );
}

export default LanguageSelector;