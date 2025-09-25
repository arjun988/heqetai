"""
Base integration classes for AgentDebugger framework integrations.
"""

import inspect
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..events import EventType, TraceEvent
from ..state import AgentState


class BaseIntegration(ABC):
    """Base class for framework integrations with enhanced features"""
    
    def __init__(self, debugger):
        self.debugger = debugger
        self.original_methods: Dict[str, Any] = {}
        self.instrumented_agents: Dict[str, Any] = {}
        self.framework_events: List[TraceEvent] = []
        self.integration_metadata: Dict[str, Any] = {
            'integration_type': self.__class__.__name__,
            'instrumentation_count': 0,
            'error_count': 0
        }
        
    @abstractmethod
    def instrument_agent(self, agent: Any, agent_id: str) -> Any:
        """Instrument an agent with debugging capabilities"""
        pass
        
    @abstractmethod
    def extract_events(self, execution_data: Any) -> List[TraceEvent]:
        """Extract trace events from framework execution data"""
        pass
    
    def instrument_async_agent(self, agent: Any, agent_id: str) -> Any:
        """Instrument an async agent with debugging capabilities"""
        # Default implementation falls back to sync instrumentation
        return self.instrument_agent(agent, agent_id)
        
    def restore_agent(self, agent: Any):
        """Restore agent to original state (remove instrumentation)"""
        for method_name, original_method in self.original_methods.items():
            if hasattr(agent, method_name):
                setattr(agent, method_name, original_method)
        self.original_methods.clear()
        
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get integration statistics"""
        return {
            **self.integration_metadata,
            'instrumented_agents': list(self.instrumented_agents.keys()),
            'framework_events_count': len(self.framework_events)
        }
        
    def _emit_framework_event(self, event_type: str, agent_id: str, data: Dict[str, Any]):
        """Emit framework-specific event"""
        event = TraceEvent(
            event_type=EventType.REASONING_START,  # Use base event type
            agent_id=agent_id,
            step_id=f"framework_{event_type}_{int(datetime.now().timestamp())}",
            data={
                'framework_event_type': event_type,
                'framework': self.__class__.__name__.replace('Integration', ''),
                **data
            },
            metadata={'framework_specific': True}
        )
        self.framework_events.append(event)
        if hasattr(self.debugger, '_emit_event'):
            self.debugger._emit_event(event)
        else:
            self.debugger.trace_events.append(event)
