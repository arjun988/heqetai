"""
AutoGPT integration for AgentDebugger.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..debugger import AgentDebugger
from ..events import EventType, TraceEvent
from ..state import AgentState
from .base import BaseIntegration


class AutoGPTIntegration(BaseIntegration):
    """Enhanced integration for AutoGPT agents"""
    
    def instrument_agent(self, agent: Any, agent_id: str) -> Any:
        """Instrument AutoGPT agent with enhanced features"""
        self.instrumented_agents[agent_id] = agent
        
        # Enhanced AutoGPT method detection
        methods_instrumented = []
        
        if hasattr(agent, 'start_interaction_loop'):
            self._instrument_interaction_loop(agent, agent_id)
            methods_instrumented.append('start_interaction_loop')
            
        if hasattr(agent, 'execute_command'):
            self._instrument_command_execution(agent, agent_id)
            methods_instrumented.append('execute_command')
            
        if hasattr(agent, 'chat'):
            self._instrument_chat(agent, agent_id)
            methods_instrumented.append('chat')
            
        # Emit framework event
        self._emit_framework_event('autogpt_instrumented', agent_id, {
            'methods_instrumented': methods_instrumented,
            'agent_name': getattr(agent, 'ai_name', 'Unknown')
        })
            
        return agent
        
    def _instrument_interaction_loop(self, agent: Any, agent_id: str):
        """Instrument AutoGPT interaction loop with enhanced features"""
        original_loop = agent.start_interaction_loop
        
        def debugged_interaction_loop(*args, **kwargs):
            event = TraceEvent(
                event_type=EventType.REASONING_START,
                agent_id=agent_id,
                step_id=f"interaction_loop_{int(datetime.now().timestamp())}",
                data={
                    'agent_name': getattr(agent, 'ai_name', 'AutoGPT'),
                    'framework': 'AutoGPT',
                    'loop_type': 'interaction'
                }
            )
            self.debugger.trace_events.append(event)
            
            result = original_loop(*args, **kwargs)
            
            end_event = TraceEvent(
                event_type=EventType.REASONING_END,
                agent_id=agent_id,
                step_id=event.step_id,
                data={'loop_result': 'completed'},
                parent_event_id=event.id
            )
            self.debugger.trace_events.append(end_event)
            
            return result
            
        agent.start_interaction_loop = debugged_interaction_loop
        self.original_methods['start_interaction_loop'] = original_loop
        
    def _instrument_command_execution(self, agent: Any, agent_id: str):
        """Instrument AutoGPT command execution with enhanced features"""
        original_execute = agent.execute_command
        
        def debugged_execute_command(command_name, arguments, *args, **kwargs):
            event = TraceEvent(
                event_type=EventType.TOOL_CALL_START,
                agent_id=agent_id,
                step_id=f"command_{int(datetime.now().timestamp())}",
                data={
                    'command_name': command_name,
                    'arguments': arguments,
                    'framework': 'AutoGPT'
                }
            )
            self.debugger.trace_events.append(event)
            
            # Check for mocked output
            mock_output = self.debugger.mock_registry.get_tool_mock(command_name)
            if mock_output is not None:
                return mock_output
                
            start_time = datetime.now()
            result = original_execute(command_name, arguments, *args, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            
            end_event = TraceEvent(
                event_type=EventType.TOOL_CALL_END,
                agent_id=agent_id,
                step_id=event.step_id,
                data={
                    'command_name': command_name,
                    'result': str(result)[:200] + "..." if len(str(result)) > 200 else str(result),
                    'duration': duration
                },
                parent_event_id=event.id
            )
            self.debugger.trace_events.append(end_event)
            
            return result
            
        agent.execute_command = debugged_execute_command
        self.original_methods['execute_command'] = original_execute
        
    def _instrument_chat(self, agent: Any, agent_id: str):
        """Instrument AutoGPT chat method"""
        if hasattr(agent, 'chat'):
            original_chat = agent.chat
            
            def debugged_chat(message, *args, **kwargs):
                event = TraceEvent(
                    event_type=EventType.LLM_CALL_START,
                    agent_id=agent_id,
                    step_id=f"chat_{int(datetime.now().timestamp())}",
                    data={
                        'message': str(message)[:100] + "..." if len(str(message)) > 100 else str(message),
                        'framework': 'AutoGPT'
                    }
                )
                self.debugger.trace_events.append(event)
                
                result = original_chat(message, *args, **kwargs)
                
                end_event = TraceEvent(
                    event_type=EventType.LLM_CALL_END,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={'response': str(result)[:200] + "..." if len(str(result)) > 200 else str(result)},
                    parent_event_id=event.id
                )
                self.debugger.trace_events.append(end_event)
                
                return result
                
            agent.chat = debugged_chat
            self.original_methods['chat'] = original_chat
        
    def extract_events(self, execution_data: Any) -> List[TraceEvent]:
        """Extract events from AutoGPT execution data"""
        return []


class AutoGPTDebugger(AgentDebugger):
    """Specialized debugger for AutoGPT agents with enhanced features"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.integration = AutoGPTIntegration(self)
        self.framework = "AutoGPT"
        
    def attach(self, agent, agent_id: Optional[str] = None):
        """Attach debugger to AutoGPT agent with enhanced features"""
        if agent_id is None:
            agent_id = f"autogpt_{len(self._attached_agents)}"
            
        self._attached_agents[agent_id] = agent
        self.agent_states[agent_id] = AgentState(agent_id)
        
        debugged_agent = self.integration.instrument_agent(agent, agent_id)
        
        agent_name = getattr(agent, 'ai_name', 'Unknown')
        print(f"🤖 AutoGPT debugger attached to '{agent_id}' ({agent_name})")
        print(f"   Methods instrumented: {list(self.integration.original_methods.keys())}")
        
        return debugged_agent
        
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get AutoGPT integration statistics"""
        return self.integration.get_integration_stats()
