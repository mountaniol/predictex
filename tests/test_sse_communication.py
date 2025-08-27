"""
Comprehensive Test Suite for SSE (Server-Sent Events) Communication Layer
Phase 2 - Protocol Implementation
Test-Driven Development (RED PHASE - Tests written before implementation)

This test suite covers:
1. Core SSE functionality from BK-FR-CHANGE.md plan
2. Comprehensive additional test cases for production-ready implementation
3. Thread safety and concurrent connection handling
4. Performance and scalability testing
5. Error handling and edge cases
6. Authentication and session management

SSE Protocol Structure:
    GET /api/sse/{session_id}
    Accept: text/event-stream
    
    Response events:
    - event: command, data: {"type": "RENDER|UPDATE|STATE_SYNC", ...}
    - event: heartbeat, data: {"timestamp": 1234567890}
    - event: error, data: {"message": "Error description"}
"""

import pytest
import asyncio
import time
import threading
import json
import uuid
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import weakref
import gc

# Import the SSE Manager (will fail initially - RED phase of TDD)
try:
    from src.backend.sse_manager import (
        SSEManager, 
        SSEConnection, 
        SSEMessage,
        ConnectionStats,
        AuthenticationError,
        InvalidSessionError,
        SSETimeoutError
    )
except ImportError:
    # Expected to fail initially - we're in RED phase of TDD
    SSEManager = None
    SSEConnection = None
    SSEMessage = None
    ConnectionStats = None
    AuthenticationError = None
    InvalidSessionError = None
    SSETimeoutError = None

# Test configuration constants
TEST_SESSION_ID = "test-session-12345"
TEST_CLIENT_ID = "client-abc123"
HEARTBEAT_INTERVAL = 1.0  # 1 second for fast testing
CONNECTION_TIMEOUT = 5.0  # 5 seconds for testing
MAX_MESSAGE_QUEUE_SIZE = 100


class TestSSEManager:
    """Test suite for SSEManager core functionality"""
    
    def setup_method(self):
        """Setup before each test method"""
        if SSEManager is None:
            pytest.skip("SSEManager not implemented yet - RED phase of TDD")
        
        self.sse_manager = SSEManager(
            heartbeat_interval=HEARTBEAT_INTERVAL,
            connection_timeout=CONNECTION_TIMEOUT,
            max_queue_size=MAX_MESSAGE_QUEUE_SIZE
        )
        
    def teardown_method(self):
        """Cleanup after each test method"""
        if hasattr(self, 'sse_manager') and self.sse_manager:
            # Clean up all connections
            self.sse_manager.shutdown()


class TestCoreSSEFunctionality:
    """Core test cases from BK-FR-CHANGE.md plan"""
    
    @pytest.mark.asyncio
    async def test_sse_connection(self):
        """Test that client can establish SSE connection"""
        sse_manager = SSEManager()
        
        # Establish connection
        connection = await sse_manager.create_connection(
            session_id=TEST_SESSION_ID,
            client_id=TEST_CLIENT_ID
        )
        
        assert connection is not None
        assert connection.session_id == TEST_SESSION_ID
        assert connection.client_id == TEST_CLIENT_ID
        assert connection.is_connected() is True
        
        # Verify connection is tracked
        active_connections = sse_manager.get_active_connections()
        assert TEST_SESSION_ID in active_connections
        assert TEST_CLIENT_ID in active_connections[TEST_SESSION_ID]
        
    @pytest.mark.asyncio
    async def test_command_streaming(self):
        """Test that commands stream to connected clients"""
        sse_manager = SSEManager()
        connection = await sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        
        # Prepare to capture streamed messages
        received_messages = []
        
        async def message_handler(message):
            received_messages.append(message)
        
        connection.on_message(message_handler)
        
        # Send various command types
        commands = [
            {"type": "RENDER", "component": "question", "data": {"id": "Q1", "text": "Test?"}},
            {"type": "UPDATE", "component": "score", "data": {"score": 85, "explanation": "Good"}},
            {"type": "STATE_SYNC", "data": {"answers": {"Q1": "answer"}, "scores": {"Q1": 85}}}
        ]
        
        for command in commands:
            await sse_manager.send_command(TEST_SESSION_ID, command)
        
        # Wait for messages to be processed
        await asyncio.sleep(0.1)
        
        assert len(received_messages) == 3
        for i, command in enumerate(commands):
            assert received_messages[i]["type"] == command["type"]
            
    @pytest.mark.asyncio 
    async def test_reconnection(self):
        """Test that client reconnects after disconnect"""
        sse_manager = SSEManager()
        
        # Initial connection
        connection1 = await sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        assert connection1.is_connected()
        
        # Simulate disconnect
        await connection1.disconnect()
        assert not connection1.is_connected()
        
        # Reconnect with same session/client
        connection2 = await sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        assert connection2.is_connected()
        
        # Should be able to send messages to reconnected client
        await sse_manager.send_command(TEST_SESSION_ID, {"type": "RENDER", "data": "test"})
        
        # Verify message was received by new connection
        messages = await connection2.get_pending_messages()
        assert len(messages) >= 1
        
    @pytest.mark.asyncio
    async def test_heartbeat(self):
        """Test that heartbeat prevents connection timeout"""
        sse_manager = SSEManager(heartbeat_interval=0.5, connection_timeout=2.0)
        connection = await sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        
        heartbeat_count = 0
        
        async def heartbeat_handler(message):
            nonlocal heartbeat_count
            if message.get("event") == "heartbeat":
                heartbeat_count += 1
        
        connection.on_message(heartbeat_handler)
        
        # Wait for multiple heartbeats
        await asyncio.sleep(1.5)
        
        # Should have received at least 2 heartbeats
        assert heartbeat_count >= 2
        assert connection.is_connected()
        
        # Connection should still be alive after heartbeat period
        assert not connection.is_timed_out()


