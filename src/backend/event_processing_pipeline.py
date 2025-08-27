"""
EventProcessingPipeline - Main orchestrator for Server-Driven UI architecture

This module provides the central coordination point for all backend components,
managing the complete event processing workflow from HTTP requests to SSE responses.
"""

import asyncio
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    # Try relative imports first (when used as package)
    from .command_generator import CommandGenerator
    from .dependency_engine import DependencyEngine
    from .event_handler import EventHandler
    from .session_manager import SessionManager
    from .sse_manager import SSEManager
    from .ui_schema_generator import UISchemaGenerator
except ImportError:
    # Fall back to absolute imports (when testing standalone)
    from command_generator import CommandGenerator
    from dependency_engine import DependencyEngine
    from event_handler import EventHandler
    from session_manager import SessionManager
    from sse_manager import SSEManager
    from ui_schema_generator import UISchemaGenerator


class EventType(Enum):
    """Supported event types in the pipeline"""
    SESSION_CREATE = "session_create"
    ANSWER_CHANGE = "answer_change"
    ANSWER_BLUR = "answer_blur"
    SCHEMA_REQUEST = "schema_request"
    SUBMIT = "submit"
    NAVIGATION = "navigation"
    HEALTH_CHECK = "health_check"


class PipelineStatus(Enum):
    """Pipeline processing status"""
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class PipelineResponse:
    """Response from pipeline processing"""
    success: bool
    commands: List[Dict[str, Any]] = field(default_factory=list)
    session_id: str = ""
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0


@dataclass
class ProcessingContext:
    """Context for event processing operations"""
    event_type: EventType
    session_id: str
    user_id: Optional[str] = None
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ComponentHealth:
    """Health monitoring for pipeline components"""
    
    def __init__(self):
        self.component_status: Dict[str, bool] = {}
        self.last_check: Dict[str, float] = {}
        self.error_counts: Dict[str, int] = {}
    
    def update_status(self, component: str, healthy: bool) -> None:
        """Update component health status"""
        self.component_status[component] = healthy
        self.last_check[component] = time.time()
        if not healthy:
            self.error_counts[component] = self.error_counts.get(component, 0) + 1
        else:
            self.error_counts[component] = 0
    
    def is_healthy(self, component: str) -> bool:
        """Check if component is healthy"""
        return self.component_status.get(component, False)
    
    def get_overall_health(self) -> Tuple[bool, Dict[str, Any]]:
        """Get overall pipeline health"""
        healthy_components = sum(1 for status in self.component_status.values() if status)
        total_components = len(self.component_status)
        
        overall_healthy = (
            total_components > 0 and 
            healthy_components == total_components
        )
        
        health_data = {
            "overall_healthy": overall_healthy,
            "healthy_components": healthy_components,
            "total_components": total_components,
            "component_status": self.component_status.copy(),
            "error_counts": self.error_counts.copy()
        }
        
        return overall_healthy, health_data


