/**
 * Feature Flag Configuration Manager
 * 
 * Handles TOML configuration loading, hot-reload, and validation
 * Implements atomic configuration updates for consistency guarantees
 * 
 * Mathematical properties:
 * - Atomic configuration updates (no partial state)
 * - Configuration validation before activation
 * - Rollback capability to previous valid state
 */

import * as TOML from '@iarna/toml';

class ConfigurationManager {
    constructor(configPath = 'public/featureFlags.toml') {
        this.configPath = configPath;
        this.currentConfig = null;
        this.previousConfig = null;
        this.isWatching = false;
        this.watchInterval = null;
        this.lastModified = null;
        this.validationRules = new Map();
        
        this.setupValidationRules();
    }

    /**
     * Setup configuration validation rules
     * Ensures mathematical constraints are maintained
     */
    setupValidationRules() {
        // Percentage validation (0-100 range)
        this.validationRules.set('percentage', (value) => {
            return typeof value === 'number' && value >= 0 && value <= 100;
        });

        // Rollout strategy validation
        this.validationRules.set('rollout_strategy', (value) => {
            return ['gradual', 'immediate', 'manual'].includes(value);
        });

        // User overrides validation (array of strings)
        this.validationRules.set('user_overrides', (value) => {
            return Array.isArray(value) && value.every(v => typeof v === 'string');
        });

        // AB split validation (0-100 range)
        this.validationRules.set('ab_split', (value) => {
            return typeof value === 'number' && value >= 0 && value <= 100;
        });
    }

    /**
     * Load configuration from TOML file
     * @returns {Promise<Object>} Parsed and validated configuration
     */
    async loadConfiguration() {
        try {
            const fs = await import('fs');
            const configContent = fs.readFileSync(this.configPath, 'utf8');
            const parsedConfig = TOML.parse(configContent);
            
            // Validate configuration structure
            if (!this.validateConfiguration(parsedConfig)) {
                throw new Error('Configuration validation failed');
            }
            
            // Atomic update: store previous config for rollback
            this.previousConfig = this.currentConfig;
            this.currentConfig = parsedConfig;
            
            // Update last modified timestamp
            const stats = fs.statSync(this.configPath);
            this.lastModified = stats.mtime.getTime();
            
            console.log(`[ConfigManager] Configuration loaded successfully`);
            return this.currentConfig;
            
        } catch (error) {
            console.error(`[ConfigManager] Failed to load configuration:`, error);
            
            // Return previous valid configuration if available
            if (this.currentConfig) {
                console.warn(`[ConfigManager] Using previous valid configuration`);
                return this.currentConfig;
            }
            
            // Fallback to minimal safe configuration
            return this.getFallbackConfiguration();
        }
    }

    /**
     * Validate configuration structure and constraints
     * @param {Object} config - Configuration to validate
     * @returns {boolean} Whether configuration is valid
     */
    validateConfiguration(config) {
        try {
            // Check top-level structure
            if (!config.feature_flags || typeof config.feature_flags !== 'object') {
                console.error(`[ConfigManager] Missing or invalid feature_flags section`);
                return false;
            }

            // Validate each feature flag
            for (const [flagName, flagConfig] of Object.entries(config.feature_flags)) {
                if (!this.validateFeatureFlag(flagName, flagConfig)) {
                    return false;
                }
            }

            // Validate performance configuration
            if (config.performance && !this.validatePerformanceConfig(config.performance)) {
                return false;
            }

            // Validate hash function configuration  
            if (config.hash_function && !this.validateHashConfig(config.hash_function)) {
                return false;
            }

            return true;
            
        } catch (error) {
            console.error(`[ConfigManager] Validation error:`, error);
            return false;
        }
    }

    /**
     * Validate individual feature flag configuration
     * @param {string} flagName - Name of the flag
     * @param {Object} flagConfig - Flag configuration object
     * @returns {boolean} Whether flag configuration is valid
     */
    validateFeatureFlag(flagName, flagConfig) {
        // Required fields
        const requiredFields = ['name', 'enabled', 'percentage'];
        for (const field of requiredFields) {
            if (!(field in flagConfig)) {
                console.error(`[ConfigManager] Flag ${flagName} missing required field: ${field}`);
                return false;
            }
        }

        // Validate specific fields using rules
        for (const [field, validator] of this.validationRules) {
            if (field in flagConfig && !validator(flagConfig[field])) {
                console.error(`[ConfigManager] Flag ${flagName} invalid ${field}: ${flagConfig[field]}`);
                return false;
            }
        }

        // Mathematical constraint: percentage rollout consistency
        if (flagConfig.ab_test && flagConfig.ab_split > flagConfig.percentage) {
            console.error(`[ConfigManager] Flag ${flagName} AB split (${flagConfig.ab_split}%) > rollout (${flagConfig.percentage}%)`);
            return false;
        }

        return true;
    }

    /**
     * Validate performance configuration section
     * @param {Object} perfConfig - Performance configuration
     * @returns {boolean} Whether configuration is valid
     */
    validatePerformanceConfig(perfConfig) {
        const numericFields = [
            'hash_cache_size', 
            'config_reload_interval', 
            'session_tracking_enabled',
            'metrics_collection_interval'
        ];

        for (const field of numericFields) {
            if (field in perfConfig && field !== 'session_tracking_enabled') {
                if (typeof perfConfig[field] !== 'number' || perfConfig[field] < 0) {
                    console.error(`[ConfigManager] Invalid performance config ${field}: ${perfConfig[field]}`);
                    return false;
                }
            }
        }

        return true;
    }

