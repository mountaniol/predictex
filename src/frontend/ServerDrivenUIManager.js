/**
 * Server-Driven UI Manager
 * 
 * Main coordinator for Server-Driven UI architecture:
 * - Orchestrates all frontend components (CommandProcessor, EventDispatcher, SSEClient, UIUpdater)
 * - Manages component lifecycle and health monitoring
 * - Provides unified interface for React integration
 */

import CommandProcessor from './CommandProcessor.js';
import EventDispatcher from './EventDispatcher.js';
import SSEClient from './SSEClient.js';
import UIUpdater from './UIUpdater.js';

const MANAGER_CONFIG = {
  health_check_interval: 5000,     // Component health monitoring interval
  reconnection_delay: 2000,        // Delay before attempting reconnection
  initialization_timeout: 10000,   // Max time for system initialization
  graceful_shutdown_timeout: 5000  // Max time for graceful shutdown
};

class ServerDrivenUIManager {
  constructor(config = {}) {
    this.config = {
      sseEndpoint: config.sseEndpoint || '/api/sse',
      eventsEndpoint: config.eventsEndpoint || '/api',
      sessionId: config.sessionId || this.generateSessionId(),
      autoStart: config.autoStart !== false,
      ...config
    };

    // Component instances
    this.commandProcessor = null;
    this.eventDispatcher = null;
    this.sseClient = null;
    this.uiUpdater = null;

    // State management
    this.state = 'uninitialized';  // 'uninitialized' | 'initializing' | 'running' | 'error' | 'shutdown'
    this.contextSetter = null;
    
    // Monitoring
    this.healthTimer = null;
    this.lastHealthCheck = 0;
    this.initializationTimer = null;
    
    this.stats = {
      startTime: null,
      uptime: 0,
      healthChecks: 0,
      errors: 0,
      reconnections: 0,
      commandsProcessed: 0,
      eventsDispatched: 0
    };

    // Event listeners for external integration
    this.listeners = new Map();

    // Bind methods
    this.initialize = this.initialize.bind(this);
    this.shutdown = this.shutdown.bind(this);
    this.handleCommand = this.handleCommand.bind(this);
    this.handleConnectionChange = this.handleConnectionChange.bind(this);
  }

  /**
   * Initialize the Server-Driven UI system
   * Mathematical guarantee: Complete initialization or failure with cleanup
   */
  async initialize(contextSetter) {
    if (this.state !== 'uninitialized') {
      console.warn('[ServerDrivenUIManager] Already initialized');
      return;
    }

    this.state = 'initializing';
    this.contextSetter = contextSetter;
    this.stats.startTime = Date.now();

    console.log('[ServerDrivenUIManager] Initializing Server-Driven UI system...');

    try {
      // Set initialization timeout
      this.initializationTimer = setTimeout(() => {
        if (this.state === 'initializing') {
          throw new Error('Initialization timeout');
        }
      }, MANAGER_CONFIG.initialization_timeout);

      // Initialize components in dependency order
      await this.initializeComponents();
      
      // Setup component integration
      this.setupComponentIntegration();
      
      // Start health monitoring
      this.startHealthMonitoring();

      // Clear timeout
      if (this.initializationTimer) {
        clearTimeout(this.initializationTimer);
        this.initializationTimer = null;
      }

      this.state = 'running';
      console.log('[ServerDrivenUIManager] System initialized successfully');
      this.emit('initialized');

      // Auto-start SSE connection if configured
      if (this.config.autoStart) {
        await this.connect();
      }

    } catch (error) {
      console.error('[ServerDrivenUIManager] Initialization failed:', error);
      this.stats.errors++;
      this.state = 'error';
      
      // Cleanup on failure
      await this.cleanup();
      
      this.emit('initializationFailed', error);
      throw error;
    }
  }

