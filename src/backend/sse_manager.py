"""
Server-Sent Events Manager for real-time client communication.

This module provides a robust SSE communication system following RFC standards
with support for multiple clients per session, thread-safe operations,
and high-performance message delivery.
"""

import threading
import time
import json
import queue
import uuid
import asyncio
from typing import Dict, Set, Optional, Any, List
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

# Configure logging
logger = logging.getLogger(__name__)


# Exception classes for SSE Manager
class AuthenticationError(Exception):
    """Raised when client authentication fails"""
    pass


class InvalidSessionError(Exception):
    """Raised when session ID is invalid or not found"""
    pass


class SSETimeoutError(Exception):
    """Raised when SSE operation times out"""
    pass


class ConnectionStats:
    """Connection statistics and monitoring data"""
    
    def __init__(self):
        self.connections_created = 0
        self.connections_active = 0
        self.messages_sent = 0
        self.bytes_transferred = 0
        self.last_activity = None
        self.error_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary format"""
        return {
            'connections_created': self.connections_created,
            'connections_active': self.connections_active,
            'messages_sent': self.messages_sent,
            'bytes_transferred': self.bytes_transferred,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'error_count': self.error_count
        }


class SSEConnection:
    """Represents a Server-Sent Events connection with event handling"""
    
    def __init__(self, session_id: str, client_id: str):
        self.session_id = session_id
        self.client_id = client_id
        self.connected_at = datetime.now()
        self.last_activity = datetime.now()
        self._is_connected = True
        self._message_handlers = []
        self._message_queue = asyncio.Queue(maxsize=1000)
        self._lock = asyncio.Lock()
    
    def is_connected(self) -> bool:
        """Check if connection is still active"""
        return self._is_connected
    
    def on_message(self, handler):
        """Register message event handler"""
        self._message_handlers.append(handler)
    
    async def send_message(self, message: Dict[str, Any]):
        """Send message to this connection"""
        if not self._is_connected:
            return False
        
        async with self._lock:
            try:
                self._message_queue.put_nowait(message)
                self.last_activity = datetime.now()
                
                # Trigger message handlers
                for handler in self._message_handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(message)
                        else:
                            handler(message)
                    except Exception as e:
                        logger.error(f"Error in message handler: {e}")
                
                return True
            except asyncio.QueueFull:
                logger.warning(f"Message queue full for client {self.client_id}")
                return False
    
    async def get_message(self, timeout: Optional[float] = None):
        """Get next message from queue"""
        try:
            if timeout:
                return await asyncio.wait_for(self._message_queue.get(), timeout=timeout)
            else:
                return await self._message_queue.get()
        except asyncio.TimeoutError:
            raise SSETimeoutError(f"Timeout waiting for message on client {self.client_id}")
    
    async def disconnect(self):
        """Disconnect this connection"""
        async with self._lock:
            self._is_connected = False
            # Clear message queue
            while not self._message_queue.empty():
                try:
                    self._message_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
    
    async def get_pending_messages(self) -> List[Dict[str, Any]]:
        """Get all pending messages from queue"""
        messages = []
        while not self._message_queue.empty():
            try:
                message = self._message_queue.get_nowait()
                messages.append(message)
            except asyncio.QueueEmpty:
                break
        return messages
    
    def is_timed_out(self, timeout_seconds: float = 60.0) -> bool:
        """Check if connection has timed out"""
        if not self._is_connected:
            return True
        
        timeout_threshold = datetime.now() - timedelta(seconds=timeout_seconds)
        return self.last_activity < timeout_threshold


class SSEMessage:
    """Represents a Server-Sent Event message with proper formatting."""
    
    def __init__(self, event: str, data: Any, message_id: Optional[str] = None):
        self.event = event
        self.data = data
        self.message_id = message_id or str(uuid.uuid4())
        self.timestamp = datetime.now()
    
    def format(self) -> str:
        """Format message according to SSE protocol specification."""
        lines = []
        if self.message_id:
            lines.append(f"id: {self.message_id}")
        lines.append(f"event: {self.event}")
        
        # Handle data serialization
        if isinstance(self.data, (dict, list)):
            data_str = json.dumps(self.data)
        else:
            data_str = str(self.data)
        
        # Split multi-line data properly
        for line in data_str.split('\n'):
            lines.append(f"data: {line}")
        
        # Add final newline as per SSE spec
        lines.append("")
        return '\n'.join(lines)


class ClientConnection:
    """Represents a single SSE client connection."""
    
    def __init__(self, client_id: str, session_id: str):
        self.client_id = client_id
        self.session_id = session_id
        self.connected_at = datetime.now()
        self.last_heartbeat = datetime.now()
        self.message_queue = queue.Queue(maxsize=1000)  # Bounded queue for memory safety
        self.is_active = True
        self._lock = threading.Lock()
    
    def add_message(self, message: SSEMessage) -> bool:
        """Add message to client queue. Returns False if queue is full."""
        try:
            with self._lock:
                if not self.is_active:
                    return False
                self.message_queue.put_nowait(message)
                return True
        except queue.Full:
            logger.warning(f"Message queue full for client {self.client_id}")
            return False
    
    def get_messages(self) -> List[SSEMessage]:
        """Get all pending messages for this client."""
        messages = []
        with self._lock:
            while not self.message_queue.empty():
                try:
                    messages.append(self.message_queue.get_nowait())
                except queue.Empty:
                    break
        return messages
    
    def update_heartbeat(self):
        """Update last heartbeat timestamp."""
        with self._lock:
            self.last_heartbeat = datetime.now()
    
    def disconnect(self):
        """Mark connection as disconnected."""
        with self._lock:
            self.is_active = False


class SSEManagerSync:
    """
    Server-Sent Events Manager for real-time client communication.
    
    Provides thread-safe management of SSE connections with support for:
    - Multiple clients per session
    - High-throughput message delivery (1000+ msg/sec)
    - Connection lifecycle management
    - Automatic cleanup and heartbeat monitoring
    - SSE protocol compliance
    """
    
    def __init__(self):
        # Core data structures
        self._sessions: Dict[str, Set[str]] = defaultdict(set)  # session_id -> client_ids
        self._clients: Dict[str, ClientConnection] = {}  # client_id -> ClientConnection
        self._client_to_session: Dict[str, str] = {}  # client_id -> session_id
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics tracking
        self._stats = {
            'total_connections': 0,
            'active_connections': 0,
            'messages_sent': 0,
            'heartbeats_sent': 0,
            'disconnections': 0,
            'errors': 0
        }
        
        # Heartbeat management
        self._heartbeat_interval = 30  # seconds
        self._heartbeat_thread = None
        self._heartbeat_running = False
        self._connection_timeout = 60  # seconds
        
        # Performance optimization
        self._message_batch_size = 50
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = datetime.now()
        
        # Message history for debugging
        self._message_history = deque(maxlen=1000)
    
    def register_client(self, session_id: str, client_id: Optional[str] = None) -> str:
        """
        Register a new SSE client connection.
        
        Args:
            session_id: Session identifier for grouping clients
            client_id: Optional client identifier (generated if not provided)
            
        Returns:
            The client_id for the registered connection
            
        Raises:
            ValueError: If session_id is invalid
        """
        if not session_id or not isinstance(session_id, str):
            raise ValueError("Invalid session_id: must be non-empty string")
        
        if not client_id:
            client_id = str(uuid.uuid4())
        
        with self._lock:
            # Create client connection
            connection = ClientConnection(client_id, session_id)
            
            # Register in data structures
            self._clients[client_id] = connection
            self._sessions[session_id].add(client_id)
            self._client_to_session[client_id] = session_id
            
            # Update statistics
            self._stats['total_connections'] += 1
            self._stats['active_connections'] = len(self._clients)
            
            logger.info(f"Registered client {client_id} for session {session_id}")
            
        return client_id
    
    def unregister_client(self, client_id: str) -> bool:
        """
        Remove a client connection.
        
        Args:
            client_id: Client identifier to remove
            
        Returns:
            True if client was found and removed, False otherwise
        """
        with self._lock:
            if client_id not in self._clients:
                return False
            
            connection = self._clients[client_id]
            session_id = connection.session_id
            
            # Disconnect and cleanup
            connection.disconnect()
            
            # Remove from data structures
            del self._clients[client_id]
            self._sessions[session_id].discard(client_id)
            if not self._sessions[session_id]:
                del self._sessions[session_id]
            del self._client_to_session[client_id]
            
            # Update statistics
            self._stats['active_connections'] = len(self._clients)
            self._stats['disconnections'] += 1
            
            logger.info(f"Unregistered client {client_id}")
            
        return True
    
    def send_command(self, session_id: str, command: Dict[str, Any]) -> int:
        """
        Send a command message to all clients in a session.
        
        Args:
            session_id: Target session identifier
            command: Command data to send
            
        Returns:
            Number of clients that received the command
            
        Raises:
            ValueError: If session_id is invalid
        """
        if not session_id or not isinstance(session_id, str):
            raise ValueError("Invalid session_id")
        
        if not isinstance(command, dict):
            raise ValueError("Command must be a dictionary")
        
        message = SSEMessage("command", command)
        return self._send_to_session(session_id, message)
    
    def send_to_client(self, client_id: str, message_data: Any) -> bool:
        """
        Send a message to a specific client.
        
        Args:
            client_id: Target client identifier
            message_data: Message data to send
            
        Returns:
            True if message was queued successfully, False otherwise
            
        Raises:
            ValueError: If client_id is invalid
        """
        if not client_id or not isinstance(client_id, str):
            raise ValueError("Invalid client_id")
        
        with self._lock:
            if client_id not in self._clients:
                return False
            
            connection = self._clients[client_id]
            message = SSEMessage("message", message_data)
            
            success = connection.add_message(message)
            if success:
                self._stats['messages_sent'] += 1
                self._message_history.append({
                    'timestamp': datetime.now(),
                    'type': 'direct',
                    'client_id': client_id,
                    'message': message_data
                })
            
            return success
    
    def broadcast(self, command: Dict[str, Any]) -> int:
        """
        Broadcast a command to all connected clients.
        
        Args:
            command: Command data to broadcast
            
        Returns:
            Number of clients that received the command
            
        Raises:
            ValueError: If command is invalid
        """
        if not isinstance(command, dict):
            raise ValueError("Command must be a dictionary")
        
        message = SSEMessage("command", command)
        
        with self._lock:
            sent_count = 0
            for connection in self._clients.values():
                if connection.add_message(message):
                    sent_count += 1
            
            self._stats['messages_sent'] += sent_count
            self._message_history.append({
                'timestamp': datetime.now(),
                'type': 'broadcast',
                'recipients': sent_count,
                'command': command
            })
            
        return sent_count
    
    def start_heartbeat(self):
        """Start the heartbeat mechanism for connection monitoring."""
        if self._heartbeat_running:
            return
        
        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self._heartbeat_thread.start()
        
        logger.info("Heartbeat mechanism started")
    
    def stop_heartbeat(self):
        """Stop the heartbeat mechanism."""
        self._heartbeat_running = False
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5)
        
        logger.info("Heartbeat mechanism stopped")
    
    def cleanup_connections(self) -> int:
        """
        Clean up disconnected or timed-out connections.
        
        Returns:
            Number of connections cleaned up
        """
        current_time = datetime.now()
        timeout_threshold = current_time - timedelta(seconds=self._connection_timeout)
        
        cleanup_count = 0
        
        with self._lock:
            # Find clients to remove
            clients_to_remove = []
            
            for client_id, connection in self._clients.items():
                if (not connection.is_active or 
                    connection.last_heartbeat < timeout_threshold):
                    clients_to_remove.append(client_id)
            
            # Remove timed-out clients
            for client_id in clients_to_remove:
                if self.unregister_client(client_id):
                    cleanup_count += 1
            
            self._last_cleanup = current_time
        
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} connections")
        
        return cleanup_count
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get connection statistics and status information.
        
        Returns:
            Dictionary containing connection statistics
        """
        with self._lock:
            stats = self._stats.copy()
            stats.update({
                'active_sessions': len(self._sessions),
                'heartbeat_running': self._heartbeat_running,
                'last_cleanup': self._last_cleanup.isoformat(),
                'session_details': {
                    session_id: len(clients) 
                    for session_id, clients in self._sessions.items()
                }
            })
            
        return stats
    
    def validate_connection(self, session_id: str, client_id: str) -> bool:
        """
        Validate that a client connection is active and belongs to the session.
        
        Args:
            session_id: Session identifier to validate
            client_id: Client identifier to validate
            
        Returns:
            True if connection is valid and active, False otherwise
        """
        if not session_id or not client_id:
            return False
        
        with self._lock:
            # Check if client exists and is active
            if client_id not in self._clients:
                return False
            
            connection = self._clients[client_id]
            if not connection.is_active:
                return False
            
            # Verify session association
            if connection.session_id != session_id:
                return False
            
            # Verify bidirectional mapping consistency
            if (client_id not in self._sessions.get(session_id, set()) or
                self._client_to_session.get(client_id) != session_id):
                return False
            
            return True
    
    def get_session_clients(self, session_id: str) -> List[str]:
        """Get list of client IDs for a session."""
        with self._lock:
            return list(self._sessions.get(session_id, set()))
    
    def get_client_count(self, session_id: Optional[str] = None) -> int:
        """Get count of active clients, optionally filtered by session."""
        with self._lock:
            if session_id:
                return len(self._sessions.get(session_id, set()))
            return len(self._clients)
    
    def _send_to_session(self, session_id: str, message: SSEMessage) -> int:
        """Internal method to send message to all clients in a session."""
        with self._lock:
            if session_id not in self._sessions:
                return 0
            
            sent_count = 0
            for client_id in self._sessions[session_id]:
                if client_id in self._clients:
                    connection = self._clients[client_id]
                    if connection.add_message(message):
                        sent_count += 1
            
            if sent_count > 0:
                self._stats['messages_sent'] += sent_count
                self._message_history.append({
                    'timestamp': datetime.now(),
                    'type': 'session',
                    'session_id': session_id,
                    'recipients': sent_count,
                    'event': message.event
                })
            
            return sent_count
    
    def _heartbeat_worker(self):
        """Background thread worker for sending heartbeat messages."""
        while self._heartbeat_running:
            try:
                # Send heartbeat to all active connections
                heartbeat_data = {
                    'timestamp': datetime.now().isoformat(),
                    'server_time': int(time.time())
                }
                heartbeat_message = SSEMessage("heartbeat", heartbeat_data)
                
                with self._lock:
                    sent_count = 0
                    for connection in self._clients.values():
                        if connection.is_active:
                            if connection.add_message(heartbeat_message):
                                connection.update_heartbeat()
                                sent_count += 1
                    
                    self._stats['heartbeats_sent'] += sent_count
                
                # Periodic cleanup
                if (datetime.now() - self._last_cleanup).seconds >= self._cleanup_interval:
                    self.cleanup_connections()
                
                # Wait for next heartbeat interval
                time.sleep(self._heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in heartbeat worker: {e}")
                self._stats['errors'] += 1
                time.sleep(1)  # Brief pause on error
    
    def __enter__(self):
        """Context manager entry."""
        self.start_heartbeat()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.stop_heartbeat()
        
        # Disconnect all clients
        with self._lock:
            for connection in self._clients.values():
                connection.disconnect()
            
            # Clear all data structures
            self._clients.clear()
            self._sessions.clear()
            self._client_to_session.clear()
        
        logger.info("SSEManagerSync shutdown complete")


class SSEManager:
    """Async-compatible SSE Manager interface for tests"""
    
    def __init__(self, heartbeat_interval: float = 5.0, connection_timeout: float = 60.0, batch_interval: float = 0.1):
        self._sync_manager = SSEManagerSync()
        self._sync_manager._heartbeat_interval = heartbeat_interval
        self._sync_manager._connection_timeout = connection_timeout
        self._connections: Dict[str, SSEConnection] = {}
        self._async_heartbeat_task: Optional[asyncio.Task] = None
        
        # Override heartbeat worker to include async connections
        self._sync_manager._original_heartbeat_worker = self._sync_manager._heartbeat_worker
        self._sync_manager._heartbeat_worker = self._async_heartbeat_worker
    
    async def create_connection(self, session_id: str, client_id: Optional[str] = None) -> SSEConnection:
        """Create new SSE connection (async interface)"""
        if not client_id:
            client_id = str(uuid.uuid4())
        
        # Register with sync manager
        actual_client_id = self._sync_manager.register_client(session_id, client_id)
        
        # Create async connection wrapper
        connection = SSEConnection(session_id, actual_client_id)
        self._connections[actual_client_id] = connection
        
        # Start heartbeat if not already running
        if self._async_heartbeat_task is None or self._async_heartbeat_task.done():
            self._async_heartbeat_task = asyncio.create_task(self._async_heartbeat_loop())
        
        return connection
    
    async def send_command(self, session_id: str, command: Dict[str, Any]) -> int:
        """Send command to session (async interface)"""
        # Check if session exists
        if session_id not in self._sync_manager._sessions:
            raise InvalidSessionError(f"Session not found: {session_id}")
        
        # Send via sync manager
        sent_count = self._sync_manager.send_command(session_id, command)
        
        # Also send to async connections
        if session_id in self._sync_manager._sessions:
            for client_id in self._sync_manager._sessions[session_id]:
                if client_id in self._connections:
                    await self._connections[client_id].send_message(command)
        
        return sent_count
    
    async def send_to_client(self, client_id: str, message: Any) -> bool:
        """Send message to specific client (async interface)"""
        # Send via sync manager
        success = self._sync_manager.send_to_client(client_id, message)
        
        # Also send to async connection
        if client_id in self._connections:
            if isinstance(message, dict):
                await self._connections[client_id].send_message(message)
            else:
                await self._connections[client_id].send_message({'data': message})
        
        return success
    
    async def send_command_to_client(self, session_id: str, client_id: str, command: Dict[str, Any]) -> bool:
        """Send command to specific client in session"""
        # Validate that client belongs to session
        if not self._sync_manager.validate_connection(session_id, client_id):
            raise InvalidSessionError(f"Client {client_id} not found in session {session_id}")
        
        # Send to specific client
        return await self.send_to_client(client_id, command)
    
    def get_active_connections(self) -> Dict[str, List[str]]:
        """Get active connections grouped by session"""
        result = {}
        for session_id, client_ids in self._sync_manager._sessions.items():
            result[session_id] = list(client_ids)
        return result
    
    def register_client(self, session_id: str, client_id: Optional[str] = None) -> str:
        """Register client (sync interface)"""
        return self._sync_manager.register_client(session_id, client_id)
    
    def unregister_client(self, client_id: str) -> bool:
        """Unregister client (sync interface)"""
        # Remove from async connections
        if client_id in self._connections:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._connections[client_id].disconnect())
                else:
                    asyncio.run(self._connections[client_id].disconnect())
            except RuntimeError:
                # No event loop, just delete
                pass
            del self._connections[client_id]
        
        return self._sync_manager.unregister_client(client_id)
    
    def broadcast(self, command: Dict[str, Any]) -> int:
        """Broadcast to all clients (sync interface)"""
        return self._sync_manager.broadcast(command)
    
    def start_heartbeat(self):
        """Start heartbeat mechanism"""
        self._sync_manager.start_heartbeat()
    
    def stop_heartbeat(self):
        """Stop heartbeat mechanism"""
        self._sync_manager.stop_heartbeat()
        
        # Cancel async heartbeat task
        if self._async_heartbeat_task and not self._async_heartbeat_task.done():
            self._async_heartbeat_task.cancel()
    
    def cleanup_connections(self) -> int:
        """Clean up disconnected connections"""
        return self._sync_manager.cleanup_connections()
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return self._sync_manager.get_connection_stats()
    
    def validate_connection(self, session_id: str, client_id: str) -> bool:
        """Validate connection"""
        return self._sync_manager.validate_connection(session_id, client_id)
    
    def get_session_clients(self, session_id: str) -> List[str]:
        """Get session clients"""
        return self._sync_manager.get_session_clients(session_id)
    
    def get_client_count(self, session_id: Optional[str] = None) -> int:
        """Get client count"""
        return self._sync_manager.get_client_count(session_id)
    
    def _async_heartbeat_worker(self):
        """Heartbeat worker that also handles async connections"""
        while self._sync_manager._heartbeat_running:
            try:
                # Create heartbeat message
                heartbeat_data = {
                    'timestamp': datetime.now().isoformat(),
                    'server_time': int(time.time()),
                    'event': 'heartbeat'
                }
                
                # Send to sync connections (original logic)
                heartbeat_message = SSEMessage("heartbeat", heartbeat_data)
                
                with self._sync_manager._lock:
                    sent_count = 0
                    for connection in self._sync_manager._clients.values():
                        if connection.is_active:
                            if connection.add_message(heartbeat_message):
                                connection.update_heartbeat()
                                sent_count += 1
                    
                    self._sync_manager._stats['heartbeats_sent'] += sent_count
                
                # Send to async connections
                for connection in self._connections.values():
                    if connection.is_connected():
                        try:
                            # Use asyncio to schedule the coroutine
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.create_task(connection.send_message(heartbeat_data))
                        except RuntimeError:
                            # No event loop running, skip async connections
                            pass
                
                # Periodic cleanup (from original logic)
                if (datetime.now() - self._sync_manager._last_cleanup).seconds >= self._sync_manager._cleanup_interval:
                    self._sync_manager.cleanup_connections()
                
                # Wait for next heartbeat interval
                time.sleep(self._sync_manager._heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in async heartbeat worker: {e}")
                self._sync_manager._stats['errors'] += 1
                time.sleep(1)  # Brief pause on error
    
    async def _async_heartbeat_loop(self):
        """Async heartbeat loop for async connections"""
        # Initial delay before first heartbeat
        await asyncio.sleep(self._sync_manager._heartbeat_interval)
        
        while self._connections:  # Run while there are active connections
            try:
                # Create heartbeat message
                heartbeat_data = {
                    'timestamp': datetime.now().isoformat(),
                    'server_time': int(time.time()),
                    'event': 'heartbeat'
                }
                
                # Send to all async connections
                for connection in self._connections.values():
                    if connection.is_connected():
                        await connection.send_message(heartbeat_data)
                
                # Wait for next heartbeat interval
                await asyncio.sleep(self._sync_manager._heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in async heartbeat loop: {e}")
                await asyncio.sleep(1)  # Brief pause on error