"""
AgentDebugger Framework Integrations
===================================

Integration adapters for popular AI agent frameworks including
LangChain, CrewAI, AutoGPT, and LlamaIndex.

These adapters provide seamless debugging capabilities by automatically
instrumenting framework-specific methods and converting framework events
into AgentDebugger trace events.

NEW FEATURES:
- Async method support
- Better error handling and recovery
- Integration-specific event types
- Performance monitoring per framework
- Advanced instrumentation options
"""

import asyncio
import inspect
import functools
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Union
from datetime import datetime
import logging

from main import AgentDebugger, TraceEvent, EventType, AgentState, BreakpointType

# Set up logging
logger = logging.getLogger(__name__)


class BaseIntegration(ABC):
    """Base class for framework integrations with enhanced features"""
    
    def __init__(self, debugger: AgentDebugger):
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
        
    # Removed unused _safe_instrument helper to reduce surface area
        
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


class LangChainIntegration(BaseIntegration):
    """Enhanced integration for LangChain agents and chains"""
    
    def instrument_agent(self, agent: Any, agent_id: str) -> Any:
        """Instrument LangChain agent/chain with enhanced capabilities"""
        self.instrumented_agents[agent_id] = agent
        
        # Handle different LangChain components with better detection
        if hasattr(agent, 'ainvoke') or hasattr(agent, 'ainvoke'):  # Async support
            return self._instrument_async_runnable(agent, agent_id)
        elif hasattr(agent, 'invoke'):  # New LangChain LCEL syntax
            return self._instrument_runnable(agent, agent_id)
        elif hasattr(agent, 'run'):  # Legacy Agent interface
            self._instrument_legacy_agent(agent, agent_id)
        elif hasattr(agent, '__call__'):  # Chain interface
            self._instrument_chain(agent, agent_id)
        elif hasattr(agent, 'predict'):  # LLMChain interface
            self._instrument_llm_chain(agent, agent_id)
            
        # Emit framework detection event
        self._emit_framework_event('agent_instrumented', agent_id, {
            'agent_type': type(agent).__name__,
            'methods_instrumented': list(self.original_methods.keys())
        })
            
        return agent
    
    def instrument_async_agent(self, agent: Any, agent_id: str) -> Any:
        """Instrument async LangChain agent"""
        if hasattr(agent, 'ainvoke'):
            return self._instrument_async_runnable(agent, agent_id)
        return self.instrument_agent(agent, agent_id)
        
    def _instrument_async_runnable(self, runnable: Any, agent_id: str):
        """Instrument async LangChain Runnable by returning a proxy (no setattr)."""
        original_invoke = getattr(runnable, 'invoke', None)
        original_ainvoke = getattr(runnable, 'ainvoke', None)

        # Prepare sync wrapper if available
        def _build_debugged_invoke():
            if original_invoke is None:
                return None

            def debugged_invoke(input_data, config=None, **kwargs):
                event = TraceEvent(
                    event_type=EventType.REASONING_START,
                    agent_id=agent_id,
                    step_id=f"invoke_{int(datetime.now().timestamp())}",
                    data={
                        'input': str(input_data)[:200] + "..." if len(str(input_data)) > 200 else str(input_data),
                        'runnable_type': type(runnable).__name__,
                        'config': config,
                        'framework': 'LangChain',
                        'input_type': type(input_data).__name__
                    }
                )
                self.debugger.trace_events.append(event)

                if self.debugger._should_break(event):
                    self.debugger._trigger_breakpoint(event, agent_id)

                try:
                    start_time = datetime.now()
                    result = original_invoke(input_data, config, **kwargs)
                    duration = (datetime.now() - start_time).total_seconds()

                    end_event = TraceEvent(
                        event_type=EventType.REASONING_END,
                        agent_id=agent_id,
                        step_id=event.step_id,
                        data={
                            'output': str(result)[:200] + "..." if len(str(result)) > 200 else str(result),
                            'success': True,
                            'duration': duration,
                            'output_type': type(result).__name__
                        },
                        parent_event_id=event.id
                    )
                    self.debugger.trace_events.append(end_event)
                    return result
                except Exception as e:
                    duration = (datetime.now() - start_time).total_seconds()
                    error_event = TraceEvent(
                        event_type=EventType.ERROR,
                        agent_id=agent_id,
                        step_id=event.step_id,
                        data={
                            'error': str(e),
                            'error_type': type(e).__name__,
                            'duration': duration
                        },
                        parent_event_id=event.id
                    )
                    self.debugger.trace_events.append(error_event)
                    if self.debugger._should_break(error_event):
                        self.debugger._trigger_breakpoint(error_event, agent_id)
                    raise

            self.original_methods['invoke'] = original_invoke
            return debugged_invoke

        def _build_debugged_ainvoke():
            if original_ainvoke is None:
                return None

            async def debugged_ainvoke(input_data, config=None, **kwargs):
                event = TraceEvent(
                    event_type=EventType.REASONING_START,
                    agent_id=agent_id,
                    step_id=f"async_invoke_{int(datetime.now().timestamp())}",
                    data={
                        'input': str(input_data)[:200] + "..." if len(str(input_data)) > 200 else str(input_data),
                        'runnable_type': type(runnable).__name__,
                        'config': config,
                        'async': True
                    }
                )
                self.debugger.trace_events.append(event)

                if self.debugger._should_break(event):
                    self.debugger._trigger_breakpoint(event, agent_id)

                try:
                    result = await original_ainvoke(input_data, config, **kwargs)
                    end_event = TraceEvent(
                        event_type=EventType.REASONING_END,
                        agent_id=agent_id,
                        step_id=event.step_id,
                        data={
                            'output': str(result)[:200] + "..." if len(str(result)) > 200 else str(result),
                            'success': True,
                            'async': True
                        },
                        parent_event_id=event.id
                    )
                    self.debugger.trace_events.append(end_event)
                    return result
                except Exception as e:
                    error_event = TraceEvent(
                        event_type=EventType.ERROR,
                        agent_id=agent_id,
                        step_id=event.step_id,
                        data={
                            'error': str(e),
                            'error_type': type(e).__name__,
                            'async': True
                        },
                        parent_event_id=event.id
                    )
                    self.debugger.trace_events.append(error_event)
                    if self.debugger._should_break(error_event):
                        self.debugger._trigger_breakpoint(error_event, agent_id)
                    raise

            self.original_methods['ainvoke'] = original_ainvoke
            return debugged_ainvoke

        debugged_invoke = _build_debugged_invoke()
        debugged_ainvoke = _build_debugged_ainvoke()

        class _AsyncRunnableProxy:
            def __init__(self, underlying, debug_invoke, debug_ainvoke):
                self._underlying = underlying
                self._debug_invoke = debug_invoke
                self._debug_ainvoke = debug_ainvoke

            def invoke(self, input_data, config=None, **kwargs):
                if self._debug_invoke is None:
                    # Fallback to underlying if no sync wrapper
                    return self._underlying.invoke(input_data, config, **kwargs)
                return self._debug_invoke(input_data, config, **kwargs)

            async def ainvoke(self, input_data, config=None, **kwargs):
                if self._debug_ainvoke is None:
                    # Fallback: run sync in thread if async not available
                    import asyncio
                    return await asyncio.get_event_loop().run_in_executor(None, self.invoke, input_data, config, **kwargs)
                return await self._debug_ainvoke(input_data, config, **kwargs)

            def batch(self, inputs, config=None, **kwargs):
                results = []
                for input_data in inputs:
                    results.append(self.invoke(input_data, config, **kwargs))
                return results

            def __getattr__(self, name):
                return getattr(self._underlying, name)

        return _AsyncRunnableProxy(runnable, debugged_invoke, debugged_ainvoke)
        
    def _instrument_runnable(self, runnable: Any, agent_id: str):
        """Instrument LangChain Runnable (LCEL) with enhanced features"""
        original_invoke = runnable.invoke

        def debugged_invoke(input_data, config=None, **kwargs):
            # Enhanced event data with framework specifics
            event = TraceEvent(
                event_type=EventType.REASONING_START,
                agent_id=agent_id,
                step_id=f"invoke_{int(datetime.now().timestamp())}",
                data={
                    'input': str(input_data)[:200] + "..." if len(str(input_data)) > 200 else str(input_data),
                    'runnable_type': type(runnable).__name__,
                    'config': config,
                    'framework': 'LangChain',
                    'input_type': type(input_data).__name__
                }
            )
            self.debugger.trace_events.append(event)

            if self.debugger._should_break(event):
                self.debugger._trigger_breakpoint(event, agent_id)

            try:
                # Add performance monitoring
                start_time = datetime.now()
                result = original_invoke(input_data, config, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()

                end_event = TraceEvent(
                    event_type=EventType.REASONING_END,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={
                        'output': str(result)[:200] + "..." if len(str(result)) > 200 else str(result),
                        'success': True,
                        'duration': duration,
                        'output_type': type(result).__name__
                    },
                    parent_event_id=event.id
                )
                self.debugger.trace_events.append(end_event)
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                error_event = TraceEvent(
                    event_type=EventType.ERROR,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'duration': duration
                    },
                    parent_event_id=event.id
                )
                self.debugger.trace_events.append(error_event)
                if self.debugger._should_break(error_event):
                    self.debugger._trigger_breakpoint(error_event, agent_id)
                raise

        # Enhanced proxy for better compatibility
        class _RunnableProxy:
            def __init__(self, underlying, debug_invoke):
                self._underlying = underlying
                self._debug_invoke = debug_invoke

            def invoke(self, input_data, config=None, **kwargs):
                return self._debug_invoke(input_data, config, **kwargs)
                
            def batch(self, inputs, config=None, **kwargs):
                # Instrument batch operations
                results = []
                for i, input_data in enumerate(inputs):
                    result = self._debug_invoke(input_data, config, **kwargs)
                    results.append(result)
                return results

            def __getattr__(self, name):
                return getattr(self._underlying, name)

        self.original_methods['invoke'] = original_invoke
        return _RunnableProxy(runnable, debugged_invoke)
        
    def _instrument_llm_chain(self, chain: Any, agent_id: str):
        """Instrument LangChain LLMChain"""
        if hasattr(chain, 'predict'):
            original_predict = chain.predict
            
            def debugged_predict(**kwargs):
                event = TraceEvent(
                    event_type=EventType.LLM_CALL_START,
                    agent_id=agent_id,
                    step_id=f"predict_{int(datetime.now().timestamp())}",
                    data={
                        'chain_type': type(chain).__name__,
                        'kwargs': kwargs,
                        'framework': 'LangChain'
                    }
                )
                self.debugger.trace_events.append(event)
                
                result = original_predict(**kwargs)
                
                end_event = TraceEvent(
                    event_type=EventType.LLM_CALL_END,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={
                        'result': str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                    },
                    parent_event_id=event.id
                )
                self.debugger.trace_events.append(end_event)
                
                return result
                
            chain.predict = debugged_predict
            self.original_methods['predict'] = original_predict
            
    def _instrument_legacy_agent(self, agent: Any, agent_id: str):
        """Instrument legacy LangChain Agent with enhanced features"""
        if hasattr(agent, 'run'):
            original_run = agent.run
            
            def debugged_run(input_text, **kwargs):
                event = TraceEvent(
                    event_type=EventType.REASONING_START,
                    agent_id=agent_id,
                    step_id=f"agent_run_{int(datetime.now().timestamp())}",
                    data={
                        'input': input_text,
                        'kwargs': kwargs,
                        'agent_type': type(agent).__name__
                    }
                )
                self.debugger.trace_events.append(event)
                
                start_time = datetime.now()
                result = original_run(input_text, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                
                end_event = TraceEvent(
                    event_type=EventType.REASONING_END,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={
                        'output': result,
                        'duration': duration
                    },
                    parent_event_id=event.id
                )
                self.debugger.trace_events.append(end_event)
                
                return result
                
            agent.run = debugged_run
            self.original_methods['run'] = original_run
            
        # Enhanced tool instrumentation
        if hasattr(agent, 'tools'):
            self._instrument_tools(agent.tools, agent_id)
            
    def _instrument_tools(self, tools: List[Any], agent_id: str):
        """Instrument LangChain tools with enhanced features"""
        for i, tool in enumerate(tools):
            tool_name = getattr(tool, 'name', f"{type(tool).__name__}_{i}")
            
            # Instrument both sync and async methods
            if hasattr(tool, '_run'):
                self._instrument_tool_method(tool, '_run', tool_name, agent_id, sync=True)
            if hasattr(tool, '_arun'):
                self._instrument_tool_method(tool, '_arun', tool_name, agent_id, sync=False)
                
    def _instrument_tool_method(self, tool: Any, method_name: str, tool_name: str, agent_id: str, sync: bool = True):
        """Instrument individual tool method"""
        original_method = getattr(tool, method_name)
        
        def debugged_tool_run(*args, **kwargs):
            event_type = EventType.TOOL_CALL_START
            event = TraceEvent(
                event_type=event_type,
                agent_id=agent_id,
                step_id=f"tool_{int(datetime.now().timestamp())}",
                data={
                    'tool_name': tool_name,
                    'args': str(args)[:100] + "..." if len(str(args)) > 100 else str(args),
                    'kwargs': kwargs,
                    'async': not sync
                }
            )
            self.debugger.trace_events.append(event)
            
            # Check for mocked output
            mock_output = self.debugger.mock_registry.get_tool_mock(tool_name)
            if mock_output is not None:
                return mock_output
                
            start_time = datetime.now()
            try:
                result = original_method(*args, **kwargs)
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
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                error_event = TraceEvent(
                    event_type=EventType.ERROR,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={
                        'tool_name': tool_name,
                        'error': str(e),
                        'duration': duration
                    },
                    parent_event_id=event.id
                )
                self.debugger.trace_events.append(error_event)
                raise
                
        setattr(tool, method_name, debugged_tool_run)
        self.original_methods[f'{tool_name}_{method_name}'] = original_method
                
    def extract_events(self, execution_data: Any) -> List[TraceEvent]:
        """Extract events from LangChain execution data with enhanced parsing"""
        events = []
        
        if hasattr(execution_data, 'get'):  # Handle callback data
            # Parse LangChain callback structure
            if 'actions' in execution_data:
                for action in execution_data['actions']:
                    event = TraceEvent(
                        event_type=EventType.TOOL_CALL_START,
                        agent_id="langchain_callback",
                        step_id=f"callback_{int(datetime.now().timestamp())}",
                        data={
                            'tool': action.get('tool', 'unknown'),
                            'tool_input': action.get('tool_input', {}),
                            'log': action.get('log', '')
                        }
                    )
                    events.append(event)
                    
        return events


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


class LlamaIndexIntegration(BaseIntegration):
    """Enhanced integration for LlamaIndex agents and query engines"""
    
    def instrument_agent(self, agent: Any, agent_id: str) -> Any:
        """Instrument LlamaIndex agent or query engine with enhanced features"""
        self.instrumented_agents[agent_id] = agent
        
        methods_instrumented = []
        
        # Enhanced LlamaIndex component detection
        if hasattr(agent, 'achat'):  # Async chat
            self._instrument_async_chat_agent(agent, agent_id)
            methods_instrumented.append('achat')
        if hasattr(agent, 'chat'):  # Chat agent
            self._instrument_chat_agent(agent, agent_id)
            methods_instrumented.append('chat')
        if hasattr(agent, 'aquery'):  # Async query
            self._instrument_async_query_engine(agent, agent_id)
            methods_instrumented.append('aquery')
        if hasattr(agent, 'query'):  # Query engine
            self._instrument_query_engine(agent, agent_id)
            methods_instrumented.append('query')
        if hasattr(agent, 'retrieve'):  # Retriever
            self._instrument_retriever(agent, agent_id)
            methods_instrumented.append('retrieve')
        if hasattr(agent, 'asynthesize'):  # Async synthesizer
            self._instrument_async_synthesizer(agent, agent_id)
            methods_instrumented.append('asynthesize')
            
        # Emit framework event
        self._emit_framework_event('llamaindex_instrumented', agent_id, {
            'methods_instrumented': methods_instrumented,
            'agent_type': type(agent).__name__
        })
            
        return agent
    
    def instrument_async_agent(self, agent: Any, agent_id: str) -> Any:
        """Instrument async LlamaIndex agent"""
        # Prioritize async methods
        if hasattr(agent, 'achat'):
            self._instrument_async_chat_agent(agent, agent_id)
        if hasattr(agent, 'aquery'):
            self._instrument_async_query_engine(agent, agent_id)
        
        # Fall back to sync instrumentation for other methods
        return self.instrument_agent(agent, agent_id)
        
    def _instrument_async_chat_agent(self, agent: Any, agent_id: str):
        """Instrument async LlamaIndex chat agent"""
        original_achat = agent.achat
        
        async def debugged_achat(message, chat_history=None, **kwargs):
            event = TraceEvent(
                event_type=EventType.REASONING_START,
                agent_id=agent_id,
                step_id=f"async_chat_{int(datetime.now().timestamp())}",
                data={
                    'message': str(message)[:200] + "..." if len(str(message)) > 200 else str(message),
                    'chat_history_length': len(chat_history) if chat_history else 0,
                    'async': True,
                    'framework': 'LlamaIndex'
                }
            )
            self.debugger.trace_events.append(event)
            
            result = await original_achat(message, chat_history, **kwargs)
            
            end_event = TraceEvent(
                event_type=EventType.REASONING_END,
                agent_id=agent_id,
                step_id=event.step_id,
                data={'response': str(result)[:200] + "..." if len(str(result)) > 200 else str(result)},
                parent_event_id=event.id
            )
            self.debugger.trace_events.append(end_event)
            
            return result
            
        agent.achat = debugged_achat
        self.original_methods['achat'] = original_achat
        
    def _instrument_chat_agent(self, agent: Any, agent_id: str):
        """Instrument LlamaIndex chat agent with enhanced features"""
        original_chat = agent.chat
        
        def debugged_chat(message, chat_history=None, **kwargs):
            event = TraceEvent(
                event_type=EventType.REASONING_START,
                agent_id=agent_id,
                step_id=f"chat_{int(datetime.now().timestamp())}",
                data={
                    'message': str(message)[:200] + "..." if len(str(message)) > 200 else str(message),
                    'chat_history_length': len(chat_history) if chat_history else 0,
                    'framework': 'LlamaIndex',
                    'agent_type': type(agent).__name__
                }
            )
            self.debugger.trace_events.append(event)
            
            start_time = datetime.now()
            result = original_chat(message, chat_history, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            
            end_event = TraceEvent(
                event_type=EventType.REASONING_END,
                agent_id=agent_id,
                step_id=event.step_id,
                data={
                    'response': str(result)[:200] + "..." if len(str(result)) > 200 else str(result),
                    'duration': duration
                },
                parent_event_id=event.id
            )
            self.debugger.trace_events.append(end_event)
            
            return result
            
        agent.chat = debugged_chat
        self.original_methods['chat'] = original_chat
        
    def _instrument_async_query_engine(self, engine: Any, agent_id: str):
        """Instrument async LlamaIndex query engine"""
        original_aquery = engine.aquery
        
        async def debugged_aquery(query_str, **kwargs):
            event = TraceEvent(
                event_type=EventType.REASONING_START,
                agent_id=agent_id,
                step_id=f"async_query_{int(datetime.now().timestamp())}",
                data={
                    'query': str(query_str)[:200] + "..." if len(str(query_str)) > 200 else str(query_str),
                    'engine_type': type(engine).__name__,
                    'async': True
                }
            )
            self.debugger.trace_events.append(event)
            
            result = await original_aquery(query_str, **kwargs)
            
            end_event = TraceEvent(
                event_type=EventType.REASONING_END,
                agent_id=agent_id,
                step_id=event.step_id,
                data={
                    'response': str(result.response)[:200] + "..." if hasattr(result, 'response') and len(str(result.response)) > 200 else str(result.response) if hasattr(result, 'response') else str(result)[:200],
                    'source_nodes': len(result.source_nodes) if hasattr(result, 'source_nodes') else 0
                },
                parent_event_id=event.id
            )
            self.debugger.trace_events.append(end_event)
            
            return result
            
        engine.aquery = debugged_aquery
        self.original_methods['aquery'] = original_aquery
        
    def _instrument_query_engine(self, engine: Any, agent_id: str):
        """Instrument LlamaIndex query engine with enhanced features"""
        original_query = engine.query
        
        def debugged_query(query_str, **kwargs):
            event = TraceEvent(
                event_type=EventType.REASONING_START,
                agent_id=agent_id,
                step_id=f"query_{int(datetime.now().timestamp())}",
                data={
                    'query': str(query_str)[:200] + "..." if len(str(query_str)) > 200 else str(query_str),
                    'engine_type': type(engine).__name__,
                    'framework': 'LlamaIndex'
                }
            )
            self.debugger.trace_events.append(event)
            
            start_time = datetime.now()
            result = original_query(query_str, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            
            end_event = TraceEvent(
                event_type=EventType.REASONING_END,
                agent_id=agent_id,
                step_id=event.step_id,
                data={
                    'response': str(result.response)[:200] + "..." if hasattr(result, 'response') and len(str(result.response)) > 200 else str(result.response) if hasattr(result, 'response') else str(result)[:200],
                    'source_nodes': len(result.source_nodes) if hasattr(result, 'source_nodes') else 0,
                    'duration': duration
                },
                parent_event_id=event.id
            )
            self.debugger.trace_events.append(end_event)
            
            return result
            
        engine.query = debugged_query
        self.original_methods['query'] = original_query
        
    def _instrument_async_synthesizer(self, synthesizer: Any, agent_id: str):
        """Instrument async synthesizer"""
        original_asynthesize = synthesizer.asynthesize
        
        async def debugged_asynthesize(query, nodes, **kwargs):
            event = TraceEvent(
                event_type=EventType.REASONING_START,
                agent_id=agent_id,
                step_id=f"async_synthesize_{int(datetime.now().timestamp())}",
                data={
                    'query': str(query)[:100] + "..." if len(str(query)) > 100 else str(query),
                    'nodes_count': len(nodes),
                    'async': True
                }
            )
            self.debugger.trace_events.append(event)
            
            result = await original_asynthesize(query, nodes, **kwargs)
            
            end_event = TraceEvent(
                event_type=EventType.REASONING_END,
                agent_id=agent_id,
                step_id=event.step_id,
                data={'result': str(result)[:200] + "..." if len(str(result)) > 200 else str(result)},
                parent_event_id=event.id
            )
            self.debugger.trace_events.append(end_event)
            
            return result
            
        synthesizer.asynthesize = debugged_asynthesize
        self.original_methods['asynthesize'] = original_asynthesize
        
    def _instrument_retriever(self, retriever: Any, agent_id: str):
        """Instrument LlamaIndex retriever with enhanced features"""
        original_retrieve = retriever.retrieve
        
        def debugged_retrieve(query_str, **kwargs):
            event = TraceEvent(
                event_type=EventType.TOOL_CALL_START,
                agent_id=agent_id,
                step_id=f"retrieve_{int(datetime.now().timestamp())}",
                data={
                    'tool_name': 'retriever',
                    'query': str(query_str)[:200] + "..." if len(str(query_str)) > 200 else str(query_str),
                    'framework': 'LlamaIndex'
                }
            )
            self.debugger.trace_events.append(event)
            
            start_time = datetime.now()
            nodes = original_retrieve(query_str, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            
            end_event = TraceEvent(
                event_type=EventType.TOOL_CALL_END,
                agent_id=agent_id,
                step_id=event.step_id,
                data={
                    'tool_name': 'retriever',
                    'retrieved_nodes': len(nodes) if nodes else 0,
                    'top_score': nodes[0].score if nodes and hasattr(nodes[0], 'score') else None,
                    'duration': duration
                },
                parent_event_id=event.id
            )
            self.debugger.trace_events.append(end_event)
            
            return nodes
            
        retriever.retrieve = debugged_retrieve
        self.original_methods['retrieve'] = original_retrieve
        
    def extract_events(self, execution_data: Any) -> List[TraceEvent]:
        """Extract events from LlamaIndex execution data"""
        return []


# Enhanced convenience classes for each integration
class LangChainDebugger(AgentDebugger):
    """Specialized debugger for LangChain agents with enhanced features"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.integration = LangChainIntegration(self)
        self.framework = "LangChain"
        
    def attach(self, agent, agent_id: Optional[str] = None):
        """Attach debugger to LangChain agent/chain with enhanced features"""
        if agent_id is None:
            agent_id = f"langchain_{len(self._attached_agents)}"
            
        self._attached_agents[agent_id] = agent
        self.agent_states[agent_id] = AgentState(agent_id)
        
        debugged_agent = self.integration.instrument_agent(agent, agent_id)
        
        print(f"🦜 LangChain debugger attached to '{agent_id}'")
        print(f"   Agent type: {type(agent).__name__}")
        print(f"   Methods instrumented: {list(self.integration.original_methods.keys())}")
        
        return debugged_agent
    
    def attach_async(self, agent, agent_id: Optional[str] = None):
        """Attach debugger to async LangChain agent"""
        if agent_id is None:
            agent_id = f"langchain_async_{len(self._attached_agents)}"
            
        self._attached_agents[agent_id] = agent
        self.agent_states[agent_id] = AgentState(agent_id)
        
        debugged_agent = self.integration.instrument_async_agent(agent, agent_id)
        
        print(f"🦜 Async LangChain debugger attached to '{agent_id}'")
        return debugged_agent
        
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get LangChain integration statistics"""
        return self.integration.get_integration_stats()


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


class LlamaIndexDebugger(AgentDebugger):
    """Specialized debugger for LlamaIndex agents and query engines with enhanced features"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.integration = LlamaIndexIntegration(self)
        self.framework = "LlamaIndex"
        
    def attach(self, agent_or_engine, agent_id: Optional[str] = None):
        """Attach debugger to LlamaIndex agent or query engine with enhanced features"""
        if agent_id is None:
            agent_id = f"llamaindex_{len(self._attached_agents)}"
            
        self._attached_agents[agent_id] = agent_or_engine
        self.agent_states[agent_id] = AgentState(agent_id)
        
        debugged_entity = self.integration.instrument_agent(agent_or_engine, agent_id)
        
        print(f"🦙 LlamaIndex debugger attached to '{agent_id}'")
        print(f"   Component type: {type(agent_or_engine).__name__}")
        print(f"   Methods instrumented: {list(self.integration.original_methods.keys())}")
        
        return debugged_entity
    
    def attach_async(self, agent_or_engine, agent_id: Optional[str] = None):
        """Attach debugger to async LlamaIndex agent"""
        if agent_id is None:
            agent_id = f"llamaindex_async_{len(self._attached_agents)}"
            
        self._attached_agents[agent_id] = agent_or_engine
        self.agent_states[agent_id] = AgentState(agent_id)
        
        debugged_entity = self.integration.instrument_async_agent(agent_or_engine, agent_id)
        
        print(f"🦙 Async LlamaIndex debugger attached to '{agent_id}'")
        return debugged_entity
        
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get LlamaIndex integration statistics"""
        return self.integration.get_integration_stats()


# New: Hugging Face (Transformers) integration
class HuggingFaceIntegration(BaseIntegration):
    """Integration for Hugging Face transformers Pipelines and Models"""

    def instrument_agent(self, agent: Any, agent_id: str) -> Any:
        self.instrumented_agents[agent_id] = agent

        # Pipelines expose __call__; special method lookup bypasses instance attributes,
        # so wrap with a proxy that defines __call__ on its own class.
        proxy = None
        if hasattr(agent, '__call__'):
            underlying = agent

            class _PipelineProxy:
                def __init__(self, underlying_ref):
                    self._underlying = underlying_ref

                def __call__(self, *args, **kwargs):
                    event = TraceEvent(
                        event_type=EventType.LLM_CALL_START,
                        agent_id=agent_id,
                        step_id=f"hf_call_{int(datetime.now().timestamp())}",
                        data={
                            'args_preview': str(args)[:200],
                            'kwargs_keys': list(kwargs.keys()),
                            'component': type(self._underlying).__name__,
                            'framework': 'Transformers'
                        }
                    )
                    self_ref = self  # capture for readability
                    self_ref_debugger = self_ref_debugger_outer
                    self_ref_debugger._emit_event(event)
                    if self_ref_debugger._should_break(event):
                        self_ref_debugger._trigger_breakpoint(event, agent_id)

                    try:
                        start_time = datetime.now()
                        result = self._underlying.__call__(*args, **kwargs)
                        duration = (datetime.now() - start_time).total_seconds()
                        end_event = TraceEvent(
                            event_type=EventType.LLM_CALL_END,
                            agent_id=agent_id,
                            step_id=event.step_id,
                            data={
                                'result_preview': str(result)[:300],
                                'duration': duration
                            },
                            parent_event_id=event.id,
                            duration=duration
                        )
                        self_ref_debugger._emit_event(end_event)
                        if self_ref_debugger._should_break(end_event):
                            self_ref_debugger._trigger_breakpoint(end_event, agent_id)
                        return result
                    except Exception as e:
                        error_event = TraceEvent(
                            event_type=EventType.ERROR,
                            agent_id=agent_id,
                            step_id=event.step_id,
                            data={'error': str(e), 'error_type': type(e).__name__},
                            parent_event_id=event.id
                        )
                        self_ref_debugger._emit_event(error_event)
                        if self_ref_debugger._should_break(error_event):
                            self_ref_debugger._trigger_breakpoint(error_event, agent_id)
                        raise

                def __getattr__(self, name):
                    return getattr(self._underlying, name)

            # Provide debugger to proxy without closing over self in class body
            self_ref_debugger_outer = self.debugger
            proxy = _PipelineProxy(underlying)
            self.instrumented_agents[agent_id] = proxy
            agent = proxy

        if hasattr(agent, 'generate'):
            original_generate = agent.generate

            def debugged_generate(*args, **kwargs):
                event = TraceEvent(
                    event_type=EventType.LLM_CALL_START,
                    agent_id=agent_id,
                    step_id=f"hf_generate_{int(datetime.now().timestamp())}",
                    data={'kwargs_keys': list(kwargs.keys()), 'framework': 'Transformers'}
                )
                self.debugger._emit_event(event)
                if self.debugger._should_break(event):
                    self.debugger._trigger_breakpoint(event, agent_id)
                start_time = datetime.now()
                outputs = original_generate(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                end_event = TraceEvent(
                    event_type=EventType.LLM_CALL_END,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={'duration': duration},
                    parent_event_id=event.id,
                    duration=duration
                )
                self.debugger._emit_event(end_event)
                if self.debugger._should_break(end_event):
                    self.debugger._trigger_breakpoint(end_event, agent_id)
                return outputs

            agent.generate = debugged_generate
            self.original_methods['generate'] = original_generate

        # Emit framework detection event
        self._emit_framework_event('huggingface_instrumented', agent_id, {
            'component_type': type(agent).__name__,
            'methods_instrumented': list(self.original_methods.keys())
        })

        return agent if proxy is None else proxy

    def extract_events(self, execution_data: Any) -> List[TraceEvent]:
        return []


class HuggingFaceDebugger(AgentDebugger):
    """Debugger wrapper for Hugging Face transformers components"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.integration = HuggingFaceIntegration(self)
        self.framework = "Transformers"

    def attach(self, component, agent_id: Optional[str] = None):
        if agent_id is None:
            agent_id = f"hf_{len(self._attached_agents)}"
        self._attached_agents[agent_id] = component
        self.agent_states[agent_id] = AgentState(agent_id)
        debugged_component = self.integration.instrument_agent(component, agent_id)
        print(f"🤗 Hugging Face debugger attached to '{agent_id}'")
        print(f"   Methods instrumented: {list(self.integration.original_methods.keys())}")
        return debugged_component

    def get_integration_stats(self) -> Dict[str, Any]:
        return self.integration.get_integration_stats()

# Enhanced universal integration detector
def auto_detect_framework(agent: Any) -> Optional[str]:
    """Automatically detect which framework an agent belongs to with enhanced detection"""
    module = inspect.getmodule(agent)
    if module:
        module_name = module.__name__
        
        if 'langchain' in module_name:
            return 'langchain'
        elif 'crewai' in module_name:
            return 'crewai'
        elif 'autogpt' in module_name or 'auto_gpt' in module_name:
            return 'autogpt'
        elif 'llama_index' in module_name or 'llamaindex' in module_name:
            return 'llamaindex'
        elif 'openai' in module_name and hasattr(agent, 'chat'):
            return 'openai'
        elif 'transformers' in module_name:
            return 'transformers'
    
    # Enhanced framework-specific attributes detection
    agent_class_name = agent.__class__.__name__.lower()
    
    # LangChain detection
    if (hasattr(agent, 'invoke') and hasattr(agent, 'ainvoke')) or 'chain' in agent_class_name:
        return 'langchain'
    # CrewAI detection
    elif (hasattr(agent, 'role') and hasattr(agent, 'goal')) or 'crew' in agent_class_name:
        return 'crewai'
    # AutoGPT detection
    elif (hasattr(agent, 'ai_name') and hasattr(agent, 'execute_command')) or 'autogpt' in agent_class_name:
        return 'autogpt'
    # LlamaIndex detection
    elif (hasattr(agent, 'query') and hasattr(agent, 'retrieve')) or 'index' in agent_class_name:
        return 'llamaindex'
    # OpenAI detection
    elif hasattr(agent, 'chat') and hasattr(agent, 'model'):
        return 'openai'
    # Transformers pipelines/models detection by common callables
    elif hasattr(agent, '__call__') or hasattr(agent, 'generate'):
        mod = inspect.getmodule(agent.__class__)
        if mod and 'transformers' in mod.__name__:
            return 'transformers'
    
    return None


def smart_debug(agent: Any, mode: str = "console", **kwargs) -> Any:
    """Automatically detect framework and attach appropriate debugger with enhanced features"""
    framework = auto_detect_framework(agent)
    
    debugger_map = {
        'langchain': LangChainDebugger,
        'crewai': CrewAIDebugger,
        'autogpt': AutoGPTDebugger,
        'llamaindex': LlamaIndexDebugger,
        'transformers': HuggingFaceDebugger,
    }
    
    if framework in debugger_map:
        debugger = debugger_map[framework](mode=mode, **kwargs)
        print(f"🔍 Detected framework: {framework}")
    else:
        print(f"⚠️ Framework not detected, using generic debugger")
        debugger = AgentDebugger(mode=mode, **kwargs)
    
    return debugger.attach(agent)


# Enhanced testing utilities for integrations
# Removed IntegrationTester utility class to streamline package


# Enhanced MultiAgentOrchestrator with framework awareness
class MultiAgentOrchestrator:
    """Enhanced orchestrator for coordinating multiple agents with shared debugging and framework awareness"""

    def __init__(self, debugger: AgentDebugger):
        self.debugger = debugger
        self.agents: Dict[str, Any] = {}
        self.agent_frameworks: Dict[str, str] = {}
        self.message_history: List[Dict[str, Any]] = []

    def register(self, agent_id: str, agent: Any, framework: Optional[str] = None):
        """Register an agent with optional framework specification"""
        self.agents[agent_id] = agent
        if framework:
            self.agent_frameworks[agent_id] = framework
        else:
            self.agent_frameworks[agent_id] = auto_detect_framework(agent) or "unknown"
        
        # Auto-attach debugger if not already attached
        if agent_id not in self.debugger.agent_states:
            self.debugger.attach(agent, agent_id)

    def send(self, sender_id: str, receiver_id: str, content: str, message_type: str = "task") -> Any:
        """Send message between agents with enhanced tracking"""
        # Enhanced inter-agent message event
        event = TraceEvent(
            event_type=EventType.INTER_AGENT_MESSAGE,
            agent_id=sender_id,
            step_id=f"msg_{int(datetime.now().timestamp())}",
            data={
                'from': sender_id,
                'to': receiver_id,
                'content_preview': content[:200] + "..." if len(content) > 200 else content,
                'message_type': message_type,
                'sender_framework': self.agent_frameworks.get(sender_id, 'unknown'),
                'receiver_framework': self.agent_frameworks.get(receiver_id, 'unknown')
            }
        )
        
        # Record message in history
        self.message_history.append({
            'timestamp': datetime.now(),
            'from': sender_id,
            'to': receiver_id,
            'content': content,
            'type': message_type
        })
        
        # Use debugger internal emitter when available; otherwise append
        if hasattr(self.debugger, '_emit_event'):
            self.debugger._emit_event(event)
        else:
            self.debugger.trace_events.append(event)

        # Optional break on inter-agent messages via conditional breakpoint
        if self.debugger._should_break(event):
            self.debugger._trigger_breakpoint(event, sender_id)

        receiver = self.agents.get(receiver_id)
        if receiver is None:
            raise ValueError(f"Receiver '{receiver_id}' not registered")

        # Framework-aware invocation
        try:
            receiver_framework = self.agent_frameworks.get(receiver_id, 'unknown')
            
            if receiver_framework == 'langchain':
                if hasattr(receiver, 'invoke'):
                    return receiver.invoke({'input': content})
                elif hasattr(receiver, 'run'):
                    return receiver.run(content)
                    
            elif receiver_framework == 'crewai':
                if hasattr(receiver, 'execute_task'):
                    # Create a simple task object
                    task = type('Task', (), {'description': content})()
                    return receiver.execute_task(task)
                    
            elif receiver_framework == 'autogpt':
                if hasattr(receiver, 'execute_command'):
                    return receiver.execute_command('process_message', {'content': content})
                    
            elif receiver_framework == 'llamaindex':
                if hasattr(receiver, 'query'):
                    return receiver.query(content)
                elif hasattr(receiver, 'chat'):
                    return receiver.chat(content)
            
            # Fallback to common methods
            if hasattr(receiver, 'invoke'):
                return receiver.invoke({'input': content})
            if hasattr(receiver, 'run'):
                return receiver.run(content)
            if hasattr(receiver, '__call__'):
                return receiver(content)
                
            raise TypeError(f"Receiver {receiver_id} does not support standard invocation methods")
            
        except Exception as e:
            error_event = TraceEvent(
                event_type=EventType.ERROR,
                agent_id=sender_id,
                step_id=event.step_id,
                data={
                    'error': f"Message delivery failed: {str(e)}",
                    'operation': 'inter_agent_communication'
                }
            )
            self.debugger.trace_events.append(error_event)
            raise

    def broadcast(self, sender_id: str, content: str, message_type: str = "broadcast") -> Dict[str, Any]:
        """Broadcast message to all agents"""
        results = {}
        for receiver_id in self.agents:
            if receiver_id != sender_id:
                try:
                    result = self.send(sender_id, receiver_id, content, message_type)
                    results[receiver_id] = result
                except Exception as e:
                    results[receiver_id] = f"Error: {e}"
        return results

    def get_communication_graph(self) -> Dict[str, Any]:
        """Get communication graph data for visualization"""
        nodes = [{'id': agent_id, 'framework': framework} 
                for agent_id, framework in self.agent_frameworks.items()]
        
        edges = []
        for message in self.message_history:
            edges.append({
                'source': message['from'],
                'target': message['to'],
                'type': message['type'],
                'timestamp': message['timestamp'].isoformat()
            })
            
        return {'nodes': nodes, 'edges': edges}