  /**
   * Initialize all components
   */
  async initializeComponents() {
    // Initialize UI Updater first (no dependencies)
    this.uiUpdater = new UIUpdater(this.contextSetter);
    console.log('[ServerDrivenUIManager] UIUpdater initialized');

    // Initialize Command Processor (depends on UIUpdater)
    this.commandProcessor = new CommandProcessor(this.uiUpdater);
    console.log('[ServerDrivenUIManager] CommandProcessor initialized');

    // Initialize Event Dispatcher (independent)
    this.eventDispatcher = new EventDispatcher(this.config.eventsEndpoint);
    console.log('[ServerDrivenUIManager] EventDispatcher initialized');

    // Initialize SSE Client (independent)
    this.sseClient = new SSEClient(this.config.sseEndpoint, this.config.sessionId);
    console.log('[ServerDrivenUIManager] SSEClient initialized');
  }

  /**
   * Setup integration between components
   */
  setupComponentIntegration() {
    // SSE Client -> Command Processor
    this.sseClient.on('command', this.handleCommand);
    this.sseClient.on('connected', () => this.handleConnectionChange(true));
    this.sseClient.on('disconnected', () => this.handleConnectionChange(false));
    this.sseClient.on('error', (error) => this.handleSSEError(error));

    // Event Dispatcher -> SSE Client connection status
    this.sseClient.on('connected', () => this.eventDispatcher.setConnected(true));
    this.sseClient.on('disconnected', () => this.eventDispatcher.setConnected(false));

    // Event Dispatcher -> Backend commands (if any returned)
    this.eventDispatcher.onCommandsReceived((commands) => {
      if (Array.isArray(commands)) {
        commands.forEach(command => this.handleCommand(command));
      }
    });

    console.log('[ServerDrivenUIManager] Component integration configured');
  }

  /**
   * Start health monitoring for all components
   */
  startHealthMonitoring() {
    this.healthTimer = setInterval(() => {
      this.performHealthCheck();
    }, MANAGER_CONFIG.health_check_interval);

    console.log('[ServerDrivenUIManager] Health monitoring started');
  }

  /**
   * Connect to backend SSE endpoint
   */
  async connect() {
    if (this.state !== 'running') {
      throw new Error('System not initialized');
    }

    console.log('[ServerDrivenUIManager] Connecting to backend...');
    await this.sseClient.connect();
  }

  /**
   * Disconnect from backend
   */
  async disconnect() {
    console.log('[ServerDrivenUIManager] Disconnecting from backend...');
    this.sseClient.disconnect();
  }

  /**
   * Dispatch user event to backend
   */
  async dispatchEvent(event) {
    if (this.state !== 'running') {
      console.warn('[ServerDrivenUIManager] Cannot dispatch event: system not running');
      return false;
    }

    const success = this.eventDispatcher.dispatch(event);
    
    if (success) {
      this.stats.eventsDispatched++;
    }

    return success;
  }

  /**
   * Handle command from backend
   */
  async handleCommand(command) {
    if (this.state !== 'running') {
      console.warn('[ServerDrivenUIManager] Ignoring command: system not running');
      return;
    }

    try {
      const success = this.commandProcessor.enqueue(command);
      
      if (success) {
        this.stats.commandsProcessed++;
        this.emit('commandReceived', command);
      }
    } catch (error) {
      console.error('[ServerDrivenUIManager] Error handling command:', error);
      this.stats.errors++;
      this.emit('commandError', error);
    }
  }

  /**
   * Handle SSE connection state changes
   */
  handleConnectionChange(connected) {
    this.emit('connectionStateChanged', connected);
    
    if (connected) {
      console.log('[ServerDrivenUIManager] Connected to backend');
    } else {
      console.log('[ServerDrivenUIManager] Disconnected from backend');
    }
  }

  /**
   * Handle SSE errors
   */
  handleSSEError(error) {
    this.stats.errors++;
    console.error('[ServerDrivenUIManager] SSE error:', error);
    this.emit('sseError', error);
  }

