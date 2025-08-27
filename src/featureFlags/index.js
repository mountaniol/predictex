/**
 * Feature Flag System - Main Entry Point
 * 
 * Integrates all components with mathematical guarantees:
 * - Consistent hash-based user assignment
 * - Atomic configuration updates
 * - Session state consistency tracking
 * - Performance monitoring and health checks
 * 
 * Usage:
 *   import { FeatureFlagSystem } from './featureFlags';
 *   const flags = new FeatureFlagSystem();
 *   await flags.initialize();
 *   const mode = flags.getUserMode(userId);
 */

import FeatureFlagEvaluator from './evaluator.js';
import ConfigurationManager from './configManager.js';
import SessionTracker from './sessionTracker.js';

class FeatureFlagSystem {
    constructor(configPath = 'public/featureFlags.toml') {
        this.evaluator = new FeatureFlagEvaluator();
        this.configManager = new ConfigurationManager(configPath);
        this.sessionTracker = new SessionTracker();
        
        this.initialized = false;
        this.healthChecks = {
            last_check: null,
            status: 'unknown',
            components: {}
        };

        // Bind configuration change handler
        if (typeof window !== 'undefined') {
            window.addEventListener('featureFlagConfigChanged', this.handleConfigChange.bind(this));
        }
    }

    /**
     * Initialize the feature flag system
     * @returns {Promise<boolean>} Whether initialization was successful
     */
    async initialize() {
        try {
            console.log(`[FeatureFlagSystem] Initializing...`);
            
            // Load initial configuration
            const config = await this.configManager.loadConfiguration();
            this.evaluator.loadConfiguration(config);

            // Start configuration watching if enabled
            const reloadInterval = config.performance?.config_reload_interval || 30000;
            this.configManager.startWatching(reloadInterval);

            // Set up periodic cleanup
            this.startPeriodicCleanup();

            this.initialized = true;
            console.log(`[FeatureFlagSystem] Initialization complete`);
            
            return true;
            
        } catch (error) {
            console.error(`[FeatureFlagSystem] Initialization failed:`, error);
            return false;
        }
    }

    /**
     * Get user's client mode (main integration point)
     * @param {string|number} userId - User identifier
     * @param {Object} sessionMetadata - Additional session metadata
     * @returns {string} 'thick' or 'thin' client mode
     */
    getUserMode(userId, sessionMetadata = {}) {
        if (!this.initialized) {
            console.warn(`[FeatureFlagSystem] Not initialized, defaulting to thick client`);
            return 'thick';
        }

        try {
            // Get mode from evaluator
            const mode = this.evaluator.getUserSessionMode(userId);
            
            // Initialize or update session tracking
            this.sessionTracker.initializeSession(userId, mode, sessionMetadata);
            
            // Verify session consistency
            const serverDrivenEnabled = this.evaluator.isFeatureEnabled(userId, 'server_driven_ui');
            this.sessionTracker.verifySessionConsistency(userId, serverDrivenEnabled);
            
            return mode;
            
        } catch (error) {
            console.error(`[FeatureFlagSystem] Error determining user mode:`, error);
            return 'thick';  // Safe fallback
        }
    }

    /**
     * Check if feature is enabled for user
     * @param {string|number} userId - User identifier  
     * @param {string} flagName - Feature flag name
     * @returns {boolean} Whether feature is enabled
     */
    isFeatureEnabled(userId, flagName) {
        if (!this.initialized) {
            return false;
        }

        return this.evaluator.isFeatureEnabled(userId, flagName);
    }

    /**
     * Evaluate multiple features for user (performance optimization)
     * @param {string|number} userId - User identifier
     * @param {string[]} flagNames - Array of flag names
     * @returns {Object} Map of flag names to boolean results
     */
    evaluateMultipleFeatures(userId, flagNames) {
        if (!this.initialized) {
            return Object.fromEntries(flagNames.map(name => [name, false]));
        }

        return this.evaluator.evaluateMultipleFlags(userId, flagNames);
    }

    /**
     * Get A/B test group for user
     * @param {string|number} userId - User identifier
     * @param {string} flagName - Feature flag name
     * @returns {string} 'control' or 'treatment' group
     */
    getABTestGroup(userId, flagName) {
        if (!this.initialized) {
            return 'control';
        }

        return this.evaluator.getABTestGroup(userId, flagName);
    }

    /**
     * Update flag configuration at runtime
     * @param {string} flagName - Flag to update
     * @param {Object} updates - Configuration updates
     * @returns {boolean} Whether update was successful
     */
    updateFlag(flagName, updates) {
        if (!this.initialized) {
            return false;
        }

        return this.configManager.updateFlag(flagName, updates);
    }

