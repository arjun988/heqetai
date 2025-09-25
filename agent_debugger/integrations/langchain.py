"""
LangChain integration for AgentDebugger.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..debugger import AgentDebugger
from ..events import EventType, TraceEvent
from ..state import AgentState
from .base import BaseIntegration


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
