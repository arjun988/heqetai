"""
CrewAI integration for AgentDebugger.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..debugger import AgentDebugger
from ..events import EventType, TraceEvent
from ..state import AgentState
from .base import BaseIntegration


class CrewAIIntegration(BaseIntegration):
    """Enhanced integration for CrewAI agents and crews"""
    
    def instrument_agent(self, crew_or_agent: Any, agent_id: str) -> Any:
        """Instrument CrewAI Crew or Agent with enhanced features"""
        self.instrumented_agents[agent_id] = crew_or_agent
        
        if hasattr(crew_or_agent, 'kickoff'):  # It's a Crew
            self._instrument_crew(crew_or_agent, agent_id)
        elif hasattr(crew_or_agent, 'execute_task'):  # It's an Agent
            self._instrument_crewai_agent(crew_or_agent, agent_id)
        elif hasattr(crew_or_agent, 'task_execution'):  # Alternative method
            self._instrument_task_execution(crew_or_agent, agent_id)
            
        # Emit framework event
        self._emit_framework_event('crewai_instrumented', agent_id, {
            'component_type': 'Crew' if hasattr(crew_or_agent, 'kickoff') else 'Agent',
            'methods': list(self.original_methods.keys())
        })
            
        return crew_or_agent
        
    def _instrument_crew(self, crew: Any, crew_id: str):
        """Instrument CrewAI Crew with enhanced features"""
        original_kickoff = crew.kickoff
        
        def debugged_kickoff(*args, **kwargs):
            # Enhanced crew startup event
            event = TraceEvent(
                event_type=EventType.TASK_START,
                agent_id=crew_id,
                step_id=f"crew_kickoff_{int(datetime.now().timestamp())}",
                data={
                    'crew_agents': [getattr(agent, 'role', 'Unknown') for agent in crew.agents] if hasattr(crew, 'agents') else [],
                    'tasks_count': len(crew.tasks) if hasattr(crew, 'tasks') else 0,
                    'framework': 'CrewAI',
                    'crew_type': type(crew).__name__
                }
            )
            self.debugger.trace_events.append(event)
            
            # Instrument individual agents in the crew
            if hasattr(crew, 'agents'):
                for i, agent in enumerate(crew.agents):
                    agent_id = f"{crew_id}_agent_{i}"
                    self._instrument_crewai_agent(agent, agent_id)
            
            start_time = datetime.now()
            result = original_kickoff(*args, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            
            end_event = TraceEvent(
                event_type=EventType.TASK_END,
                agent_id=crew_id,
                step_id=event.step_id,
                data={
                    'result': str(result)[:300] + "..." if len(str(result)) > 300 else str(result),
                    'duration': duration,
                    'success': True
                },
                parent_event_id=event.id
            )
            self.debugger.trace_events.append(end_event)
            
            return result
            
        crew.kickoff = debugged_kickoff
        self.original_methods['kickoff'] = original_kickoff
        
    def _instrument_crewai_agent(self, agent: Any, agent_id: str):
        """Instrument individual CrewAI Agent with enhanced features"""
        if hasattr(agent, 'execute_task'):
            original_execute = agent.execute_task
            
            def debugged_execute_task(task, *args, **kwargs):
                # Enhanced task execution event
                event = TraceEvent(
                    event_type=EventType.REASONING_START,
                    agent_id=agent_id,
                    step_id=f"task_execute_{int(datetime.now().timestamp())}",
                    data={
                        'agent_role': getattr(agent, 'role', 'Unknown'),
                        'agent_goal': getattr(agent, 'goal', ''),
                        'task': str(task)[:200] + "..." if len(str(task)) > 200 else str(task),
                        'framework': 'CrewAI'
                    }
                )
                self.debugger.trace_events.append(event)
                
                start_time = datetime.now()
                result = original_execute(task, *args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                
                end_event = TraceEvent(
                    event_type=EventType.REASONING_END,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={
                        'task_result': str(result)[:200] + "..." if len(str(result)) > 200 else str(result),
                        'duration': duration
                    },
                    parent_event_id=event.id
                )
                self.debugger.trace_events.append(end_event)
                
                return result
                
            agent.execute_task = debugged_execute_task
            self.original_methods[f'{agent_id}_execute_task'] = original_execute
            
        # Enhanced tool instrumentation
        if hasattr(agent, 'tools') and agent.tools:
            for tool in agent.tools:
                self._instrument_crewai_tool(tool, agent_id)
                
    def _instrument_task_execution(self, agent: Any, agent_id: str):
        """Instrument alternative task execution method"""
        original_task_exec = agent.task_execution
        
        def debugged_task_execution(task, context=None):
            event = TraceEvent(
                event_type=EventType.REASONING_START,
                agent_id=agent_id,
                step_id=f"task_exec_{int(datetime.now().timestamp())}",
                data={
                    'task': str(task),
                    'context': str(context)[:100] if context else None
                }
            )
            self.debugger.trace_events.append(event)
            
            result = original_task_exec(task, context)
            
            end_event = TraceEvent(
                event_type=EventType.REASONING_END,
                agent_id=agent_id,
                step_id=event.step_id,
                data={'result': str(result)[:200] + "..." if len(str(result)) > 200 else str(result)},
                parent_event_id=event.id
            )
            self.debugger.trace_events.append(end_event)
            
            return result
            
        agent.task_execution = debugged_task_execution
        self.original_methods['task_execution'] = original_task_exec
                
    def _instrument_crewai_tool(self, tool: Any, agent_id: str):
        """Instrument CrewAI tools with enhanced features"""
        if hasattr(tool, 'run'):
            original_run = tool.run
            tool_name = getattr(tool, 'name', type(tool).__name__)
            
            def debugged_tool_run(*args, **kwargs):
                event = TraceEvent(
                    event_type=EventType.TOOL_CALL_START,
                    agent_id=agent_id,
                    step_id=f"tool_{int(datetime.now().timestamp())}",
                    data={
                        'tool_name': tool_name,
                        'args': str(args)[:100] + "..." if len(str(args)) > 100 else str(args),
                        'kwargs': kwargs,
                        'framework': 'CrewAI'
                    }
                )
                self.debugger.trace_events.append(event)
                
                # Check for mocked output
                mock_output = self.debugger.mock_registry.get_tool_mock(tool_name)
                if mock_output is not None:
                    return mock_output
                    
                start_time = datetime.now()
                result = original_run(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                
                end_event = TraceEvent(
                    event_type=EventType.TOOL_CALL_END,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={
                        'tool_name': tool_name, 
                        'result': str(result)[:200] + "..." if len(str(result)) > 200 else str(result),
                        'duration': duration
                    },
                    parent_event_id=event.id
                )
                self.debugger.trace_events.append(end_event)
                
                return result
                
            tool.run = debugged_tool_run
            self.original_methods[f'{tool_name}_run'] = original_run
            
    def extract_events(self, execution_data: Any) -> List[TraceEvent]:
        """Extract events from CrewAI execution data"""
        events = []
        # Enhanced CrewAI event extraction
        if hasattr(execution_data, 'tasks') and hasattr(execution_data, 'results'):
            for task, result in zip(execution_data.tasks, execution_data.results):
                event = TraceEvent(
                    event_type=EventType.TASK_END,
                    agent_id="crewai_execution",
                    step_id=f"crew_task_{int(datetime.now().timestamp())}",
                    data={
                        'task': str(task),
                        'result': str(result),
                        'framework': 'CrewAI'
                    }
                )
                events.append(event)
        return events


class CrewAIDebugger(AgentDebugger):
    """Specialized debugger for CrewAI agents and crews with enhanced features"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.integration = CrewAIIntegration(self)
        self.framework = "CrewAI"
        
    def attach(self, crew_or_agent, agent_id: Optional[str] = None):
        """Attach debugger to CrewAI crew or agent with enhanced features"""
        if agent_id is None:
            agent_id = f"crewai_{len(self._attached_agents)}"
            
        self._attached_agents[agent_id] = crew_or_agent
        self.agent_states[agent_id] = AgentState(agent_id)
        
        debugged_entity = self.integration.instrument_agent(crew_or_agent, agent_id)
        
        component_type = "Crew" if hasattr(crew_or_agent, 'kickoff') else "Agent"
        print(f"🚢 CrewAI debugger attached to {component_type} '{agent_id}'")
        print(f"   Methods instrumented: {list(self.integration.original_methods.keys())}")
        
        return debugged_entity
        
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get CrewAI integration statistics"""
        return self.integration.get_integration_stats()
