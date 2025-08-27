/**
 * SSE Client for Server-Driven UI
 * 
 * Handles real-time backend communication with connection management:
 * - Automatic reconnection with exponential backoff
 * - Connection health monitoring and recovery
 * - Event parsing and command routing
 */

const SSE_CONFIG = {
  reconnect_delay_base: 1000,    // Base reconnection delay (ms)
  max_reconnect_delay: 30000,    // Maximum reconnection delay (ms)
  reconnect_attempts: 5,         // Max reconnection attempts before giving up
  heartbeat_interval: 30000,     // Heartbeat check interval (ms)
  connection_timeout: 5000,      // Connection establishment timeout (ms)
  event_buffer_size: 100         // Maximum buffered events
};

class SSEClient {
  constructor(endpoint, sessionId) {
    this.endpoint = endpoint;
    this.sessionId = sessionId;
    this.eventSource = null;
    this.connectionState = 'disconnected';  // 'connecting' | 'connected' | 'disconnected' | 'error'
    this.reconnectAttempts = 0;
    this.reconnectTimer = null;
    this.heartbeatTimer = null;
    this.lastEventTime = 0;
    this.eventBuffer = [];
    this.listeners = new Map();
    
    this.stats = {
      connectionsEstablished: 0,
      reconnections: 0,
      eventsReceived: 0,
      commandsProcessed: 0,
      errors: 0,
      lastConnectedAt: null,
      uptime: 0
    };

    // Bind methods to preserve context
    this.handleOpen = this.handleOpen.bind(this);
    this.handleMessage = this.handleMessage.bind(this);
    this.handleError = this.handleError.bind(this);
    this.handleClose = this.handleClose.bind(this);
  }

  /**
   * Connect to SSE endpoint
   * Mathematical guarantee: Connection establishment with timeout
   */
  async connect() {
    if (this.connectionState === 'connecting' || this.connectionState === 'connected') {
      console.warn('[SSEClient] Already connecting or connected');
      return;
    }

    this.connectionState = 'connecting';
    this.emit('connectionStateChange', 'connecting');

    try {
      // Clear any existing connection
      this.disconnect();

      // Construct SSE URL with session ID
      const url = new URL(this.endpoint);
      url.searchParams.set('sessionId', this.sessionId);
      url.searchParams.set('clientId', this.getClientId());

      console.log(`[SSEClient] Connecting to: ${url.toString()}`);

      // Create EventSource with timeout
      this.eventSource = new EventSource(url.toString());
      
      // Set up event handlers
      this.eventSource.onopen = this.handleOpen;
      this.eventSource.onmessage = this.handleMessage;
      this.eventSource.onerror = this.handleError;

      // Setup connection timeout
      const timeoutId = setTimeout(() => {
        if (this.connectionState === 'connecting') {
          console.error('[SSEClient] Connection timeout');
          this.handleConnectionTimeout();
        }
      }, SSE_CONFIG.connection_timeout);

      // Clear timeout on successful connection
      this.once('connected', () => clearTimeout(timeoutId));

    } catch (error) {
      console.error('[SSEClient] Connection failed:', error);
      this.handleConnectionError(error);
    }
  }

  /**
   * Disconnect from SSE endpoint
   */
  disconnect() {
    console.log('[SSEClient] Disconnecting');
    
    // Clear timers
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    // Close EventSource
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    this.connectionState = 'disconnected';
    this.emit('connectionStateChange', 'disconnected');
  }

  /**
   * Handle SSE connection open
   */
  handleOpen(event) {
    console.log('[SSEClient] Connected successfully');
    
    this.connectionState = 'connected';
    this.reconnectAttempts = 0;
    this.stats.connectionsEstablished++;
    this.stats.lastConnectedAt = new Date();
    this.lastEventTime = Date.now();

    // Start heartbeat monitoring
    this.startHeartbeat();

    this.emit('connected', event);
    this.emit('connectionStateChange', 'connected');
  }

  /**
   * Handle SSE message reception
   */
  handleMessage(event) {
    this.lastEventTime = Date.now();
    this.stats.eventsReceived++;

    try {
      // Parse event data
      const data = JSON.parse(event.data);
      
      // Handle different event types
      switch (data.type) {
        case 'heartbeat':
          this.handleHeartbeat(data);
          break;
          
        case 'command':
          this.handleCommand(data);
          break;
          
        case 'batch':
          this.handleBatchCommands(data);
          break;
          
        case 'system':
          this.handleSystemMessage(data);
          break;
          
        default:
          console.warn('[SSEClient] Unknown event type:', data.type);
      }

      // Buffer event for replay on reconnection if needed
      this.bufferEvent(data);

      this.emit('message', data);
      
    } catch (error) {
      console.error('[SSEClient] Error processing message:', error);
      this.stats.errors++;
      this.emit('error', error);
    }
  }

  /**
   * Handle SSE connection error
   */
  handleError(event) {
    console.error('[SSEClient] Connection error:', event);
    this.stats.errors++;
    
    if (this.connectionState !== 'error') {
      this.connectionState = 'error';
      this.emit('connectionStateChange', 'error');
    }

    this.emit('error', event);

    // Attempt reconnection if not manually disconnected
    this.scheduleReconnection();
  }

