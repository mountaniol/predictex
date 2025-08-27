/**
 * Feature Flag Client for Server-Driven UI
 * 
 * Frontend integration for gradual rollout system.
 * Determines whether to use thick client (legacy) or thin client (server-driven UI).
 */

import React, { createContext, useContext, useState, useEffect } from 'react';

// Client modes matching backend enum
const ClientMode = {
  THICK: 'thick',  // Legacy: business logic in frontend
  THIN: 'thin'     // New: server-driven UI
};

// Context for feature flag state
const FeatureFlagContext = createContext();

/**
 * Feature Flag Provider component
 * Wraps the app and provides feature flag state to all children
 */
export const FeatureFlagProvider = ({ children }) => {
  const [clientMode, setClientMode] = useState(ClientMode.THICK);
  const [isLoading, setIsLoading] = useState(true);
  const [userId, setUserId] = useState(null);
  const [sessionId, setSessionId] = useState(null);

  useEffect(() => {
    // Initialize user and session IDs
    initializeIdentifiers();
    
    // Fetch client mode from backend
    fetchClientMode();
  }, []);

  const initializeIdentifiers = () => {
    // Get or create user ID from localStorage
    let storedUserId = localStorage.getItem('userId');
    if (!storedUserId) {
      // Generate new user ID
      storedUserId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('userId', storedUserId);
    }
    setUserId(storedUserId);

    // Create session ID for this session
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    setSessionId(newSessionId);
    sessionStorage.setItem('sessionId', newSessionId);
  };

  const fetchClientMode = async () => {
    try {
      const storedUserId = localStorage.getItem('userId');
      const storedSessionId = sessionStorage.getItem('sessionId');
      
      if (!storedUserId) {
        // Default to thick client if no user ID
        setClientMode(ClientMode.THICK);
        setIsLoading(false);
        return;
      }

      // Call backend to determine client mode
      const response = await fetch('/api/feature-flag/client-mode', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          userId: storedUserId,
          sessionId: storedSessionId
        })
      });

      if (response.ok) {
        const data = await response.json();
        setClientMode(data.mode || ClientMode.THICK);
        
        // Log for monitoring
        console.log(`[FeatureFlag] User ${storedUserId} assigned mode: ${data.mode}`);
      } else {
        // Default to thick client on error
        console.error('[FeatureFlag] Failed to fetch client mode, defaulting to thick');
        setClientMode(ClientMode.THICK);
      }
    } catch (error) {
      console.error('[FeatureFlag] Error fetching client mode:', error);
      setClientMode(ClientMode.THICK);
    } finally {
      setIsLoading(false);
    }
  };

  const value = {
    clientMode,
    isLoading,
    userId,
    sessionId,
    isServerDriven: clientMode === ClientMode.THIN,
    isLegacyMode: clientMode === ClientMode.THICK,
    refreshMode: fetchClientMode
  };

  return (
    <FeatureFlagContext.Provider value={value}>
      {children}
    </FeatureFlagContext.Provider>
  );
};

/**
 * Hook to use feature flag context
 */
export const useFeatureFlags = () => {
  const context = useContext(FeatureFlagContext);
  if (!context) {
    throw new Error('useFeatureFlags must be used within FeatureFlagProvider');
  }
  return context;
};

/**
 * Component that conditionally renders based on client mode
 */
export const FeatureFlaggedComponent = ({ thickComponent, thinComponent, fallback }) => {
  const { clientMode, isLoading } = useFeatureFlags();

  if (isLoading) {
    return fallback || <div>Loading...</div>;
  }

  if (clientMode === ClientMode.THIN) {
    return thinComponent;
  }

  return thickComponent;
};

/**
 * HOC for wrapping components with feature flag logic
 */
export const withFeatureFlags = (ThickComponent, ThinComponent) => {
  return (props) => {
    const { clientMode, isLoading } = useFeatureFlags();

    if (isLoading) {
      return <div>Loading feature configuration...</div>;
    }

    if (clientMode === ClientMode.THIN) {
      return <ThinComponent {...props} />;
    }

    return <ThickComponent {...props} />;
  };
};

/**
 * Utility to check if a specific feature is enabled
 */