class TestMultipleClientConnections:
    """Test handling of multiple concurrent client connections"""
    
    @pytest.mark.asyncio
    async def test_multiple_clients_same_session(self):
        """Test multiple clients connecting to same session"""
        sse_manager = SSEManager()
        
        client_ids = ["client-1", "client-2", "client-3"]
        connections = {}
        
        # Connect multiple clients to same session
        for client_id in client_ids:
            connections[client_id] = await sse_manager.create_connection(
                TEST_SESSION_ID, client_id
            )
        
        # Send broadcast message to session
        await sse_manager.send_command(TEST_SESSION_ID, {
            "type": "UPDATE", 
            "data": {"broadcast": True}
        })
        
        # All clients should receive the message
        await asyncio.sleep(0.1)
        for client_id, connection in connections.items():
            messages = await connection.get_pending_messages()
            assert any(msg.get("data", {}).get("broadcast") for msg in messages)
            
    @pytest.mark.asyncio
    async def test_multiple_sessions(self):
        """Test multiple sessions with different clients"""
        sse_manager = SSEManager()
        
        sessions = {
            "session-1": ["client-1a", "client-1b"],
            "session-2": ["client-2a"],
            "session-3": ["client-3a", "client-3b", "client-3c"]
        }
        
        connections = {}
        
        # Create connections for all session/client combinations
        for session_id, client_ids in sessions.items():
            connections[session_id] = {}
            for client_id in client_ids:
                connections[session_id][client_id] = await sse_manager.create_connection(
                    session_id, client_id
                )
        
        # Send session-specific messages
        for session_id in sessions:
            await sse_manager.send_command(session_id, {
                "type": "RENDER",
                "data": {"session": session_id}
            })
        
        await asyncio.sleep(0.1)
        
        # Verify session isolation - clients only receive their session's messages
        for session_id, session_connections in connections.items():
            for client_id, connection in session_connections.items():
                messages = await connection.get_pending_messages()
                session_messages = [m for m in messages if m.get("data", {}).get("session") == session_id]
                assert len(session_messages) >= 1
                
                # Should not receive messages from other sessions
                other_session_messages = [m for m in messages if m.get("data", {}).get("session") not in [session_id, None]]
                assert len(other_session_messages) == 0


