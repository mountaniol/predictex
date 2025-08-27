#!/usr/bin/env python3
"""
Standalone test for EventProcessingPipeline - No relative imports

This is a simplified test to verify the pipeline orchestration logic
without dealing with component dependencies.
"""

import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Add backend path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'backend')
sys.path.insert(0, backend_path)

# Mock all component modules before importing pipeline
component_modules = [
    'command_generator', 'dependency_engine', 'event_handler',
    'session_manager', 'sse_manager', 'ui_schema_generator'
]

for module in component_modules:
    mock_module = MagicMock()
    # Create mock classes that return AsyncMock instances
    for class_name in ['CommandGenerator', 'DependencyEngine', 'EventHandler', 
                       'SessionManager', 'SSEManager', 'UISchemaGenerator']:
        mock_class = MagicMock()
        mock_class.return_value = MagicMock()
        setattr(mock_module, class_name, mock_class)
    sys.modules[module] = mock_module

# Now we can import the pipeline
from event_processing_pipeline import (
    EventProcessingPipeline,
    EventType,
    PipelineStatus,
    ComponentHealth
)


def test_component_health():
    """Test ComponentHealth functionality"""
    print("Testing ComponentHealth...")
    
    health = ComponentHealth()
    
    # Test initial state
    assert health.component_status == {}
    assert health.last_check == {}
    assert health.error_counts == {}
    
    # Test healthy status
    health.update_status("test_component", True)
    assert health.is_healthy("test_component")
    assert health.error_counts["test_component"] == 0
    
    # Test unhealthy status  
    health.update_status("test_component", False)
    assert not health.is_healthy("test_component")
    assert health.error_counts["test_component"] == 1
    
    # Test overall health
    health.update_status("comp1", True)
    health.update_status("comp2", True)
    overall, data = health.get_overall_health()
    assert not overall  # Still have unhealthy test_component
    assert data["healthy_components"] == 2
    assert data["total_components"] == 3
    
    print("✅ ComponentHealth tests passed")


def test_pipeline_basics():
    """Test basic pipeline functionality"""
    print("Testing EventProcessingPipeline basics...")
    
    config = {
        "max_workers": 2,
        "session": {"timeout": 3600},
        "dependencies": {"max_cascade_depth": 10}
    }
    
    pipeline = EventProcessingPipeline(config)
    
    # Test initialization
    assert pipeline.config == config
    assert pipeline.status == PipelineStatus.INITIALIZING
    assert isinstance(pipeline.health, ComponentHealth)
    assert pipeline.session_manager is None
    assert pipeline.metrics["total_events"] == 0
    
    print("✅ Pipeline basic tests passed")


def test_event_validation():
    """Test event data validation"""
    print("Testing event validation...")
    
    pipeline = EventProcessingPipeline({})
    
    # Valid events
    valid_events = [
        {"type": "session_create", "user_data": {}},
        {"type": "answer_change", "session_id": "test", "question_id": "Q1"},
        {"type": "schema_request", "session_id": "test", "question_id": "Q1"},
        {"type": "submit", "session_id": "test"},
        {"type": "health_check"}
    ]
    
    for event in valid_events:
        assert pipeline._validate_event_data(event), f"Should validate: {event}"
    
    # Invalid events
    invalid_events = [
        {},  # No type
        {"type": "invalid_type"},  # Unknown type
        {"session_id": "test"},  # Missing type
        "not_a_dict"  # Not a dictionary
    ]
    
    for event in invalid_events:
        assert not pipeline._validate_event_data(event), f"Should not validate: {event}"
    
    print("✅ Event validation tests passed")


def test_metrics():
    """Test metrics functionality"""
    print("Testing metrics...")
    
    pipeline = EventProcessingPipeline({})
    
    # Test initial metrics
    assert pipeline.metrics["total_events"] == 0
    assert pipeline.metrics["successful_events"] == 0
    assert pipeline.metrics["failed_events"] == 0
    assert pipeline.metrics["average_processing_time"] == 0.0
    
    # Test successful event
    pipeline._update_metrics(True, 0.05)  # 50ms
    assert pipeline.metrics["total_events"] == 1
    assert pipeline.metrics["successful_events"] == 1
    assert pipeline.metrics["failed_events"] == 0
    assert pipeline.metrics["average_processing_time"] == 0.05
    
    # Test failed event
    pipeline._update_metrics(False, 0.1)  # 100ms
    assert pipeline.metrics["total_events"] == 2
    assert pipeline.metrics["successful_events"] == 1
    assert pipeline.metrics["failed_events"] == 1
    # Average should be (0.05 + 0.1) / 2 = 0.075
    assert abs(pipeline.metrics["average_processing_time"] - 0.075) < 0.001
    
    print("✅ Metrics tests passed")


async def test_process_event_invalid():
    """Test processing invalid event data"""
    print("Testing invalid event processing...")
    
    pipeline = EventProcessingPipeline({})
    
    # Test invalid event
    response = await pipeline.process_event({"invalid": "data"})
    
    assert not response.success
    assert len(response.errors) > 0
    assert "Invalid event data format" in response.errors[0]
    assert response.processing_time_ms > 0
    
    print("✅ Invalid event processing tests passed")


async def test_health_status():
    """Test health status functionality"""
    print("Testing health status...")
    
    pipeline = EventProcessingPipeline({})
    
    # Set some component statuses
    pipeline.health.update_status("component1", True)
    pipeline.health.update_status("component2", False)
    
    # Add some metrics
    pipeline.metrics["total_events"] = 100
    pipeline.metrics["successful_events"] = 95
    
    healthy, status = await pipeline.get_health_status()
    
    assert not healthy  # One component is unhealthy
    assert status["pipeline_status"] == PipelineStatus.INITIALIZING.value
    assert status["metrics"]["total_events"] == 100
    assert status["healthy_components"] == 1
    assert status["total_components"] == 2
    
    print("✅ Health status tests passed")


async def main():
    """Run all tests"""
    print("🚀 Starting EventProcessingPipeline standalone tests...")
    print()
    
    try:
        # Run synchronous tests
        test_component_health()
        test_pipeline_basics()
        test_event_validation()
        test_metrics()
        
        # Run async tests
        await test_process_event_invalid()
        await test_health_status()
        
        print()
        print("🎯 All EventProcessingPipeline tests passed successfully!")
        print()
        
        # Test basic orchestration flow
        print("Testing basic orchestration flow...")
        config = {
            "max_workers": 1,
            "session": {},
            "dependencies": {},
            "ui_schema": {},
            "commands": {},
            "events": {},
            "sse": {}
        }
        
        pipeline = EventProcessingPipeline(config)
        print("✅ Pipeline created")
        
        # Test event type recognition
        for event_type in EventType:
            event = {"type": event_type.value}
            if event_type != EventType.SESSION_CREATE:
                event["session_id"] = "test_session"
            if event_type == EventType.SCHEMA_REQUEST:
                event["question_id"] = "Q1"
            
            assert pipeline._validate_event_data(event)
            print(f"✅ Event type {event_type.value} validated")
        
        print()
        print("🏆 EventProcessingPipeline orchestration ready for production!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())