export const useFeature = (featureName) => {
  const [isEnabled, setIsEnabled] = useState(false);
  const { userId } = useFeatureFlags();

  useEffect(() => {
    if (!userId) return;

    const checkFeature = async () => {
      try {
        const response = await fetch('/api/feature-flag/check', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            userId,
            flagName: featureName
          })
        });

        if (response.ok) {
          const data = await response.json();
          setIsEnabled(data.enabled);
        }
      } catch (error) {
        console.error(`[FeatureFlag] Error checking feature ${featureName}:`, error);
        setIsEnabled(false);
      }
    };

    checkFeature();
  }, [userId, featureName]);

  return isEnabled;
};

/**
 * A/B Testing hook
 */
export const useABTest = (testName) => {
  const [group, setGroup] = useState(null);
  const { userId } = useFeatureFlags();

  useEffect(() => {
    if (!userId) return;

    const getGroup = async () => {
      try {
        const response = await fetch('/api/feature-flag/ab-test', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            userId,
            testName
          })
        });

        if (response.ok) {
          const data = await response.json();
          setGroup(data.group);
        }
      } catch (error) {
        console.error(`[FeatureFlag] Error getting A/B test group for ${testName}:`, error);
        setGroup('A'); // Default to A
      }
    };

    getGroup();
  }, [userId, testName]);

  return group;
};

/**
 * Admin component for managing feature flags (development only)
 */
export const FeatureFlagAdmin = () => {
  const [flags, setFlags] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFlags();
  }, []);

  const fetchFlags = async () => {
    try {
      const response = await fetch('/api/feature-flag/admin/list');
      if (response.ok) {
        const data = await response.json();
        setFlags(data.flags);
      }
    } catch (error) {
      console.error('[FeatureFlagAdmin] Error fetching flags:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateFlag = async (flagName, updates) => {
    try {
      const response = await fetch('/api/feature-flag/admin/update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          flagName,
          ...updates
        })
      });

      if (response.ok) {
        await fetchFlags(); // Refresh
        console.log(`[FeatureFlagAdmin] Updated ${flagName}`);
      }
    } catch (error) {
      console.error(`[FeatureFlagAdmin] Error updating ${flagName}:`, error);
    }
  };

  const emergencyRollback = async (flagName) => {
    if (!window.confirm(`Are you sure you want to rollback ${flagName}?`)) {
      return;
    }

    try {
      const response = await fetch('/api/feature-flag/admin/rollback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ flagName })
      });

      if (response.ok) {
        await fetchFlags(); // Refresh
        alert(`Emergency rollback completed for ${flagName}`);
      }
    } catch (error) {
      console.error(`[FeatureFlagAdmin] Error during rollback:`, error);
      alert('Rollback failed!');
    }
  };

  if (loading) {
    return <div>Loading feature flags...</div>;
  }

  return (
    <div style={{ padding: '20px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
      <h2>Feature Flag Admin</h2>
      {Object.entries(flags).map(([flagName, flag]) => (
        <div key={flagName} style={{ 
          marginBottom: '20px', 
          padding: '15px', 
          backgroundColor: 'white',
          borderRadius: '4px'
        }}>
          <h3>{flagName}</h3>
          <p>{flag.description}</p>
          
          <div style={{ marginTop: '10px' }}>
            <label>
              <input
                type="checkbox"
                checked={flag.enabled}
                onChange={(e) => updateFlag(flagName, { enabled: e.target.checked })}
              />
              Enabled
            </label>
          </div>
          
          <div style={{ marginTop: '10px' }}>
            <label>
              Percentage: 
              <input
                type="number"
                min="0"
                max="100"
                value={flag.percentage}
                onChange={(e) => updateFlag(flagName, { 
                  percentage: parseInt(e.target.value, 10) 
                })}
                style={{ marginLeft: '10px', width: '60px' }}
              />
              %
            </label>
          </div>
          
          <button
            onClick={() => emergencyRollback(flagName)}
            style={{
              marginTop: '10px',
              padding: '5px 10px',
              backgroundColor: '#dc3545',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Emergency Rollback
          </button>
        </div>
      ))}
    </div>
  );
};

export default {
  FeatureFlagProvider,
  useFeatureFlags,
  FeatureFlaggedComponent,
  withFeatureFlags,
  useFeature,
  useABTest,
  FeatureFlagAdmin,
  ClientMode
};