class TestSessionSpecificRouting:
    """Test session-based message routing and isolation"""
    
    @pytest.mark.asyncio
    async def test_session_message_isolation(self):
        """Test that messages are properly isolated by session"""
        sse_manager = SSEManager()
        
        # Connect clients to different sessions
        conn_a = await sse_manager.create_connection("session-a", "client-a")
        conn_b = await sse_manager.create_connection("session-b", "client-b")
        
        received_a = []
        received_b = []
        
        async def handler_a(msg):
            received_a.append(msg)
            
        async def handler_b(msg):
            received_b.append(msg)
            
        conn_a.on_message(handler_a)
        conn_b.on_message(handler_b)
        
        # Send messages to specific sessions
        await sse_manager.send_command("session-a", {"type": "UPDATE", "data": "for-a"})
        await sse_manager.send_command("session-b", {"type": "UPDATE", "data": "for-b"})
        
        await asyncio.sleep(0.1)
        
        # Verify session isolation
        assert len(received_a) >= 1
        assert len(received_b) >= 1
        assert any("for-a" in str(msg) for msg in received_a)
        assert not any("for-b" in str(msg) for msg in received_a)
        assert any("for-b" in str(msg) for msg in received_b)
        assert not any("for-a" in str(msg) for msg in received_b)
        
    @pytest.mark.asyncio
    async def test_targeted_client_messaging(self):
        """Test sending messages to specific clients within a session"""
        sse_manager = SSEManager()
        
        # Multiple clients in same session
        conn1 = await sse_manager.create_connection(TEST_SESSION_ID, "client-1")
        conn2 = await sse_manager.create_connection(TEST_SESSION_ID, "client-2")
        
        received_1 = []
        received_2 = []
        
        conn1.on_message(lambda msg: received_1.append(msg))
        conn2.on_message(lambda msg: received_2.append(msg))
        
        # Send to specific client
        await sse_manager.send_command_to_client(
            TEST_SESSION_ID, "client-1", 
            {"type": "UPDATE", "data": "only-for-client-1"}
        )
        
        await asyncio.sleep(0.1)
        
        assert len(received_1) >= 1
        assert len(received_2) == 0  # Should not receive targeted message


class TestCommandBatchingOptimization:
    """Test command batching and performance optimization"""
    
    @pytest.mark.asyncio
    async def test_message_batching(self):
        """Test that rapid messages are batched for efficiency"""
        sse_manager = SSEManager(batch_interval=0.1)  # 100ms batching
        connection = await sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        
        received_batches = []
        
        async def batch_handler(batch):
            received_batches.append(batch)
            
        connection.on_batch(batch_handler)
        
        # Send rapid sequence of messages
        messages = [
            {"type": "UPDATE", "data": f"msg-{i}"}
            for i in range(10)
        ]
        
        for msg in messages:
            await sse_manager.send_command(TEST_SESSION_ID, msg)
            
        # Wait for batching interval
        await asyncio.sleep(0.2)
        
        # Should have received fewer batches than individual messages
        assert len(received_batches) < len(messages)
        
        # Total messages in batches should equal original count
        total_messages = sum(len(batch) for batch in received_batches)
        assert total_messages == len(messages)
        
    @pytest.mark.asyncio
    async def test_priority_message_handling(self):
        """Test that high-priority messages bypass batching"""
        sse_manager = SSEManager(batch_interval=1.0)  # Long batching interval
        connection = await sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        
        received_messages = []
        connection.on_message(lambda msg: received_messages.append(msg))
        
        # Send high-priority message (should bypass batching)
        await sse_manager.send_command(TEST_SESSION_ID, {
            "type": "ERROR",
            "priority": "HIGH", 
            "data": "critical-error"
        })
        
        # Should receive immediately, not batched
        await asyncio.sleep(0.1)
        assert len(received_messages) >= 1
        assert "critical-error" in str(received_messages[0])