  /**
   * Handle SSE connection close
   */
  handleClose(event) {
    console.log('[SSEClient] Connection closed');
    
    if (this.connectionState === 'connected') {
      // Unexpected disconnection
      this.connectionState = 'disconnected';
      this.emit('connectionStateChange', 'disconnected');
      this.scheduleReconnection();
    }

    this.emit('close', event);
  }

  /**
   * Handle connection timeout
   */
  handleConnectionTimeout() {
    console.error('[SSEClient] Connection establishment timeout');
    this.connectionState = 'error';
    this.stats.errors++;
    this.disconnect();
    this.scheduleReconnection();
  }

  /**
   * Handle connection error during establishment
   */
  handleConnectionError(error) {
    this.connectionState = 'error';
    this.stats.errors++;
    this.emit('connectionStateChange', 'error');
    this.emit('error', error);
    this.scheduleReconnection();
  }

  /**
   * Schedule reconnection with exponential backoff
   */
  scheduleReconnection() {
    if (this.reconnectAttempts >= SSE_CONFIG.reconnect_attempts) {
      console.error('[SSEClient] Max reconnection attempts reached');
      this.emit('reconnectionFailed');
      return;
    }

    // Calculate delay with exponential backoff and jitter
    const baseDelay = SSE_CONFIG.reconnect_delay_base * Math.pow(2, this.reconnectAttempts);
    const jitter = Math.random() * 1000;  // Add up to 1 second jitter
    const delay = Math.min(baseDelay + jitter, SSE_CONFIG.max_reconnect_delay);

    console.log(`[SSEClient] Scheduling reconnection attempt ${this.reconnectAttempts + 1} in ${delay.toFixed(0)}ms`);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      this.stats.reconnections++;
      this.connect();
    }, delay);

    this.emit('reconnectionScheduled', { attempt: this.reconnectAttempts + 1, delay });
  }

  /**
   * Start heartbeat monitoring
   */
  startHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
    }

    this.heartbeatTimer = setInterval(() => {
      const timeSinceLastEvent = Date.now() - this.lastEventTime;
      
      if (timeSinceLastEvent > SSE_CONFIG.heartbeat_interval * 1.5) {
        console.warn('[SSEClient] Heartbeat timeout detected');
        this.handleError(new Error('Heartbeat timeout'));
      }
    }, SSE_CONFIG.heartbeat_interval);
  }

  /**
   * Handle heartbeat event from server
   */
  handleHeartbeat(data) {
    // Server is alive, update timestamp
    this.lastEventTime = Date.now();
    this.emit('heartbeat', data);
  }

  /**
   * Handle command event from server
   */
  handleCommand(data) {
    if (data.command) {
      this.stats.commandsProcessed++;
      this.emit('command', data.command);
    }
  }

  /**
   * Handle batch of commands from server
   */
  handleBatchCommands(data) {
    if (data.commands && Array.isArray(data.commands)) {
      data.commands.forEach(command => {
        this.stats.commandsProcessed++;
        this.emit('command', command);
      });
    }
  }

  /**
   * Handle system message from server
   */
  handleSystemMessage(data) {
    console.log('[SSEClient] System message:', data.message);
    this.emit('system', data);
  }

  /**
   * Buffer event for potential replay
   */
  bufferEvent(event) {
    // Only buffer non-heartbeat events
    if (event.type !== 'heartbeat') {
      this.eventBuffer.push({
        ...event,
        receivedAt: Date.now()
      });

      // Maintain buffer size
      if (this.eventBuffer.length > SSE_CONFIG.event_buffer_size) {
        this.eventBuffer.shift();
      }
    }
  }

  /**
   * Get client ID from storage
   */
  getClientId() {
    let clientId = sessionStorage.getItem('sse_client_id');
    if (!clientId) {
      clientId = `sse_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('sse_client_id', clientId);
    }
    return clientId;
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
   * Add one-time event listener
   */
  once(event, callback) {
    const wrappedCallback = (...args) => {
      this.off(event, wrappedCallback);
      callback(...args);
    };
    this.on(event, wrappedCallback);
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
          console.error(`[SSEClient] Error in event listener for ${event}:`, error);
        }
      });
    }
  }

  /**
   * Get connection statistics
   */
  getStats() {
    const now = Date.now();
    const uptime = this.stats.lastConnectedAt ? now - this.stats.lastConnectedAt.getTime() : 0;
    
    return {
      ...this.stats,
      connectionState: this.connectionState,
      reconnectAttempts: this.reconnectAttempts,
      eventBufferSize: this.eventBuffer.length,
      timeSinceLastEvent: now - this.lastEventTime,
      uptime: uptime,
      isConnected: this.connectionState === 'connected'
    };
  }

  /**
   * Check if client is healthy
   */
  isHealthy() {
    const timeSinceLastEvent = Date.now() - this.lastEventTime;
    return (
      this.connectionState === 'connected' &&
      timeSinceLastEvent < SSE_CONFIG.heartbeat_interval * 2 &&
      this.stats.errors < 10
    );
  }

  /**
   * Reset client state
   */
  reset() {
    this.disconnect();
    this.reconnectAttempts = 0;
    this.lastEventTime = 0;
    this.eventBuffer = [];
    this.listeners.clear();
    
    this.stats = {
      connectionsEstablished: 0,
      reconnections: 0,
      eventsReceived: 0,
      commandsProcessed: 0,
      errors: 0,
      lastConnectedAt: null,
      uptime: 0
    };
  }
}

export default SSEClient;