class EventProcessingPipeline:
    """
    Main orchestrator for Server-Driven UI architecture
    
    Coordinates all backend components to process events and generate
    UI updates through a complete request-response cycle.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Pipeline state
        self.status = PipelineStatus.INITIALIZING
        self.health = ComponentHealth()
        
        # Component instances
        self.session_manager: Optional[SessionManager] = None
        self.dependency_engine: Optional[DependencyEngine] = None
        self.command_generator: Optional[CommandGenerator] = None
        self.ui_schema_generator: Optional[UISchemaGenerator] = None
        self.event_handler: Optional[EventHandler] = None
        self.sse_manager: Optional[SSEManager] = None
        
        # Processing resources
        self.executor = ThreadPoolExecutor(
            max_workers=config.get("max_workers", 4),
            thread_name_prefix="pipeline"
        )
        
        # Active processing contexts
        self.active_contexts: Dict[str, ProcessingContext] = {}
        self.processing_lock = asyncio.Lock()
        
        # Performance metrics
        self.metrics = {
            "total_events": 0,
            "successful_events": 0,
            "failed_events": 0,
            "average_processing_time": 0.0,
            "last_reset": time.time()
        }
    
    async def initialize(self) -> bool:
        """
        Initialize all pipeline components
        
        Returns:
            bool: True if initialization successful
        """
        self.logger.info("Initializing EventProcessingPipeline...")
        
        try:
            # Initialize components in dependency order
            await self._initialize_session_manager()
            await self._initialize_dependency_engine()
            await self._initialize_ui_schema_generator()
            await self._initialize_command_generator()
            await self._initialize_event_handler()
            await self._initialize_sse_manager()
            
            # Verify component health
            if not await self._verify_component_health():
                self.status = PipelineStatus.ERROR
                return False
            
            self.status = PipelineStatus.READY
            self.logger.info("EventProcessingPipeline initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize pipeline: {e}")
            self.status = PipelineStatus.ERROR
            return False
    
    async def process_event(self, event_data: Dict[str, Any]) -> PipelineResponse:
        """
        Main event processing entry point
        
        Args:
            event_data: Event data containing type, session_id, and payload
            
        Returns:
            PipelineResponse: Processing result with commands and metadata
        """
        start_time = time.time()
        
        # Validate event format
        if not self._validate_event_data(event_data):
            return PipelineResponse(
                success=False,
                errors=["Invalid event data format"],
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        # Extract event information
        try:
            event_type = EventType(event_data["type"])
            session_id = event_data.get("session_id", "")
            
            # Create processing context
            context = ProcessingContext(
                event_type=event_type,
                session_id=session_id,
                user_id=event_data.get("user_id"),
                metadata=event_data.get("metadata", {})
            )
            
            self.logger.debug(
                f"Processing event {event_type.value} for session {session_id}"
            )
            
            # Process based on event type
            response = await self._route_event(context, event_data)
            
            # Update metrics
            self._update_metrics(response.success, time.time() - start_time)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing event: {e}")
            return PipelineResponse(
                success=False,
                errors=[f"Internal processing error: {str(e)}"],
                processing_time_ms=(time.time() - start_time) * 1000
            )
    
    async def create_session(self, user_data: Dict[str, Any]) -> PipelineResponse:
        """
        Create new user session
        
        Args:
            user_data: User information and session parameters
            
        Returns:
            PipelineResponse: Session creation result
        """
        try:
            # Create session through session manager
            session_id = await self.session_manager.create_session(user_data)
            
            # Generate initial UI schema
            schema_commands = await self._generate_initial_schema(session_id)
            
            # Create welcome commands
            welcome_commands = await self.command_generator.generate_session_created(
                session_id, user_data
            )
            
            all_commands = welcome_commands + schema_commands
            
            # Stream commands to client
            if self.sse_manager:
                await self.sse_manager.stream_commands(session_id, all_commands)
            
            return PipelineResponse(
                success=True,
                commands=all_commands,
                session_id=session_id,
                metadata={"action": "session_created"}
            )
            
        except Exception as e:
            self.logger.error(f"Error creating session: {e}")
            return PipelineResponse(
                success=False,
                errors=[f"Session creation failed: {str(e)}"]
            )
    
    async def handle_answer_event(
        self, 
        session_id: str, 
        event_data: Dict[str, Any]
    ) -> PipelineResponse:
        """
        Process answer change events
        
        Args:
            session_id: User session identifier
            event_data: Answer event data
            
        Returns:
            PipelineResponse: Processing result with UI updates
        """
        try:
            # Validate session exists
            if not await self.session_manager.session_exists(session_id):
                return PipelineResponse(
                    success=False,
                    errors=["Session not found"],
                    session_id=session_id
                )
            
            # Extract answer data
            question_id = event_data.get("question_id")
            answer_value = event_data.get("answer")
            trigger_evaluation = event_data.get("trigger_evaluation", False)
            
            if not question_id:
                return PipelineResponse(
                    success=False,
                    errors=["Missing question_id"],
                    session_id=session_id
                )
            
            # Process answer through event handler
            result = await self.event_handler.handle_answer_change(
                session_id=session_id,
                question_id=question_id,
                answer=answer_value,
                trigger_evaluation=trigger_evaluation
            )
            
            if not result.success:
                return PipelineResponse(
                    success=False,
                    errors=result.errors,
                    session_id=session_id
                )
            
            # Generate UI update commands
            commands = await self._generate_answer_commands(
                session_id, question_id, result
            )
            
            # Handle dependency cascades if needed
            if trigger_evaluation and result.cascaded_questions:
                cascade_commands = await self._handle_cascade_updates(
                    session_id, result.cascaded_questions
                )
                commands.extend(cascade_commands)
            
            # Stream commands to client
            if self.sse_manager:
                await self.sse_manager.stream_commands(session_id, commands)
            
            return PipelineResponse(
                success=True,
                commands=commands,
                session_id=session_id,
                metadata={
                    "question_id": question_id,
                    "cascaded_count": len(result.cascaded_questions) if result.cascaded_questions else 0
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error handling answer event: {e}")
            return PipelineResponse(
                success=False,
                errors=[f"Answer processing failed: {str(e)}"],
                session_id=session_id
            )
    
    async def handle_schema_request(
        self, 
        session_id: str, 
        question_id: str
    ) -> PipelineResponse:
        """
        Generate UI schema for specific question
        
        Args:
            session_id: User session identifier
            question_id: Question identifier
            
        Returns:
            PipelineResponse: UI schema commands
        """
        try:
            # Get session state
            session_state = await self.session_manager.get_session_state(session_id)
            if not session_state:
                return PipelineResponse(
                    success=False,
                    errors=["Session not found"],
                    session_id=session_id
                )
            
            # Generate schema
            schema = await self.ui_schema_generator.generate_question_schema(
                question_id, session_state
            )
            
            if not schema:
                return PipelineResponse(
                    success=False,
                    errors=[f"Could not generate schema for question {question_id}"],
                    session_id=session_id
                )
            
            # Create schema update command
            commands = [await self.command_generator.generate_schema_update(
                session_id, question_id, schema
            )]
            
            # Stream to client
            if self.sse_manager:
                await self.sse_manager.stream_commands(session_id, commands)
            
            return PipelineResponse(
                success=True,
                commands=commands,
                session_id=session_id,
                metadata={"question_id": question_id}
            )
            
        except Exception as e:
            self.logger.error(f"Error handling schema request: {e}")
            return PipelineResponse(
                success=False,
                errors=[f"Schema generation failed: {str(e)}"],
                session_id=session_id
            )
    
    async def handle_submit_event(self, session_id: str) -> PipelineResponse:
        """
        Process form submission
        
        Args:
            session_id: User session identifier
            
        Returns:
            PipelineResponse: Submission result
        """
        try:
            # Process submission through event handler
            result = await self.event_handler.handle_submit(session_id)
            
            if not result.success:
                return PipelineResponse(
                    success=False,
                    errors=result.errors,
                    session_id=session_id
                )
            
            # Generate submission complete commands
            commands = await self.command_generator.generate_submission_complete(
                session_id, result.submission_data
            )
            
            # Stream to client
            if self.sse_manager:
                await self.sse_manager.stream_commands(session_id, commands)
            
            return PipelineResponse(
                success=True,
                commands=commands,
                session_id=session_id,
                metadata={"action": "submission_complete"}
            )
            
        except Exception as e:
            self.logger.error(f"Error handling submit event: {e}")
            return PipelineResponse(
                success=False,
                errors=[f"Submission failed: {str(e)}"],
                session_id=session_id
            )
    
    async def get_health_status(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Get pipeline health status
        
        Returns:
            Tuple[bool, Dict]: Overall health and detailed status
        """
        overall_healthy, health_data = self.health.get_overall_health()
        
        health_data.update({
            "pipeline_status": self.status.value,
            "active_sessions": len(self.active_contexts) if hasattr(self, 'active_contexts') else 0,
            "metrics": self.metrics.copy()
        })
        
        return overall_healthy, health_data
    
    async def shutdown(self) -> None:
        """Gracefully shutdown pipeline and all components"""
        self.logger.info("Shutting down EventProcessingPipeline...")
        self.status = PipelineStatus.SHUTDOWN
        
        try:
            # Shutdown components
            if self.sse_manager:
                await self.sse_manager.shutdown()
            
            if self.session_manager:
                await self.session_manager.shutdown()
            
            # Shutdown executor
            self.executor.shutdown(wait=True, timeout=10)
            
            self.logger.info("EventProcessingPipeline shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    # Internal methods
    
    async def _initialize_session_manager(self) -> None:
        """Initialize session manager component"""
        try:
            self.session_manager = SessionManager(self.config.get("session", {}))
            await self.session_manager.initialize()
            self.health.update_status("session_manager", True)
        except Exception as e:
            self.health.update_status("session_manager", False)
            raise RuntimeError(f"Failed to initialize session manager: {e}")
    
    async def _initialize_dependency_engine(self) -> None:
        """Initialize dependency engine component"""
        try:
            self.dependency_engine = DependencyEngine(self.config.get("dependencies", {}))
            await self.dependency_engine.initialize()
            self.health.update_status("dependency_engine", True)
        except Exception as e:
            self.health.update_status("dependency_engine", False)
            raise RuntimeError(f"Failed to initialize dependency engine: {e}")
    
    async def _initialize_ui_schema_generator(self) -> None:
        """Initialize UI schema generator component"""
        try:
            self.ui_schema_generator = UISchemaGenerator(self.config.get("ui_schema", {}))
            await self.ui_schema_generator.initialize()
            self.health.update_status("ui_schema_generator", True)
        except Exception as e:
            self.health.update_status("ui_schema_generator", False)
            raise RuntimeError(f"Failed to initialize UI schema generator: {e}")
    
    async def _initialize_command_generator(self) -> None:
        """Initialize command generator component"""
        try:
            self.command_generator = CommandGenerator(self.config.get("commands", {}))
            await self.command_generator.initialize()
            self.health.update_status("command_generator", True)
        except Exception as e:
            self.health.update_status("command_generator", False)
            raise RuntimeError(f"Failed to initialize command generator: {e}")
    
    async def _initialize_event_handler(self) -> None:
        """Initialize event handler component"""
        try:
            self.event_handler = EventHandler({
                "session_manager": self.session_manager,
                "dependency_engine": self.dependency_engine,
                "config": self.config.get("events", {})
            })
            await self.event_handler.initialize()
            self.health.update_status("event_handler", True)
        except Exception as e:
            self.health.update_status("event_handler", False)
            raise RuntimeError(f"Failed to initialize event handler: {e}")
    
    async def _initialize_sse_manager(self) -> None:
        """Initialize SSE manager component"""
        try:
            self.sse_manager = SSEManager(self.config.get("sse", {}))
            await self.sse_manager.initialize()
            self.health.update_status("sse_manager", True)
        except Exception as e:
            self.health.update_status("sse_manager", False)
            raise RuntimeError(f"Failed to initialize SSE manager: {e}")
    
    async def _verify_component_health(self) -> bool:
        """Verify all components are healthy"""
        required_components = [
            "session_manager", "dependency_engine", "ui_schema_generator",
            "command_generator", "event_handler", "sse_manager"
        ]
        
        for component in required_components:
            if not self.health.is_healthy(component):
                self.logger.error(f"Component {component} is not healthy")
                return False
        
        return True
    
    def _validate_event_data(self, event_data: Dict[str, Any]) -> bool:
        """Validate event data format"""
        if not isinstance(event_data, dict):
            return False
        
        if "type" not in event_data:
            return False
        
        try:
            EventType(event_data["type"])
        except ValueError:
            return False
        
        return True
    
    async def _route_event(
        self, 
        context: ProcessingContext, 
        event_data: Dict[str, Any]
    ) -> PipelineResponse:
        """Route event to appropriate handler"""
        async with self.processing_lock:
            self.active_contexts[context.request_id] = context
        
        try:
            if context.event_type == EventType.SESSION_CREATE:
                return await self.create_session(event_data.get("user_data", {}))
            
            elif context.event_type == EventType.ANSWER_CHANGE:
                return await self.handle_answer_event(context.session_id, event_data)
            
            elif context.event_type == EventType.ANSWER_BLUR:
                # Trigger evaluation for answer blur
                event_data["trigger_evaluation"] = True
                return await self.handle_answer_event(context.session_id, event_data)
            
            elif context.event_type == EventType.SCHEMA_REQUEST:
                question_id = event_data.get("question_id", "")
                return await self.handle_schema_request(context.session_id, question_id)
            
            elif context.event_type == EventType.SUBMIT:
                return await self.handle_submit_event(context.session_id)
            
            elif context.event_type == EventType.HEALTH_CHECK:
                healthy, status = await self.get_health_status()
                return PipelineResponse(
                    success=healthy,
                    metadata={"health_status": status}
                )
            
            else:
                return PipelineResponse(
                    success=False,
                    errors=[f"Unsupported event type: {context.event_type.value}"]
                )
        
        finally:
            async with self.processing_lock:
                self.active_contexts.pop(context.request_id, None)
    
    async def _generate_initial_schema(self, session_id: str) -> List[Dict[str, Any]]:
        """Generate initial UI schema for new session"""
        try:
            session_state = await self.session_manager.get_session_state(session_id)
            if not session_state:
                return []
            
            # Get first questions to display
            initial_questions = await self.dependency_engine.get_initial_questions(session_id)
            
            commands = []
            for question_id in initial_questions:
                schema = await self.ui_schema_generator.generate_question_schema(
                    question_id, session_state
                )
                if schema:
                    command = await self.command_generator.generate_schema_update(
                        session_id, question_id, schema
                    )
                    commands.append(command)
            
            return commands
            
        except Exception as e:
            self.logger.error(f"Error generating initial schema: {e}")
            return []
    
    async def _generate_answer_commands(
        self,
        session_id: str,
        question_id: str,
        result: Any
    ) -> List[Dict[str, Any]]:
        """Generate commands for answer updates"""
        commands = []
        
        try:
            # Generate answer update command
            answer_command = await self.command_generator.generate_answer_update(
                session_id, question_id, result.answer_value
            )
            commands.append(answer_command)
            
            # Generate validation result if present
            if hasattr(result, 'validation_result') and result.validation_result:
                validation_command = await self.command_generator.generate_validation_result(
                    session_id, question_id, result.validation_result
                )
                commands.append(validation_command)
            
            # Generate evaluation result if present
            if hasattr(result, 'evaluation_result') and result.evaluation_result:
                eval_command = await self.command_generator.generate_evaluation_result(
                    session_id, question_id, result.evaluation_result
                )
                commands.append(eval_command)
            
        except Exception as e:
            self.logger.error(f"Error generating answer commands: {e}")
        
        return commands
    
    async def _handle_cascade_updates(
        self,
        session_id: str,
        cascaded_questions: List[str]
    ) -> List[Dict[str, Any]]:
        """Handle cascade updates for dependent questions"""
        commands = []
        
        try:
            for question_id in cascaded_questions:
                # Generate updated schema for cascaded question
                session_state = await self.session_manager.get_session_state(session_id)
                if session_state:
                    schema = await self.ui_schema_generator.generate_question_schema(
                        question_id, session_state
                    )
                    if schema:
                        command = await self.command_generator.generate_schema_update(
                            session_id, question_id, schema
                        )
                        commands.append(command)
            
        except Exception as e:
            self.logger.error(f"Error handling cascade updates: {e}")
        
        return commands
    
    def _update_metrics(self, success: bool, processing_time: float) -> None:
        """Update processing metrics"""
        self.metrics["total_events"] += 1
        
        if success:
            self.metrics["successful_events"] += 1
        else:
            self.metrics["failed_events"] += 1
        
        # Update average processing time
        total_events = self.metrics["total_events"]
        current_avg = self.metrics["average_processing_time"]
        self.metrics["average_processing_time"] = (
            (current_avg * (total_events - 1) + processing_time) / total_events
        )


# Pipeline factory function
async def create_pipeline(config: Dict[str, Any]) -> EventProcessingPipeline:
    """
    Factory function to create and initialize pipeline
    
    Args:
        config: Pipeline configuration
        
    Returns:
        EventProcessingPipeline: Initialized pipeline instance
    """
    pipeline = EventProcessingPipeline(config)
    
    if await pipeline.initialize():
        return pipeline
    else:
        raise RuntimeError("Failed to initialize EventProcessingPipeline")


# Context manager for pipeline lifecycle
@asynccontextmanager
async def managed_pipeline(config: Dict[str, Any]):
    """
    Context manager for pipeline lifecycle management
    
    Args:
        config: Pipeline configuration
        
    Yields:
        EventProcessingPipeline: Initialized pipeline instance
    """
    pipeline = None
    try:
        pipeline = await create_pipeline(config)
        yield pipeline
    finally:
        if pipeline:
            await pipeline.shutdown()