class TestConnectionCleanup:
    """Test connection lifecycle management and cleanup"""
    
    @pytest.mark.asyncio
    async def test_client_disconnect_cleanup(self):
        """Test cleanup when client disconnects"""
        sse_manager = SSEManager()
        connection = await sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        
        # Verify connection exists
        assert TEST_SESSION_ID in sse_manager.get_active_connections()
        
        # Client disconnects
        await connection.disconnect()
        
        # Should be cleaned up
        await asyncio.sleep(0.1)
        active_connections = sse_manager.get_active_connections()
        assert TEST_SESSION_ID not in active_connections or \
               TEST_CLIENT_ID not in active_connections.get(TEST_SESSION_ID, {})
               
    @pytest.mark.asyncio
    async def test_connection_timeout_cleanup(self):
        """Test cleanup of timed-out connections"""
        sse_manager = SSEManager(connection_timeout=0.5)  # Short timeout
        connection = await sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        
        # Stop heartbeats to simulate unresponsive client
        connection._stop_heartbeat()
        
        # Wait for timeout
        await asyncio.sleep(1.0)
        
        # Connection should be timed out and cleaned up
        assert connection.is_timed_out()
        active_connections = sse_manager.get_active_connections()
        assert TEST_SESSION_ID not in active_connections or \
               TEST_CLIENT_ID not in active_connections.get(TEST_SESSION_ID, {})
               
    def test_memory_cleanup_on_shutdown(self):
        """Test that all resources are cleaned up on shutdown"""
        sse_manager = SSEManager()
        
        # Create multiple connections
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        connections = []
        for i in range(5):
            conn = loop.run_until_complete(
                sse_manager.create_connection(f"session-{i}", f"client-{i}")
            )
            connections.append(conn)
        
        # Capture weak references for memory leak detection
        weak_refs = [weakref.ref(conn) for conn in connections]
        
        # Shutdown manager
        sse_manager.shutdown()
        
        # Clear strong references
        del connections
        del sse_manager
        gc.collect()
        
        # Weak references should be None (objects garbage collected)
        for ref in weak_refs:
            assert ref() is None, "Memory leak detected - connection not garbage collected"


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_invalid_session_error(self):
        """Test handling of invalid session IDs"""
        sse_manager = SSEManager()
        
        with pytest.raises(InvalidSessionError):
            await sse_manager.send_command("non-existent-session", {"type": "UPDATE"})
            
    @pytest.mark.asyncio
    async def test_invalid_client_error(self):
        """Test handling of invalid client IDs"""
        sse_manager = SSEManager()
        await sse_manager.create_connection(TEST_SESSION_ID, "valid-client")
        
        with pytest.raises(InvalidSessionError):
            await sse_manager.send_command_to_client(
                TEST_SESSION_ID, "non-existent-client", {"type": "UPDATE"}
            )
            
    @pytest.mark.asyncio
    async def test_message_queue_overflow(self):
        """Test handling of message queue overflow"""
        sse_manager = SSEManager(max_queue_size=3)  # Small queue for testing
        connection = await sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        
        # Stop processing to cause queue buildup
        connection._pause_processing()
        
        # Send more messages than queue can handle
        for i in range(10):
            await sse_manager.send_command(TEST_SESSION_ID, {"type": "UPDATE", "data": i})
            
        # Should handle overflow gracefully (drop oldest or reject new)
        queue_size = connection.get_queue_size()
        assert queue_size <= 3
        
    @pytest.mark.asyncio
    async def test_malformed_message_handling(self):
        """Test handling of malformed messages"""
        sse_manager = SSEManager()
        connection = await sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        
        error_messages = []
        connection.on_error(lambda err: error_messages.append(err))
        
        # Send malformed messages
        malformed_messages = [
            None,
            "",
            {"type": None},  # Invalid type
            {"data": "missing type"},
            {"type": "INVALID_TYPE", "data": "test"}
        ]
        
        for msg in malformed_messages:
            try:
                await sse_manager.send_command(TEST_SESSION_ID, msg)
            except Exception:
                pass  # Expected to handle gracefully
        
        # Should have generated error messages
        await asyncio.sleep(0.1)
        assert len(error_messages) > 0