    /**
     * Gradual rollout increment
     * @param {string} flagName - Flag to increment
     * @param {number} increment - Percentage increment
     * @returns {boolean} Whether increment was successful
     */
    incrementRollout(flagName, increment = 5) {
        if (!this.initialized) {
            return false;
        }

        this.evaluator.incrementRollout(flagName, increment);
        
        // Update configuration to persist change
        const currentConfig = this.configManager.getConfiguration();
        const flag = currentConfig.feature_flags[flagName];
        if (flag) {
            return this.configManager.updateFlag(flagName, { 
                percentage: Math.min(flag.percentage + increment, 100) 
            });
        }
        
        return false;
    }

    /**
     * Emergency rollback for flag
     * @param {string} flagName - Flag to rollback
     * @returns {boolean} Whether rollback was successful
     */
    emergencyRollback(flagName) {
        if (!this.initialized) {
            return false;
        }

        // Execute rollback in evaluator
        this.evaluator.emergencyRollback(flagName);
        
        // Update configuration
        return this.configManager.updateFlag(flagName, { 
            percentage: 0, 
            emergency_disable: true 
        });
    }

    /**
     * Handle configuration change events
     * @param {CustomEvent} event - Configuration change event
     */
    handleConfigChange(event) {
        if (event.detail && event.detail.config) {
            console.log(`[FeatureFlagSystem] Configuration changed, reloading evaluator`);
            this.evaluator.loadConfiguration(event.detail.config);
        }
    }

    /**
     * Start periodic cleanup processes
     */
    startPeriodicCleanup() {
        // Clean up expired sessions every hour
        setInterval(() => {
            this.sessionTracker.cleanup();
        }, 60 * 60 * 1000);

        // Clean up evaluator cache every 30 minutes
        setInterval(() => {
            // Evaluator cache cleanup if implemented
            const metrics = this.evaluator.getPerformanceMetrics();
            if (metrics.cacheSize > 10000) {
                console.log(`[FeatureFlagSystem] Cache size (${metrics.cacheSize}) exceeding limit, cleanup needed`);
            }
        }, 30 * 60 * 1000);
    }

    /**
     * Get comprehensive system health status
     * @returns {Object} Health status for all components
     */
    getHealthStatus() {
        if (!this.initialized) {
            return {
                status: 'not_initialized',
                timestamp: Date.now(),
                components: {}
            };
        }

        const evaluatorHealth = this.evaluator.getHealthStatus();
        const sessionHealth = this.sessionTracker.getHealthStatus();
        const configStats = this.configManager.getConfigurationStats();

        const overallStatus = 
            evaluatorHealth.status === 'healthy' && 
            sessionHealth.status === 'healthy' ? 'healthy' : 'degraded';

        this.healthChecks = {
            status: overallStatus,
            last_check: Date.now(),
            components: {
                evaluator: evaluatorHealth,
                session_tracker: sessionHealth,
                config_manager: {
                    status: 'healthy',
                    flags_loaded: configStats.flagCount,
                    watching_config: configStats.isWatching
                }
            }
        };

        return this.healthChecks;
    }

    /**
     * Get system metrics and analytics
     * @returns {Object} Comprehensive system metrics
     */
    getSystemMetrics() {
        if (!this.initialized) {
            return { error: 'System not initialized' };
        }

        return {
            evaluator: this.evaluator.getPerformanceMetrics(),
            sessions: this.sessionTracker.getSessionAnalytics(),
            configuration: this.configManager.getConfigurationStats(),
            health: this.healthChecks
        };
    }

    /**
     * Shutdown the feature flag system
     */
    shutdown() {
        console.log(`[FeatureFlagSystem] Shutting down...`);
        
        if (this.configManager) {
            this.configManager.stopWatching();
        }

        this.initialized = false;
        console.log(`[FeatureFlagSystem] Shutdown complete`);
    }
}

// Create default instance for easy usage
let defaultInstance = null;

/**
 * Get or create default feature flag system instance
 * @returns {FeatureFlagSystem} Default instance
 */
export function getFeatureFlagSystem() {
    if (!defaultInstance) {
        defaultInstance = new FeatureFlagSystem();
    }
    return defaultInstance;
}

/**
 * Initialize default instance
 * @returns {Promise<boolean>} Whether initialization was successful
 */
export async function initializeFeatureFlags() {
    const system = getFeatureFlagSystem();
    return await system.initialize();
}

/**
 * Quick access functions using default instance
 */
export function getUserMode(userId, sessionMetadata) {
    return getFeatureFlagSystem().getUserMode(userId, sessionMetadata);
}

export function isFeatureEnabled(userId, flagName) {
    return getFeatureFlagSystem().isFeatureEnabled(userId, flagName);
}

export function getABTestGroup(userId, flagName) {
    return getFeatureFlagSystem().getABTestGroup(userId, flagName);
}

export {
    FeatureFlagSystem,
    FeatureFlagEvaluator,
    ConfigurationManager,
    SessionTracker
};