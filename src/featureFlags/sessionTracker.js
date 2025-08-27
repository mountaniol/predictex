/**
 * Session State Tracker
 * 
 * Implements session consistency guarantees from mathematical model:
 * S = session state: U → {thick, thin} × Timestamp
 * 
 * Ensures:
 * - Session mode consistency across requests  
 * - State synchronization during configuration changes
 * - Session tracking for debugging and analytics
 */

class SessionTracker {
    constructor() {
        this.sessions = new Map();  // userId -> sessionData
        this.sessionHistory = new Map();  // userId -> sessionHistory[]
        this.consistencyChecks = 0;
        this.inconsistencyCount = 0;
        this.stateTransitions = new Map();  // track mode changes
        
        this.maxHistorySize = 100;  // Per-user session history limit
        this.sessionTimeout = 24 * 60 * 60 * 1000;  // 24 hours in milliseconds
    }

    /**
     * Initialize or update user session state
     * Mathematical model: S(user) = {mode, timestamp, consistency_hash}
     * 
     * @param {string|number} userId - User identifier
     * @param {string} mode - 'thick' or 'thin' client mode
     * @param {Object} metadata - Additional session metadata
     * @returns {Object} Session state object
     */
    initializeSession(userId, mode, metadata = {}) {
        const timestamp = Date.now();
        const sessionId = this.generateSessionId(userId, timestamp);
        
        const sessionData = {
            userId: String(userId),
            mode: mode,
            timestamp: timestamp,
            sessionId: sessionId,
            initialized: true,
            configVersion: metadata.configVersion || null,
            userAgent: metadata.userAgent || null,
            ipAddress: metadata.ipAddress || null,
            features: metadata.features || {},
            transitionCount: 0,
            lastTransition: null
        };

        // Check for mode transition
        const previousSession = this.sessions.get(String(userId));
        if (previousSession && previousSession.mode !== mode) {
            this.recordModeTransition(userId, previousSession.mode, mode, timestamp);
            sessionData.transitionCount = (previousSession.transitionCount || 0) + 1;
            sessionData.lastTransition = timestamp;
        }

        // Store session state
        this.sessions.set(String(userId), sessionData);
        
        // Add to history
        this.addToSessionHistory(userId, sessionData);
        
        console.log(`[SessionTracker] Initialized session for user ${userId}: ${mode} mode`);
        return sessionData;
    }

    /**
     * Get current session state for user
     * @param {string|number} userId - User identifier
     * @returns {Object|null} Session data or null if not found
     */
    getSessionState(userId) {
        const session = this.sessions.get(String(userId));
        
        if (!session) {
            return null;
        }

        // Check session timeout
        if (this.isSessionExpired(session)) {
            this.expireSession(userId);
            return null;
        }

        return session;
    }

    /**
     * Update session state while maintaining consistency
     * @param {string|number} userId - User identifier
     * @param {Object} updates - State updates to apply
     * @returns {boolean} Whether update was successful
     */
    updateSessionState(userId, updates) {
        const session = this.sessions.get(String(userId));
        if (!session) {
            console.warn(`[SessionTracker] No session found for user ${userId}`);
            return false;
        }

        // Validate state transition
        if ('mode' in updates && updates.mode !== session.mode) {
            if (!this.isValidModeTransition(session.mode, updates.mode)) {
                console.error(`[SessionTracker] Invalid mode transition: ${session.mode} -> ${updates.mode}`);
                return false;
            }
        }

        // Apply updates atomically
        const updatedSession = { 
            ...session, 
            ...updates, 
            timestamp: Date.now() 
        };

        // Record mode transition if applicable
        if ('mode' in updates && updates.mode !== session.mode) {
            this.recordModeTransition(userId, session.mode, updates.mode, updatedSession.timestamp);
            updatedSession.transitionCount = (session.transitionCount || 0) + 1;
            updatedSession.lastTransition = updatedSession.timestamp;
        }

        this.sessions.set(String(userId), updatedSession);
        this.addToSessionHistory(userId, updatedSession);

        console.log(`[SessionTracker] Updated session for user ${userId}`);
        return true;
    }

    /**
     * Verify session consistency against feature flag evaluation
     * Mathematical verification: session.mode ↔ featureFlag.isEnabled
     * 
     * @param {string|number} userId - User identifier
     * @param {boolean} serverDrivenEnabled - Current feature flag result
     * @returns {boolean} Whether session is consistent
     */
    verifySessionConsistency(userId, serverDrivenEnabled) {
        this.consistencyChecks++;
        
        const session = this.getSessionState(userId);
        if (!session) {
            // No session to verify - not an inconsistency
            return true;
        }

        const expectedMode = serverDrivenEnabled ? 'thin' : 'thick';
        const isConsistent = session.mode === expectedMode;

        if (!isConsistent) {
            this.inconsistencyCount++;
            console.warn(`[SessionTracker] Inconsistency detected for user ${userId}: ` +
                        `session.mode=${session.mode}, expected=${expectedMode}`);
            
            // Auto-correct inconsistent session
            this.updateSessionState(userId, { mode: expectedMode });
        }

        return isConsistent;
    }

    /**
     * Record mode transition for analytics
     * @param {string|number} userId - User identifier
     * @param {string} fromMode - Previous mode
     * @param {string} toMode - New mode  
     * @param {number} timestamp - Transition timestamp
     */
    recordModeTransition(userId, fromMode, toMode, timestamp) {
        const transitionKey = `${fromMode}_to_${toMode}`;
        
        if (!this.stateTransitions.has(transitionKey)) {
            this.stateTransitions.set(transitionKey, []);
        }

        this.stateTransitions.get(transitionKey).push({
            userId: String(userId),
            timestamp: timestamp,
            fromMode: fromMode,
            toMode: toMode
        });

        console.log(`[SessionTracker] Mode transition: user ${userId} ${fromMode} -> ${toMode}`);
    }