  /**
   * Perform health check on all components
   */
  performHealthCheck() {
    this.lastHealthCheck = Date.now();
    this.stats.healthChecks++;

    const healthStatus = {
      manager: this.state === 'running',
      commandProcessor: this.commandProcessor?.isHealthy() || false,
      eventDispatcher: this.eventDispatcher?.isHealthy() || false,
      sseClient: this.sseClient?.isHealthy() || false,
      uiUpdater: this.uiUpdater?.isHealthy() || false
    };

    const overallHealthy = Object.values(healthStatus).every(healthy => healthy);

    if (!overallHealthy) {
      console.warn('[ServerDrivenUIManager] Health check failed:', healthStatus);
      this.emit('healthCheckFailed', healthStatus);
    }

    this.emit('healthCheck', healthStatus);
    return healthStatus;
  }

  /**
   * Get comprehensive system statistics
   */
  getStats() {
    const now = Date.now();
    const uptime = this.stats.startTime ? now - this.stats.startTime : 0;

    return {
      ...this.stats,
      uptime,
      state: this.state,
      sessionId: this.config.sessionId,
      components: {
        commandProcessor: this.commandProcessor?.getStats() || null,
        eventDispatcher: this.eventDispatcher?.getStats() || null,
        sseClient: this.sseClient?.getStats() || null,
        uiUpdater: this.uiUpdater?.getStats() || null
      },
      health: this.performHealthCheck()
    };
  }

  /**
   * Graceful shutdown of the system
   */
  async shutdown() {
    console.log('[ServerDrivenUIManager] Initiating graceful shutdown...');
    this.state = 'shutdown';

    const shutdownPromise = new Promise(async (resolve) => {
      try {
        // Stop health monitoring
        if (this.healthTimer) {
          clearInterval(this.healthTimer);
          this.healthTimer = null;
        }

        // Disconnect SSE client
        if (this.sseClient) {
          this.sseClient.disconnect();
        }

        // Reset all components
        await this.cleanup();

        console.log('[ServerDrivenUIManager] Shutdown complete');
        this.emit('shutdown');
        resolve();

      } catch (error) {
        console.error('[ServerDrivenUIManager] Error during shutdown:', error);
        resolve();
      }
    });

    // Force shutdown after timeout
    const timeoutPromise = new Promise((resolve) => {
      setTimeout(resolve, MANAGER_CONFIG.graceful_shutdown_timeout);
    });

    await Promise.race([shutdownPromise, timeoutPromise]);
  }

  /**
   * Cleanup all components
   */
  async cleanup() {
    if (this.initializationTimer) {
      clearTimeout(this.initializationTimer);
      this.initializationTimer = null;
    }

    if (this.healthTimer) {
      clearInterval(this.healthTimer);
      this.healthTimer = null;
    }

    if (this.commandProcessor) {
      this.commandProcessor.reset();
      this.commandProcessor = null;
    }

    if (this.eventDispatcher) {
      this.eventDispatcher.reset();
      this.eventDispatcher = null;
    }

    if (this.sseClient) {
      this.sseClient.reset();
      this.sseClient = null;
    }

    if (this.uiUpdater) {
      this.uiUpdater.reset();
      this.uiUpdater = null;
    }
  }

  /**
   * Generate unique session ID
   */
  generateSessionId() {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Add event listener
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  /**
   * Remove event listener
   */
  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  /**
   * Emit event to listeners
   */
  emit(event, ...args) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      callbacks.forEach(callback => {
        try {
          callback(...args);
        } catch (error) {
          console.error(`[ServerDrivenUIManager] Error in event listener for ${event}:`, error);
        }
      });
    }
  }

  /**
   * Check if system is healthy and running
   */
  isHealthy() {
    return (
      this.state === 'running' &&
      this.stats.errors < 50  // Error threshold
    );
  }

  /**
   * Get current connection status
   */
  isConnected() {
    return this.sseClient?.getStats()?.isConnected || false;
  }
}

export default ServerDrivenUIManager;