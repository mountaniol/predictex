"""
Test suite for EventProcessingPipeline - Server-Driven UI orchestrator

Tests the main coordination logic and component integration for the
event processing pipeline.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from typing import Dict, Any, List

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'backend'))

# Mock the component imports since we're testing in isolation
sys.modules['command_generator'] = MagicMock()
sys.modules['dependency_engine'] = MagicMock()
sys.modules['event_handler'] = MagicMock()
sys.modules['session_manager'] = MagicMock()
sys.modules['sse_manager'] = MagicMock()
sys.modules['ui_schema_generator'] = MagicMock()

from event_processing_pipeline import (
    EventProcessingPipeline,
    EventType,
    PipelineStatus,
    PipelineResponse,
    ProcessingContext,
    ComponentHealth,
    create_pipeline,
    managed_pipeline
)


@dataclass
class MockEventResult:
    """Mock result for event processing"""
    success: bool
    answer_value: Any = None
    validation_result: Dict = None
    evaluation_result: Dict = None
    cascaded_questions: List[str] = None
    errors: List[str] = None
    submission_data: Dict = None


class TestComponentHealth:
    """Test ComponentHealth monitoring"""
    
    def test_health_initialization(self):
        """Test health monitor initialization"""
        health = ComponentHealth()
        
        assert health.component_status == {}
        assert health.last_check == {}
        assert health.error_counts == {}
    
    def test_update_status_healthy(self):
        """Test updating component status to healthy"""
        health = ComponentHealth()
        
        health.update_status("test_component", True)
        
        assert health.component_status["test_component"] is True
        assert health.error_counts["test_component"] == 0
        assert "test_component" in health.last_check
    
    def test_update_status_unhealthy(self):
        """Test updating component status to unhealthy"""
        health = ComponentHealth()
        
        health.update_status("test_component", False)
        
        assert health.component_status["test_component"] is False
        assert health.error_counts["test_component"] == 1
    
    def test_is_healthy(self):
        """Test health checking"""
        health = ComponentHealth()
        
        # Unknown component should be unhealthy
        assert not health.is_healthy("unknown")
        
        # Healthy component
        health.update_status("healthy_comp", True)
        assert health.is_healthy("healthy_comp")
        
        # Unhealthy component
        health.update_status("unhealthy_comp", False)
        assert not health.is_healthy("unhealthy_comp")
    
    def test_overall_health(self):
        """Test overall health calculation"""
        health = ComponentHealth()
        
        # No components - unhealthy
        overall, data = health.get_overall_health()
        assert not overall
        assert data["total_components"] == 0
        
        # All healthy
        health.update_status("comp1", True)
        health.update_status("comp2", True)
        
        overall, data = health.get_overall_health()
        assert overall
        assert data["healthy_components"] == 2
        assert data["total_components"] == 2
        
        # One unhealthy
        health.update_status("comp3", False)
        
        overall, data = health.get_overall_health()
        assert not overall
        assert data["healthy_components"] == 2
        assert data["total_components"] == 3


class TestEventProcessingPipeline:
    """Test EventProcessingPipeline orchestration"""
    
    @pytest.fixture
    def pipeline_config(self):
        """Pipeline configuration for tests"""
        return {
            "max_workers": 2,
            "session": {"timeout": 3600},
            "dependencies": {"max_cascade_depth": 10},
            "ui_schema": {"cache_ttl": 300},
            "commands": {"batch_size": 10},
            "events": {"validation_timeout": 30},
            "sse": {"heartbeat_interval": 30}
        }
    
    @pytest.fixture
    def mock_components(self):
        """Mock all pipeline components"""
        return {
            "session_manager": AsyncMock(),
            "dependency_engine": AsyncMock(),
            "ui_schema_generator": AsyncMock(),
            "command_generator": AsyncMock(),
            "event_handler": AsyncMock(),
            "sse_manager": AsyncMock()
        }
    
    def test_pipeline_initialization(self, pipeline_config):
        """Test pipeline initialization"""
        pipeline = EventProcessingPipeline(pipeline_config)
        
        assert pipeline.config == pipeline_config
        assert pipeline.status == PipelineStatus.INITIALIZING
        assert isinstance(pipeline.health, ComponentHealth)
        assert pipeline.session_manager is None
        assert pipeline.metrics["total_events"] == 0
    
    @patch('event_processing_pipeline.SessionManager')
    @patch('event_processing_pipeline.DependencyEngine')
    @patch('event_processing_pipeline.UISchemaGenerator')
    @patch('event_processing_pipeline.CommandGenerator')
    @patch('event_processing_pipeline.EventHandler')
    @patch('event_processing_pipeline.SSEManager')
    async def test_initialize_success(
        self, 
        mock_sse, mock_event, mock_cmd, mock_schema, mock_dep, mock_session,
        pipeline_config
    ):
        """Test successful pipeline initialization"""
        # Setup mocks
        for mock_class in [mock_session, mock_dep, mock_schema, mock_cmd, mock_event, mock_sse]:
            mock_instance = AsyncMock()
            mock_class.return_value = mock_instance
            mock_instance.initialize.return_value = None
        
        pipeline = EventProcessingPipeline(pipeline_config)
        result = await pipeline.initialize()
        
        assert result is True
        assert pipeline.status == PipelineStatus.READY
        assert pipeline.session_manager is not None
        assert pipeline.health.is_healthy("session_manager")
    
    async def test_initialize_failure(self, pipeline_config):
        """Test initialization failure"""
        with patch('event_processing_pipeline.SessionManager') as mock_session:
            mock_session.side_effect = Exception("Initialization failed")
            
            pipeline = EventProcessingPipeline(pipeline_config)
            result = await pipeline.initialize()
            
            assert result is False
            assert pipeline.status == PipelineStatus.ERROR
    
    def test_validate_event_data(self, pipeline_config):
        """Test event data validation"""
        pipeline = EventProcessingPipeline(pipeline_config)
        
        # Valid event data
        valid_event = {
            "type": "answer_change",
            "session_id": "test_session",
            "question_id": "Q1"
        }
        assert pipeline._validate_event_data(valid_event)
        
        # Invalid - missing type
        invalid_event = {"session_id": "test_session"}
        assert not pipeline._validate_event_data(invalid_event)
        
        # Invalid - bad type
        bad_type_event = {"type": "invalid_type"}
        assert not pipeline._validate_event_data(bad_type_event)
        
        # Invalid - not dict
        assert not pipeline._validate_event_data("not_dict")
    
    async def test_process_event_invalid_data(self, pipeline_config):
        """Test processing invalid event data"""
        pipeline = EventProcessingPipeline(pipeline_config)
        
        response = await pipeline.process_event({"invalid": "data"})
        
        assert not response.success
        assert "Invalid event data format" in response.errors
        assert response.processing_time_ms > 0
    
    async def test_create_session(self, pipeline_config, mock_components):
        """Test session creation"""
        pipeline = EventProcessingPipeline(pipeline_config)
        
        # Setup mocks
        pipeline.session_manager = mock_components["session_manager"]
        pipeline.ui_schema_generator = mock_components["ui_schema_generator"]
        pipeline.command_generator = mock_components["command_generator"]
        pipeline.sse_manager = mock_components["sse_manager"]
        pipeline.dependency_engine = mock_components["dependency_engine"]
        
        # Mock responses
        mock_components["session_manager"].create_session.return_value = "session_123"
        mock_components["session_manager"].get_session_state.return_value = {"answers": {}}
        mock_components["dependency_engine"].get_initial_questions.return_value = ["Q1", "Q2"]
        mock_components["ui_schema_generator"].generate_question_schema.return_value = {"type": "text"}
        mock_components["command_generator"].generate_session_created.return_value = [{"action": "welcome"}]
        mock_components["command_generator"].generate_schema_update.return_value = {"action": "schema"}
        
        user_data = {"user_id": "user_123", "name": "Test User"}
        response = await pipeline.create_session(user_data)
        
        assert response.success
        assert response.session_id == "session_123"
        assert len(response.commands) >= 1
        assert response.metadata["action"] == "session_created"
        
        # Verify component calls
        mock_components["session_manager"].create_session.assert_called_once_with(user_data)
        mock_components["sse_manager"].stream_commands.assert_called_once()
    
    async def test_handle_answer_event(self, pipeline_config, mock_components):
        """Test answer event handling"""
        pipeline = EventProcessingPipeline(pipeline_config)
        
        # Setup mocks
        pipeline.session_manager = mock_components["session_manager"]
        pipeline.event_handler = mock_components["event_handler"]
        pipeline.command_generator = mock_components["command_generator"]
        pipeline.sse_manager = mock_components["sse_manager"]
        
        # Mock responses
        mock_components["session_manager"].session_exists.return_value = True
        mock_result = MockEventResult(
            success=True,
            answer_value="test_answer",
            cascaded_questions=["Q2", "Q3"]
        )
        mock_components["event_handler"].handle_answer_change.return_value = mock_result
        mock_components["command_generator"].generate_answer_update.return_value = {"action": "update"}
        
        event_data = {
            "question_id": "Q1",
            "answer": "test_answer",
            "trigger_evaluation": True
        }
        
        response = await pipeline.handle_answer_event("session_123", event_data)
        
        assert response.success
        assert response.session_id == "session_123"
        assert response.metadata["question_id"] == "Q1"
        assert response.metadata["cascaded_count"] == 2
        
        # Verify event handler call
        mock_components["event_handler"].handle_answer_change.assert_called_once_with(
            session_id="session_123",
            question_id="Q1",
            answer="test_answer",
            trigger_evaluation=True
        )
    
    async def test_handle_answer_event_session_not_found(self, pipeline_config, mock_components):
        """Test answer event with invalid session"""
        pipeline = EventProcessingPipeline(pipeline_config)
        pipeline.session_manager = mock_components["session_manager"]
        
        # Session doesn't exist
        mock_components["session_manager"].session_exists.return_value = False
        
        event_data = {"question_id": "Q1", "answer": "test"}
        response = await pipeline.handle_answer_event("invalid_session", event_data)
        
        assert not response.success
        assert "Session not found" in response.errors
        assert response.session_id == "invalid_session"
    
    async def test_handle_schema_request(self, pipeline_config, mock_components):
        """Test schema request handling"""
        pipeline = EventProcessingPipeline(pipeline_config)
        
        # Setup mocks
        pipeline.session_manager = mock_components["session_manager"]
        pipeline.ui_schema_generator = mock_components["ui_schema_generator"]
        pipeline.command_generator = mock_components["command_generator"]
        pipeline.sse_manager = mock_components["sse_manager"]
        
        # Mock responses
        mock_components["session_manager"].get_session_state.return_value = {"answers": {"Q1": "value"}}
        mock_components["ui_schema_generator"].generate_question_schema.return_value = {
            "type": "text",
            "properties": {}
        }
        mock_components["command_generator"].generate_schema_update.return_value = {"action": "schema"}
        
        response = await pipeline.handle_schema_request("session_123", "Q1")
        
        assert response.success
        assert response.session_id == "session_123"
        assert response.metadata["question_id"] == "Q1"
        assert len(response.commands) == 1
        
        # Verify component calls
        mock_components["ui_schema_generator"].generate_question_schema.assert_called_once_with(
            "Q1", {"answers": {"Q1": "value"}}
        )
    
    async def test_handle_submit_event(self, pipeline_config, mock_components):
        """Test submission event handling"""
        pipeline = EventProcessingPipeline(pipeline_config)
        
        # Setup mocks
        pipeline.event_handler = mock_components["event_handler"]
        pipeline.command_generator = mock_components["command_generator"]
        pipeline.sse_manager = mock_components["sse_manager"]
        
        # Mock responses
        mock_result = MockEventResult(
            success=True,
            submission_data={"score": 85, "completed": True}
        )
        mock_components["event_handler"].handle_submit.return_value = mock_result
        mock_components["command_generator"].generate_submission_complete.return_value = [
            {"action": "complete"}
        ]
        
        response = await pipeline.handle_submit_event("session_123")
        
        assert response.success
        assert response.session_id == "session_123"
        assert response.metadata["action"] == "submission_complete"
        
        # Verify component calls
        mock_components["event_handler"].handle_submit.assert_called_once_with("session_123")
    
    async def test_get_health_status(self, pipeline_config):
        """Test health status reporting"""
        pipeline = EventProcessingPipeline(pipeline_config)
        
        # Set some health statuses
        pipeline.health.update_status("component1", True)
        pipeline.health.update_status("component2", False)
        
        # Update metrics
        pipeline.metrics["total_events"] = 100
        pipeline.metrics["successful_events"] = 95
        
        healthy, status = await pipeline.get_health_status()
        
        assert not healthy  # One component is unhealthy
        assert status["pipeline_status"] == PipelineStatus.INITIALIZING.value
        assert status["metrics"]["total_events"] == 100
        assert "component_status" in status
    
    def test_update_metrics(self, pipeline_config):
        """Test metrics updating"""
        pipeline = EventProcessingPipeline(pipeline_config)
        
        # Process successful event
        pipeline._update_metrics(True, 0.05)  # 50ms
        
        assert pipeline.metrics["total_events"] == 1
        assert pipeline.metrics["successful_events"] == 1
        assert pipeline.metrics["failed_events"] == 0
        assert pipeline.metrics["average_processing_time"] == 0.05
        
        # Process failed event
        pipeline._update_metrics(False, 0.1)  # 100ms
        
        assert pipeline.metrics["total_events"] == 2
        assert pipeline.metrics["successful_events"] == 1
        assert pipeline.metrics["failed_events"] == 1
        assert pipeline.metrics["average_processing_time"] == 0.075  # (0.05 + 0.1) / 2
    
    async def test_shutdown(self, pipeline_config, mock_components):
        """Test pipeline shutdown"""
        pipeline = EventProcessingPipeline(pipeline_config)
        
        # Setup mocks
        pipeline.sse_manager = mock_components["sse_manager"]
        pipeline.session_manager = mock_components["session_manager"]
        
        await pipeline.shutdown()
        
        assert pipeline.status == PipelineStatus.SHUTDOWN
        
        # Verify component shutdowns
        mock_components["sse_manager"].shutdown.assert_called_once()
        mock_components["session_manager"].shutdown.assert_called_once()


class TestPipelineIntegration:
    """Integration tests for pipeline components"""
    
    @pytest.fixture
    def integration_config(self):
        """Configuration for integration tests"""
        return {
            "max_workers": 1,
            "session": {"timeout": 300},
            "dependencies": {"max_cascade_depth": 5},
            "ui_schema": {"cache_ttl": 60},
            "commands": {"batch_size": 5},
            "events": {"validation_timeout": 10},
            "sse": {"heartbeat_interval": 15}
        }
    
    async def test_event_routing(self, integration_config):
        """Test event routing to correct handlers"""
        pipeline = EventProcessingPipeline(integration_config)
        
        # Mock all components
        with patch.multiple(
            'event_processing_pipeline',
            SessionManager=AsyncMock,
            DependencyEngine=AsyncMock,
            UISchemaGenerator=AsyncMock,
            CommandGenerator=AsyncMock,
            EventHandler=AsyncMock,
            SSEManager=AsyncMock
        ):
            await pipeline.initialize()
            
            # Test session create event
            session_event = {
                "type": "session_create",
                "user_data": {"user_id": "test"}
            }
            
            with patch.object(pipeline, 'create_session', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = PipelineResponse(success=True)
                
                response = await pipeline.process_event(session_event)
                mock_create.assert_called_once_with({"user_id": "test"})
            
            # Test answer change event
            answer_event = {
                "type": "answer_change",
                "session_id": "test_session",
                "question_id": "Q1",
                "answer": "test_value"
            }
            
            with patch.object(pipeline, 'handle_answer_event', new_callable=AsyncMock) as mock_answer:
                mock_answer.return_value = PipelineResponse(success=True)
                
                response = await pipeline.process_event(answer_event)
                mock_answer.assert_called_once_with("test_session", answer_event)
            
            # Test health check event
            health_event = {"type": "health_check"}
            
            with patch.object(pipeline, 'get_health_status', new_callable=AsyncMock) as mock_health:
                mock_health.return_value = (True, {"status": "healthy"})
                
                response = await pipeline.process_event(health_event)
                assert response.success
    
    async def test_concurrent_processing(self, integration_config):
        """Test concurrent event processing"""
        pipeline = EventProcessingPipeline(integration_config)
        
        # Mock all components for quick initialization
        with patch.multiple(
            'event_processing_pipeline',
            SessionManager=AsyncMock,
            DependencyEngine=AsyncMock,
            UISchemaGenerator=AsyncMock,
            CommandGenerator=AsyncMock,
            EventHandler=AsyncMock,
            SSEManager=AsyncMock
        ):
            await pipeline.initialize()
            
            # Create multiple concurrent events
            events = []
            for i in range(5):
                events.append({
                    "type": "answer_change",
                    "session_id": f"session_{i}",
                    "question_id": f"Q{i}",
                    "answer": f"value_{i}"
                })
            
            # Mock the handler to simulate processing
            with patch.object(pipeline, 'handle_answer_event', new_callable=AsyncMock) as mock_handler:
                mock_handler.return_value = PipelineResponse(success=True)
                
                # Process events concurrently
                tasks = [pipeline.process_event(event) for event in events]
                responses = await asyncio.gather(*tasks)
                
                # Verify all succeeded
                assert all(response.success for response in responses)
                assert len(responses) == 5
                
                # Verify all events were processed
                assert mock_handler.call_count == 5


class TestPipelineFactory:
    """Test pipeline factory functions"""
    
    @pytest.fixture
    def factory_config(self):
        """Configuration for factory tests"""
        return {
            "max_workers": 1,
            "session": {"timeout": 100},
            "dependencies": {},
            "ui_schema": {},
            "commands": {},
            "events": {},
            "sse": {}
        }
    
    async def test_create_pipeline_success(self, factory_config):
        """Test successful pipeline creation"""
        with patch.multiple(
            'event_processing_pipeline',
            SessionManager=AsyncMock,
            DependencyEngine=AsyncMock,
            UISchemaGenerator=AsyncMock,
            CommandGenerator=AsyncMock,
            EventHandler=AsyncMock,
            SSEManager=AsyncMock
        ):
            pipeline = await create_pipeline(factory_config)
            
            assert isinstance(pipeline, EventProcessingPipeline)
            assert pipeline.status == PipelineStatus.READY
    
    async def test_create_pipeline_failure(self, factory_config):
        """Test pipeline creation failure"""
        with patch('event_processing_pipeline.SessionManager') as mock_session:
            mock_session.side_effect = Exception("Init failed")
            
            with pytest.raises(RuntimeError, match="Failed to initialize"):
                await create_pipeline(factory_config)
    
    async def test_managed_pipeline_context(self, factory_config):
        """Test managed pipeline context manager"""
        with patch.multiple(
            'event_processing_pipeline',
            SessionManager=AsyncMock,
            DependencyEngine=AsyncMock,
            UISchemaGenerator=AsyncMock,
            CommandGenerator=AsyncMock,
            EventHandler=AsyncMock,
            SSEManager=AsyncMock
        ):
            async with managed_pipeline(factory_config) as pipeline:
                assert isinstance(pipeline, EventProcessingPipeline)
                assert pipeline.status == PipelineStatus.READY
                
                # Mock shutdown to verify it's called
                shutdown_mock = AsyncMock()
                pipeline.shutdown = shutdown_mock
            
            # Verify shutdown was called
            shutdown_mock.assert_called_once()


if __name__ == "__main__":
    # Run basic functionality test
    async def basic_test():
        config = {
            "max_workers": 2,
            "session": {},
            "dependencies": {},
            "ui_schema": {},
            "commands": {},
            "events": {},
            "sse": {}
        }
        
        pipeline = EventProcessingPipeline(config)
        
        # Test basic functionality
        print("✅ Pipeline created successfully")
        
        # Test health monitoring
        health = ComponentHealth()
        health.update_status("test", True)
        overall, data = health.get_overall_health()
        print(f"✅ Health monitoring works: {overall}")
        
        # Test event validation
        valid_event = {"type": "session_create", "user_data": {}}
        assert pipeline._validate_event_data(valid_event)
        print("✅ Event validation works")
        
        print("🎯 EventProcessingPipeline basic tests passed!")
    
    asyncio.run(basic_test())