class TestPerformanceAndScalability:
    """Test performance under load and scalability"""
    
    @pytest.mark.asyncio
    async def test_high_throughput_messaging(self):
        """Test system under high message throughput"""
        sse_manager = SSEManager()
        connection = await sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        
        received_count = 0
        
        async def counter(msg):
            nonlocal received_count
            received_count += 1
        
        connection.on_message(counter)
        
        # Send high volume of messages rapidly
        message_count = 1000
        start_time = time.time()
        
        tasks = []
        for i in range(message_count):
            task = asyncio.create_task(
                sse_manager.send_command(TEST_SESSION_ID, {"type": "UPDATE", "data": i})
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        await asyncio.sleep(1.0)  # Allow processing time
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = message_count / duration
        
        # Should handle at least 100 messages per second
        assert throughput > 100, f"Throughput too low: {throughput:.2f} msg/sec"
        assert received_count >= message_count * 0.95  # Allow 5% loss
        
    def test_concurrent_connections_scalability(self):
        """Test handling of many concurrent connections"""
        sse_manager = SSEManager()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        connection_count = 100
        connections = []
        
        # Create many concurrent connections
        start_time = time.time()
        
        async def create_connections():
            tasks = []
            for i in range(connection_count):
                task = asyncio.create_task(
                    sse_manager.create_connection(f"session-{i}", f"client-{i}")
                )
                tasks.append(task)
            return await asyncio.gather(*tasks)
        
        connections = loop.run_until_complete(create_connections())
        creation_time = time.time() - start_time
        
        # Should create connections efficiently
        assert len(connections) == connection_count
        assert creation_time < 5.0, f"Connection creation too slow: {creation_time:.2f}s"
        
        # All connections should be active
        active_connections = sse_manager.get_active_connections()
        assert len(active_connections) == connection_count
        
        # Cleanup
        sse_manager.shutdown()


class TestThreadSafety:
    """Test thread safety for concurrent operations"""
    
    def test_concurrent_connection_creation(self):
        """Test thread-safe connection creation"""
        sse_manager = SSEManager()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        connection_results = []
        
        def create_connection_thread(session_id, client_id):
            try:
                connection = loop.run_until_complete(
                    sse_manager.create_connection(session_id, client_id)
                )
                connection_results.append((session_id, client_id, connection))
                return True
            except Exception as e:
                connection_results.append((session_id, client_id, e))
                return False
        
        # Create connections from multiple threads simultaneously
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(20):
                future = executor.submit(
                    create_connection_thread, f"session-{i}", f"client-{i}"
                )
                futures.append(future)
            
            # Wait for all threads to complete
            results = [future.result() for future in as_completed(futures)]
        
        # All connections should succeed
        assert all(results), "Some connections failed in concurrent creation"
        assert len(connection_results) == 20
        
        # Verify all connections are properly tracked
        active_connections = sse_manager.get_active_connections()
        assert len(active_connections) == 20
        
    def test_concurrent_message_sending(self):
        """Test thread-safe message sending"""
        sse_manager = SSEManager()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Create connection
        connection = loop.run_until_complete(
            sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        )
        
        received_messages = []
        connection.on_message(lambda msg: received_messages.append(msg))
        
        def send_messages_thread(thread_id, message_count):
            try:
                for i in range(message_count):
                    loop.run_until_complete(
                        sse_manager.send_command(TEST_SESSION_ID, {
                            "type": "UPDATE",
                            "data": f"thread-{thread_id}-msg-{i}"
                        })
                    )
                return True
            except Exception:
                return False
        
        # Send messages from multiple threads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for thread_id in range(5):
                future = executor.submit(send_messages_thread, thread_id, 10)
                futures.append(future)
            
            results = [future.result() for future in as_completed(futures)]
        
        # All sends should succeed
        assert all(results), "Some message sends failed in concurrent test"
        
        # Wait for message processing
        time.sleep(1.0)
        
        # Should have received all 50 messages (5 threads * 10 messages)
        assert len(received_messages) >= 45  # Allow some loss in high-concurrency


class TestMessageOrdering:
    """Test message ordering guarantees"""
    
    @pytest.mark.asyncio
    async def test_fifo_message_ordering(self):
        """Test that messages maintain FIFO order within a session"""
        sse_manager = SSEManager(batch_interval=0)  # Disable batching for ordering test
        connection = await sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        
        received_messages = []
        connection.on_message(lambda msg: received_messages.append(msg))
        
        # Send ordered sequence of messages
        message_count = 20
        for i in range(message_count):
            await sse_manager.send_command(TEST_SESSION_ID, {
                "type": "UPDATE",
                "sequence": i,
                "data": f"message-{i}"
            })
        
        # Wait for processing
        await asyncio.sleep(0.5)
        
        # Verify order is maintained
        sequences = [msg.get("sequence") for msg in received_messages if "sequence" in msg]
        assert sequences == list(range(len(sequences))), "Message ordering not maintained"
        
    @pytest.mark.asyncio
    async def test_cross_session_ordering_independence(self):
        """Test that message ordering is independent across sessions"""
        sse_manager = SSEManager(batch_interval=0)
        
        conn_a = await sse_manager.create_connection("session-a", "client-a")
        conn_b = await sse_manager.create_connection("session-b", "client-b")
        
        received_a = []
        received_b = []
        
        conn_a.on_message(lambda msg: received_a.append(msg))
        conn_b.on_message(lambda msg: received_b.append(msg))
        
        # Interleave messages between sessions
        for i in range(10):
            await sse_manager.send_command("session-a", {"sequence": i, "session": "a"})
            await sse_manager.send_command("session-b", {"sequence": i, "session": "b"})
        
        await asyncio.sleep(0.5)
        
        # Each session should have received its messages in order
        sequences_a = [msg["sequence"] for msg in received_a if msg.get("session") == "a"]
        sequences_b = [msg["sequence"] for msg in received_b if msg.get("session") == "b"]
        
        assert sequences_a == list(range(len(sequences_a)))
        assert sequences_b == list(range(len(sequences_b)))


class TestAuthenticationAuthorization:
    """Test authentication and authorization features"""
    
    @pytest.mark.asyncio
    async def test_connection_authentication(self):
        """Test that connections require proper authentication"""
        sse_manager = SSEManager(require_auth=True)
        
        # Connection without auth should fail
        with pytest.raises(AuthenticationError):
            await sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        
        # Connection with valid auth should succeed
        auth_token = "valid-token-123"
        connection = await sse_manager.create_connection(
            TEST_SESSION_ID, TEST_CLIENT_ID, auth_token=auth_token
        )
        
        assert connection.is_authenticated()
        assert connection.auth_token == auth_token
        
    @pytest.mark.asyncio
    async def test_session_authorization(self):
        """Test session-based authorization"""
        sse_manager = SSEManager(require_auth=True)
        
        # User should only access their own sessions
        user_sessions = {
            "user-1": ["session-a", "session-b"],
            "user-2": ["session-c"]
        }
        
        sse_manager.set_user_sessions(user_sessions)
        
        # User 1 should be able to connect to their sessions
        conn_a = await sse_manager.create_connection(
            "session-a", "client-1", auth_token="user-1-token"
        )
        assert conn_a.is_connected()
        
        # User 1 should NOT be able to connect to user 2's session
        with pytest.raises(AuthenticationError):
            await sse_manager.create_connection(
                "session-c", "client-1", auth_token="user-1-token"
            )


class TestConnectionStatistics:
    """Test connection statistics and monitoring"""
    
    @pytest.mark.asyncio
    async def test_connection_statistics(self):
        """Test collection of connection statistics"""
        sse_manager = SSEManager()
        
        # Create multiple connections
        connections = []
        for i in range(5):
            conn = await sse_manager.create_connection(f"session-{i}", f"client-{i}")
            connections.append(conn)
        
        # Send various messages
        for i in range(10):
            await sse_manager.send_command("session-0", {"type": "UPDATE", "data": i})
        
        await asyncio.sleep(0.2)
        
        # Get statistics
        stats = sse_manager.get_connection_stats()
        
        assert stats.total_connections == 5
        assert stats.active_connections == 5
        assert stats.total_sessions == 5
        assert stats.total_messages_sent >= 10
        assert stats.average_queue_size >= 0
        
    @pytest.mark.asyncio
    async def test_per_connection_metrics(self):
        """Test per-connection performance metrics"""
        sse_manager = SSEManager()
        connection = await sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        
        # Send messages and track metrics
        message_count = 50
        for i in range(message_count):
            await sse_manager.send_command(TEST_SESSION_ID, {"type": "UPDATE", "data": i})
        
        await asyncio.sleep(0.5)
        
        metrics = connection.get_metrics()
        
        assert metrics.messages_received >= message_count * 0.95  # Allow 5% loss
        assert metrics.connection_duration > 0
        assert metrics.average_latency >= 0
        assert metrics.last_activity_time is not None
        
    def test_monitoring_integration(self):
        """Test integration with monitoring systems"""
        sse_manager = SSEManager()
        
        # Mock monitoring system
        monitoring_events = []
        
        def mock_monitor(event_type, data):
            monitoring_events.append({"type": event_type, "data": data})
        
        sse_manager.set_monitoring_callback(mock_monitor)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Perform operations that should generate monitoring events
        connection = loop.run_until_complete(
            sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        )
        
        loop.run_until_complete(
            sse_manager.send_command(TEST_SESSION_ID, {"type": "UPDATE"})
        )
        
        loop.run_until_complete(connection.disconnect())
        
        # Should have generated monitoring events
        event_types = [event["type"] for event in monitoring_events]
        expected_events = ["connection_created", "message_sent", "connection_closed"]
        
        for expected in expected_events:
            assert expected in event_types, f"Missing monitoring event: {expected}"


class TestSSEProtocolCompliance:
    """Test compliance with SSE protocol standards"""
    
    @pytest.mark.asyncio
    async def test_sse_event_format(self):
        """Test that messages follow proper SSE event format"""
        sse_manager = SSEManager()
        connection = await sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        
        raw_events = []
        
        # Capture raw SSE formatted events
        async def raw_event_handler(raw_event):
            raw_events.append(raw_event)
        
        connection.on_raw_event(raw_event_handler)
        
        # Send command
        await sse_manager.send_command(TEST_SESSION_ID, {
            "type": "RENDER",
            "component": "question",
            "data": {"id": "Q1", "text": "Test question?"}
        })
        
        await asyncio.sleep(0.1)
        
        # Should have proper SSE format
        assert len(raw_events) >= 1
        
        event = raw_events[0]
        assert event.startswith("event: command\n")
        assert "data: " in event
        assert event.endswith("\n\n")
        
        # Extract and validate JSON data
        data_line = [line for line in event.split("\n") if line.startswith("data: ")][0]
        json_data = data_line[6:]  # Remove "data: " prefix
        parsed_data = json.loads(json_data)
        
        assert parsed_data["type"] == "RENDER"
        assert parsed_data["component"] == "question"
        
    @pytest.mark.asyncio  
    async def test_heartbeat_format(self):
        """Test that heartbeat events follow SSE format"""
        sse_manager = SSEManager(heartbeat_interval=0.2)
        connection = await sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        
        raw_events = []
        connection.on_raw_event(lambda event: raw_events.append(event))
        
        # Wait for heartbeat
        await asyncio.sleep(0.5)
        
        # Find heartbeat events
        heartbeat_events = [e for e in raw_events if "event: heartbeat" in e]
        assert len(heartbeat_events) >= 1
        
        heartbeat = heartbeat_events[0]
        assert heartbeat.startswith("event: heartbeat\n")
        assert "data: " in heartbeat
        
        # Validate heartbeat data
        data_line = [line for line in heartbeat.split("\n") if line.startswith("data: ")][0]
        json_data = data_line[6:]
        parsed_data = json.loads(json_data)
        
        assert "timestamp" in parsed_data
        assert isinstance(parsed_data["timestamp"], (int, float))
        
    @pytest.mark.asyncio
    async def test_error_event_format(self):
        """Test that error events follow SSE format"""
        sse_manager = SSEManager()
        connection = await sse_manager.create_connection(TEST_SESSION_ID, TEST_CLIENT_ID)
        
        raw_events = []
        connection.on_raw_event(lambda event: raw_events.append(event))
        
        # Trigger an error event
        await connection.send_error("Test error message")
        
        await asyncio.sleep(0.1)
        
        # Find error event
        error_events = [e for e in raw_events if "event: error" in e]
        assert len(error_events) >= 1
        
        error_event = error_events[0]
        assert error_event.startswith("event: error\n")
        assert "data: " in error_event
        
        # Validate error data
        data_line = [line for line in error_event.split("\n") if line.startswith("data: ")][0]
        json_data = data_line[6:]
        parsed_data = json.loads(json_data)
        
        assert "message" in parsed_data
        assert parsed_data["message"] == "Test error message"


# Performance benchmarking utilities
class PerformanceBenchmark:
    """Utilities for performance testing"""
    
    @staticmethod
    def measure_latency(func, *args, **kwargs):
        """Measure function execution latency"""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        return result, (end_time - start_time) * 1000  # Return result and latency in ms
    
    @staticmethod
    async def measure_async_latency(async_func, *args, **kwargs):
        """Measure async function execution latency"""
        start_time = time.perf_counter()
        result = await async_func(*args, **kwargs)
        end_time = time.perf_counter()
        return result, (end_time - start_time) * 1000


# Test fixtures and utilities
@pytest.fixture
def mock_sse_manager():
    """Create a mock SSE manager for testing"""
    if SSEManager is None:
        pytest.skip("SSEManager not implemented yet - RED phase of TDD")
    
    manager = SSEManager()
    yield manager
    manager.shutdown()


@pytest.fixture
def test_session_data():
    """Provide test session data"""
    return {
        "session_id": TEST_SESSION_ID,
        "client_id": TEST_CLIENT_ID,
        "auth_token": "test-token-123",
        "user_id": "test-user-456"
    }


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])