    /**
     * Validate mode transition (state machine logic)
     * @param {string} fromMode - Current mode
     * @param {string} toMode - Target mode
     * @returns {boolean} Whether transition is valid
     */
    isValidModeTransition(fromMode, toMode) {
        const validModes = ['thick', 'thin'];
        
        // Both modes must be valid
        if (!validModes.includes(fromMode) || !validModes.includes(toMode)) {
            return false;
        }

        // All transitions between thick/thin are valid
        return true;
    }

    /**
     * Check if session has expired
     * @param {Object} session - Session object
     * @returns {boolean} Whether session is expired
     */
    isSessionExpired(session) {
        return (Date.now() - session.timestamp) > this.sessionTimeout;
    }

    /**
     * Expire and clean up session
     * @param {string|number} userId - User identifier
     */
    expireSession(userId) {
        const session = this.sessions.get(String(userId));
        if (session) {
            console.log(`[SessionTracker] Session expired for user ${userId}`);
            this.sessions.delete(String(userId));
            
            // Keep in history for analytics
            this.addToSessionHistory(userId, { ...session, expired: true });
        }
    }

    /**
     * Add session state to history
     * @param {string|number} userId - User identifier
     * @param {Object} sessionData - Session data to add
     */
    addToSessionHistory(userId, sessionData) {
        const userIdStr = String(userId);
        
        if (!this.sessionHistory.has(userIdStr)) {
            this.sessionHistory.set(userIdStr, []);
        }

        const history = this.sessionHistory.get(userIdStr);
        history.push({ ...sessionData, historyTimestamp: Date.now() });

        // Limit history size
        if (history.length > this.maxHistorySize) {
            history.shift();  // Remove oldest entry
        }
    }

    /**
     * Generate unique session identifier
     * @param {string|number} userId - User identifier
     * @param {number} timestamp - Session timestamp
     * @returns {string} Unique session ID
     */
    generateSessionId(userId, timestamp) {
        const random = Math.random().toString(36).substring(2);
        return `sess_${userId}_${timestamp}_${random}`;
    }

    /**
     * Get session analytics and statistics
     * @returns {Object} Session analytics data
     */
    getSessionAnalytics() {
        const activeThickSessions = Array.from(this.sessions.values()).filter(s => s.mode === 'thick').length;
        const activeThinSessions = Array.from(this.sessions.values()).filter(s => s.mode === 'thin').length;
        
        // Calculate transition statistics
        let totalTransitions = 0;
        const transitionStats = {};
        
        for (const [transitionType, transitions] of this.stateTransitions) {
            transitionStats[transitionType] = transitions.length;
            totalTransitions += transitions.length;
        }

        return {
            activeSessions: this.sessions.size,
            activeThickSessions,
            activeThinSessions,
            totalTransitions,
            transitionStats,
            consistencyChecks: this.consistencyChecks,
            inconsistencyCount: this.inconsistencyCount,
            consistencyRate: this.consistencyChecks > 0 ? 
                           (this.consistencyChecks - this.inconsistencyCount) / this.consistencyChecks : 1,
            sessionHistorySize: Array.from(this.sessionHistory.values()).reduce((sum, hist) => sum + hist.length, 0)
        };
    }

    /**
     * Get session history for specific user
     * @param {string|number} userId - User identifier
     * @param {number} limit - Maximum history entries to return
     * @returns {Array} Session history entries
     */
    getUserSessionHistory(userId, limit = 50) {
        const history = this.sessionHistory.get(String(userId)) || [];
        return history.slice(-limit).reverse();  // Most recent first
    }

    /**
     * Clean up expired sessions and old history
     * @returns {number} Number of sessions cleaned up
     */
    cleanup() {
        let cleanedCount = 0;
        const now = Date.now();

        // Clean up expired sessions
        for (const [userId, session] of this.sessions) {
            if (this.isSessionExpired(session)) {
                this.expireSession(userId);
                cleanedCount++;
            }
        }

        // Clean up old transition data (keep last 1000 per type)
        for (const [transitionType, transitions] of this.stateTransitions) {
            if (transitions.length > 1000) {
                this.stateTransitions.set(transitionType, transitions.slice(-1000));
            }
        }

        console.log(`[SessionTracker] Cleanup completed: ${cleanedCount} sessions expired`);
        return cleanedCount;
    }

    /**
     * Reset all session tracking data (for testing)
     */
    reset() {
        this.sessions.clear();
        this.sessionHistory.clear();
        this.stateTransitions.clear();
        this.consistencyChecks = 0;
        this.inconsistencyCount = 0;
        
        console.log(`[SessionTracker] All session data reset`);
    }

    /**
     * Get health status of session tracker
     * @returns {Object} Health status information
     */
    getHealthStatus() {
        const analytics = this.getSessionAnalytics();
        
        return {
            status: analytics.consistencyRate > 0.95 ? 'healthy' : 'degraded',
            active_sessions: analytics.activeSessions,
            consistency_rate: analytics.consistencyRate,
            memory_usage: {
                sessions: this.sessions.size,
                history_entries: analytics.sessionHistorySize,
                transition_records: Array.from(this.stateTransitions.values())
                    .reduce((sum, arr) => sum + arr.length, 0)
            }
        };
    }
}

export default SessionTracker;