    /**
     * Validate hash function configuration
     * @param {Object} hashConfig - Hash function configuration  
     * @returns {boolean} Whether configuration is valid
     */
    validateHashConfig(hashConfig) {
        // Prime multiplier should be a positive integer
        if ('prime_multiplier' in hashConfig) {
            if (!Number.isInteger(hashConfig.prime_multiplier) || hashConfig.prime_multiplier <= 0) {
                console.error(`[ConfigManager] Invalid prime_multiplier: ${hashConfig.prime_multiplier}`);
                return false;
            }
        }

        // Modulo base should be 100 for percentage calculations
        if ('modulo_base' in hashConfig && hashConfig.modulo_base !== 100) {
            console.error(`[ConfigManager] Modulo base must be 100 for percentage calculations`);
            return false;
        }

        return true;
    }

    /**
     * Start watching configuration file for changes
     * Implements hot-reload with atomic updates
     * @param {number} interval - Check interval in milliseconds (default 30s)
     */
    startWatching(interval = 30000) {
        if (this.isWatching) {
            console.warn(`[ConfigManager] Already watching configuration file`);
            return;
        }

        this.isWatching = true;
        this.watchInterval = setInterval(async () => {
            await this.checkForConfigChanges();
        }, interval);

        console.log(`[ConfigManager] Started watching configuration file (${interval}ms interval)`);
    }

    /**
     * Stop watching configuration file
     */
    stopWatching() {
        if (this.watchInterval) {
            clearInterval(this.watchInterval);
            this.watchInterval = null;
        }
        this.isWatching = false;
        console.log(`[ConfigManager] Stopped watching configuration file`);
    }

    /**
     * Check for configuration file changes
     * @returns {Promise<boolean>} Whether configuration was updated
     */
    async checkForConfigChanges() {
        try {
            const fs = await import('fs');
            const stats = fs.statSync(this.configPath);
            const currentModified = stats.mtime.getTime();

            if (currentModified > this.lastModified) {
                console.log(`[ConfigManager] Configuration file changed, reloading...`);
                await this.loadConfiguration();
                
                // Emit configuration change event
                this.emitConfigChange();
                return true;
            }

            return false;
            
        } catch (error) {
            console.error(`[ConfigManager] Error checking file changes:`, error);
            return false;
        }
    }

    /**
     * Rollback to previous configuration
     * Mathematical guarantee: atomic rollback to known good state
     * @returns {boolean} Whether rollback was successful
     */
    rollbackConfiguration() {
        if (!this.previousConfig) {
            console.error(`[ConfigManager] No previous configuration available for rollback`);
            return false;
        }

        console.warn(`[ConfigManager] Rolling back to previous configuration`);
        
        // Atomic swap
        const failedConfig = this.currentConfig;
        this.currentConfig = this.previousConfig;
        this.previousConfig = failedConfig;

        this.emitConfigChange();
        return true;
    }

    /**
     * Get fallback configuration for emergency scenarios
     * @returns {Object} Minimal safe configuration
     */
    getFallbackConfiguration() {
        return {
            feature_flags: {
                server_driven_ui: {
                    name: 'server_driven_ui',
                    enabled: false,  // Safe default: disabled
                    percentage: 0,
                    rollout_strategy: 'manual',
                    user_overrides: [],
                    ab_test: false,
                    emergency_disable: false
                }
            },
            performance: {
                hash_cache_size: 1000,
                config_reload_interval: 30000,
                session_tracking_enabled: false,
                metrics_collection_interval: 60000
            },
            hash_function: {
                prime_multiplier: 37,
                modulo_base: 100,
                salt: 'feature_flags_v1'
            }
        };
    }

    /**
     * Update specific flag configuration at runtime
     * @param {string} flagName - Flag to update
     * @param {Object} updates - Configuration updates
     * @returns {boolean} Whether update was successful
     */
    updateFlag(flagName, updates) {
        if (!this.currentConfig || !this.currentConfig.feature_flags[flagName]) {
            console.error(`[ConfigManager] Flag ${flagName} not found`);
            return false;
        }

        // Validate updates before applying
        const updatedFlag = { ...this.currentConfig.feature_flags[flagName], ...updates };
        if (!this.validateFeatureFlag(flagName, updatedFlag)) {
            console.error(`[ConfigManager] Invalid updates for flag ${flagName}`);
            return false;
        }

        // Atomic update
        this.currentConfig.feature_flags[flagName] = updatedFlag;
        console.log(`[ConfigManager] Updated flag ${flagName}:`, updates);
        
        this.emitConfigChange();
        return true;
    }

    /**
     * Get current configuration
     * @returns {Object} Current configuration object
     */
    getConfiguration() {
        return this.currentConfig;
    }

    /**
     * Emit configuration change event (for integration)
     */
    emitConfigChange() {
        // In browser environment, use CustomEvent
        if (typeof window !== 'undefined') {
            const event = new CustomEvent('featureFlagConfigChanged', {
                detail: { config: this.currentConfig }
            });
            window.dispatchEvent(event);
        }
        
        // For Node.js environment, could use EventEmitter
        console.log(`[ConfigManager] Configuration change event emitted`);
    }

    /**
     * Get configuration statistics
     * @returns {Object} Configuration statistics
     */
    getConfigurationStats() {
        if (!this.currentConfig) {
            return { flagCount: 0, enabledFlags: 0, rolloutFlags: 0 };
        }

        const flags = this.currentConfig.feature_flags;
        const flagCount = Object.keys(flags).length;
        const enabledFlags = Object.values(flags).filter(f => f.enabled).length;
        const rolloutFlags = Object.values(flags).filter(f => f.percentage > 0).length;

        return {
            flagCount,
            enabledFlags,
            rolloutFlags,
            configPath: this.configPath,
            lastModified: this.lastModified,
            isWatching: this.isWatching
        };
    }
}

export default ConfigurationManager;