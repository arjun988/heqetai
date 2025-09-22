"""
AgentDebugger Framework Integrations
===================================

Integration adapters for popular AI agent frameworks including
LangChain, CrewAI, AutoGPT, and LlamaIndex.

These adapters provide seamless debugging capabilities by automatically
instrumenting framework-specific methods and converting framework events
into AgentDebugger trace events.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
import inspect
import functools
from datetime import datetime

from main import AgentDebugger, TraceEvent, EventType, AgentState


class BaseIntegration(ABC):
    """Base class for framework integrations"""
    
    def __init__(self, debugger: AgentDebugger):
        self.debugger = debugger
        self.original_methods: Dict[str, Any] = {}
        
    @abstractmethod
    def instrument_agent(self, agent: Any, agent_id: str) -> Any:
        """Instrument an agent with debugging capabilities"""
        pass
        
    @abstractmethod
    def extract_events(self, execution_data: Any) -> List[TraceEvent]:
        """Extract trace events from framework execution data"""
        pass
        
    def restore_agent(self, agent: Any):
        """Restore agent to original state (remove instrumentation)"""
        for method_name, original_method in self.original_methods.items():
            setattr(agent, method_name, original_method)
        self.original_methods.clear()


class LangChainIntegration(BaseIntegration):
    """Integration for LangChain agents and chains"""
    
    def instrument_agent(self, agent: Any, agent_id: str) -> Any:
        """Instrument LangChain agent/chain"""
        # Handle different LangChain components
        if hasattr(agent, 'invoke'):  # New LangChain LCEL syntax
            return self._instrument_runnable(agent, agent_id)
        elif hasattr(agent, 'run'):  # Legacy Agent interface
            self._instrument_legacy_agent(agent, agent_id)
        elif hasattr(agent, '__call__'):  # Chain interface
            self._instrument_chain(agent, agent_id)
            
        return agent
        
    def _instrument_runnable(self, runnable: Any, agent_id: str):
        """Instrument LangChain Runnable (LCEL)"""
        original_invoke = runnable.invoke

        def debugged_invoke(input_data, config=None, **kwargs):
            # Emit BEFORE_REASONING style event through standard REASONING_START
            event = TraceEvent(
                event_type=EventType.REASONING_START,
                agent_id=agent_id,
                step_id=f"invoke_{int(datetime.now().timestamp())}",
                data={
                    'input': str(input_data)[:200] + "..." if len(str(input_data)) > 200 else str(input_data),
                    'runnable_type': type(runnable).__name__,
                    'config': config
                }
            )
            self.debugger.trace_events.append(event)

            if self.debugger._should_break(event):
                self.debugger._trigger_breakpoint(event, agent_id)

            try:
                result = original_invoke(input_data, config, **kwargs)
                end_event = TraceEvent(
                    event_type=EventType.REASONING_END,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={
                        'output': str(result)[:200] + "..." if len(str(result)) > 200 else str(result),
                        'success': True
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
                        'error_type': type(e).__name__
                    },
                    parent_event_id=event.id
                )
                self.debugger.trace_events.append(error_event)
                # Break on error if configured
                if self.debugger._should_break(error_event):
                    self.debugger._trigger_breakpoint(error_event, agent_id)
                raise

        # Many LCEL runnables (e.g., RunnableSequence) are Pydantic models and cannot have attributes reassigned.
        # Return a lightweight proxy that overrides invoke while delegating everything else.
        class _RunnableProxy:
            def __init__(self, underlying):
                self._underlying = underlying

            def invoke(self, input_data, config=None, **kwargs):
                return debugged_invoke(input_data, config, **kwargs)

            def __getattr__(self, name):
                return getattr(self._underlying, name)

        self.original_methods['invoke'] = original_invoke
        return _RunnableProxy(runnable)
        
    def _instrument_legacy_agent(self, agent: Any, agent_id: str):
        """Instrument legacy LangChain Agent"""
        if hasattr(agent, 'run'):
            original_run = agent.run
            
            def debugged_run(input_text, **kwargs):
                event = TraceEvent(
                    event_type=EventType.REASONING_START,
                    agent_id=agent_id,
                    step_id=f"agent_run_{int(datetime.now().timestamp())}",
                    data={'input': input_text, 'kwargs': kwargs}
                )
                self.debugger.trace_events.append(event)
                
                result = original_run(input_text, **kwargs)
                
                end_event = TraceEvent(
                    event_type=EventType.REASONING_END,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={'output': result},
                    parent_event_id=event.id
                )
                self.debugger.trace_events.append(end_event)
                
                return result
                
            agent.run = debugged_run
            self.original_methods['run'] = original_run
            
        # Instrument tool usage if available
        if hasattr(agent, 'tools'):
            self._instrument_tools(agent.tools, agent_id)
            
    def _instrument_tools(self, tools: List[Any], agent_id: str):
        """Instrument LangChain tools"""
        for tool in tools:
            if hasattr(tool, '_run'):
                original_run = tool._run
                tool_name = getattr(tool, 'name', type(tool).__name__)
                
                def debugged_tool_run(query, **kwargs):
                    event = TraceEvent(
                        event_type=EventType.TOOL_CALL_START,
                        agent_id=agent_id,
                        step_id=f"tool_{int(datetime.now().timestamp())}",
                        data={
                            'tool_name': tool_name,
                            'query': query,
                            'kwargs': kwargs
                        }
                    )
                    self.debugger.trace_events.append(event)
                    
                    # Check for mocked output
                    mock_output = self.debugger.mock_registry.get_tool_mock(tool_name)
                    if mock_output is not None:
                        return mock_output
                        
                    result = original_run(query, **kwargs)
                    
                    end_event = TraceEvent(
                        event_type=EventType.TOOL_CALL_END,
                        agent_id=agent_id,
                        step_id=event.step_id,
                        data={
                            'tool_name': tool_name,
                            'result': str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                        },
                        parent_event_id=event.id
                    )
                    self.debugger.trace_events.append(end_event)
                    
                    return result
                    
                tool._run = debugged_tool_run
                self.original_methods[f'{tool_name}_run'] = original_run
                
    def extract_events(self, execution_data: Any) -> List[TraceEvent]:
        """Extract events from LangChain execution data"""
        # This would parse LangChain's callback data if available
        return []


class CrewAIIntegration(BaseIntegration):
    """Integration for CrewAI agents and crews"""
    
    def instrument_agent(self, crew_or_agent: Any, agent_id: str) -> Any:
        """Instrument CrewAI Crew or Agent"""
        if hasattr(crew_or_agent, 'kickoff'):  # It's a Crew
            self._instrument_crew(crew_or_agent, agent_id)
        elif hasattr(crew_or_agent, 'execute'):  # It's an Agent
            self._instrument_crewai_agent(crew_or_agent, agent_id)
            
        return crew_or_agent
        
    def _instrument_crew(self, crew: Any, crew_id: str):
        """Instrument CrewAI Crew"""
        original_kickoff = crew.kickoff
        
        def debugged_kickoff(*args, **kwargs):
            event = TraceEvent(
                event_type=EventType.REASONING_START,
                agent_id=crew_id,
                step_id=f"crew_kickoff_{int(datetime.now().timestamp())}",
                data={
                    'crew_agents': [agent.role for agent in crew.agents] if hasattr(crew, 'agents') else [],
                    'tasks_count': len(crew.tasks) if hasattr(crew, 'tasks') else 0
                }
            )
            self.debugger.trace_events.append(event)
            
            # Instrument individual agents in the crew
            if hasattr(crew, 'agents'):
                for i, agent in enumerate(crew.agents):
                    self._instrument_crewai_agent(agent, f"{crew_id}_agent_{i}")
            
            result = original_kickoff(*args, **kwargs)
            
            end_event = TraceEvent(
                event_type=EventType.REASONING_END,
                agent_id=crew_id,
                step_id=event.step_id,
                data={'result': str(result)[:300] + "..." if len(str(result)) > 300 else str(result)},
                parent_event_id=event.id
            )
            self.debugger.trace_events.append(end_event)
            
            return result
            
        crew.kickoff = debugged_kickoff
        self.original_methods['kickoff'] = original_kickoff
        
    def _instrument_crewai_agent(self, agent: Any, agent_id: str):
        """Instrument individual CrewAI Agent"""
        if hasattr(agent, 'execute_task'):
            original_execute = agent.execute_task
            
            def debugged_execute_task(task, *args, **kwargs):
                event = TraceEvent(
                    event_type=EventType.REASONING_START,
                    agent_id=agent_id,
                    step_id=f"task_execute_{int(datetime.now().timestamp())}",
                    data={
                        'agent_role': getattr(agent, 'role', 'Unknown'),
                        'task': str(task)[:200] + "..." if len(str(task)) > 200 else str(task),
                        'agent_goal': getattr(agent, 'goal', '')
                    }
                )
                self.debugger.trace_events.append(event)
                
                result = original_execute(task, *args, **kwargs)
                
                end_event = TraceEvent(
                    event_type=EventType.REASONING_END,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={'task_result': str(result)[:200] + "..." if len(str(result)) > 200 else str(result)},
                    parent_event_id=event.id
                )
                self.debugger.trace_events.append(end_event)
                
                return result
                
            agent.execute_task = debugged_execute_task
            self.original_methods[f'{agent_id}_execute_task'] = original_execute
            
        # Instrument tools if available
        if hasattr(agent, 'tools') and agent.tools:
            for tool in agent.tools:
                self._instrument_crewai_tool(tool, agent_id)
                
    def _instrument_crewai_tool(self, tool: Any, agent_id: str):
        """Instrument CrewAI tools"""
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
                        'kwargs': kwargs
                    }
                )
                self.debugger.trace_events.append(event)
                
                # Check for mocked output
                mock_output = self.debugger.mock_registry.get_tool_mock(tool_name)
                if mock_output is not None:
                    return mock_output
                    
                result = original_run(*args, **kwargs)
                
                end_event = TraceEvent(
                    event_type=EventType.TOOL_CALL_END,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={'tool_name': tool_name, 'result': str(result)[:200] + "..." if len(str(result)) > 200 else str(result)},
                    parent_event_id=event.id
                )
                self.debugger.trace_events.append(end_event)
                
                return result
                
            tool.run = debugged_tool_run
            self.original_methods[f'{tool_name}_run'] = original_run
            
    def extract_events(self, execution_data: Any) -> List[TraceEvent]:
        """Extract events from CrewAI execution data"""
        return []


class AutoGPTIntegration(BaseIntegration):
    """Integration for AutoGPT agents"""
    
    def instrument_agent(self, agent: Any, agent_id: str) -> Any:
        """Instrument AutoGPT agent"""
        if hasattr(agent, 'start_interaction_loop'):
            self._instrument_interaction_loop(agent, agent_id)
        if hasattr(agent, 'execute_command'):
            self._instrument_command_execution(agent, agent_id)
            
        return agent
        
    def _instrument_interaction_loop(self, agent: Any, agent_id: str):
        """Instrument AutoGPT interaction loop"""
        original_loop = agent.start_interaction_loop
        
        def debugged_interaction_loop(*args, **kwargs):
            event = TraceEvent(
                event_type=EventType.REASONING_START,
                agent_id=agent_id,
                step_id=f"interaction_loop_{int(datetime.now().timestamp())}",
                data={'agent_name': getattr(agent, 'ai_name', 'AutoGPT')}
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
        """Instrument AutoGPT command execution"""
        original_execute = agent.execute_command
        
        def debugged_execute_command(command_name, arguments, *args, **kwargs):
            event = TraceEvent(
                event_type=EventType.TOOL_CALL_START,
                agent_id=agent_id,
                step_id=f"command_{int(datetime.now().timestamp())}",
                data={
                    'command_name': command_name,
                    'arguments': arguments
                }
            )
            self.debugger.trace_events.append(event)
            
            # Check for mocked output
            mock_output = self.debugger.mock_registry.get_tool_mock(command_name)
            if mock_output is not None:
                return mock_output
                
            result = original_execute(command_name, arguments, *args, **kwargs)
            
            end_event = TraceEvent(
                event_type=EventType.TOOL_CALL_END,
                agent_id=agent_id,
                step_id=event.step_id,
                data={
                    'command_name': command_name,
                    'result': str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                },
                parent_event_id=event.id
            )
            self.debugger.trace_events.append(end_event)
            
            return result
            
        agent.execute_command = debugged_execute_command
        self.original_methods['execute_command'] = original_execute
        
    def extract_events(self, execution_data: Any) -> List[TraceEvent]:
        """Extract events from AutoGPT execution data"""
        return []


class LlamaIndexIntegration(BaseIntegration):
    """Integration for LlamaIndex agents and query engines"""
    
    def instrument_agent(self, agent: Any, agent_id: str) -> Any:
        """Instrument LlamaIndex agent or query engine"""
        if hasattr(agent, 'chat'):  # Chat agent
            self._instrument_chat_agent(agent, agent_id)
        elif hasattr(agent, 'query'):  # Query engine
            self._instrument_query_engine(agent, agent_id)
        elif hasattr(agent, 'retrieve'):  # Retriever
            self._instrument_retriever(agent, agent_id)
            
        return agent
        
    def _instrument_chat_agent(self, agent: Any, agent_id: str):
        """Instrument LlamaIndex chat agent"""
        original_chat = agent.chat
        
        def debugged_chat(message, chat_history=None, **kwargs):
            event = TraceEvent(
                event_type=EventType.REASONING_START,
                agent_id=agent_id,
                step_id=f"chat_{int(datetime.now().timestamp())}",
                data={
                    'message': str(message)[:200] + "..." if len(str(message)) > 200 else str(message),
                    'chat_history_length': len(chat_history) if chat_history else 0
                }
            )
            self.debugger.trace_events.append(event)
            
            result = original_chat(message, chat_history, **kwargs)
            
            end_event = TraceEvent(
                event_type=EventType.REASONING_END,
                agent_id=agent_id,
                step_id=event.step_id,
                data={'response': str(result)[:200] + "..." if len(str(result)) > 200 else str(result)},
                parent_event_id=event.id
            )
            self.debugger.trace_events.append(end_event)
            
            return result
            
        agent.chat = debugged_chat
        self.original_methods['chat'] = original_chat
        
    def _instrument_query_engine(self, engine: Any, agent_id: str):
        """Instrument LlamaIndex query engine"""
        original_query = engine.query
        
        def debugged_query(query_str, **kwargs):
            event = TraceEvent(
                event_type=EventType.REASONING_START,
                agent_id=agent_id,
                step_id=f"query_{int(datetime.now().timestamp())}",
                data={
                    'query': str(query_str)[:200] + "..." if len(str(query_str)) > 200 else str(query_str),
                    'engine_type': type(engine).__name__
                }
            )
            self.debugger.trace_events.append(event)
            
            result = original_query(query_str, **kwargs)
            
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
            
        engine.query = debugged_query
        self.original_methods['query'] = original_query
        
    def _instrument_retriever(self, retriever: Any, agent_id: str):
        """Instrument LlamaIndex retriever"""
        original_retrieve = retriever.retrieve
        
        def debugged_retrieve(query_str, **kwargs):
            event = TraceEvent(
                event_type=EventType.TOOL_CALL_START,
                agent_id=agent_id,
                step_id=f"retrieve_{int(datetime.now().timestamp())}",
                data={
                    'tool_name': 'retriever',
                    'query': str(query_str)[:200] + "..." if len(str(query_str)) > 200 else str(query_str)
                }
            )
            self.debugger.trace_events.append(event)
            
            nodes = original_retrieve(query_str, **kwargs)
            
            end_event = TraceEvent(
                event_type=EventType.TOOL_CALL_END,
                agent_id=agent_id,
                step_id=event.step_id,
                data={
                    'tool_name': 'retriever',
                    'retrieved_nodes': len(nodes) if nodes else 0,
                    'top_score': nodes[0].score if nodes and hasattr(nodes[0], 'score') else None
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


# Convenience classes for each integration
class LangChainDebugger(AgentDebugger):
    """Specialized debugger for LangChain agents"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.integration = LangChainIntegration(self)
        
    def attach(self, agent, agent_id: Optional[str] = None):
        """Attach debugger to LangChain agent/chain"""
        if agent_id is None:
            agent_id = f"langchain_{len(self._attached_agents)}"
            
        self._attached_agents[agent_id] = agent
        self.agent_states[agent_id] = AgentState(agent_id)
        
        debugged_agent = self.integration.instrument_agent(agent, agent_id)
        
        print(f"🦜 LangChain debugger attached to '{agent_id}'")
        return debugged_agent


class CrewAIDebugger(AgentDebugger):
    """Specialized debugger for CrewAI agents and crews"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.integration = CrewAIIntegration(self)
        
    def attach(self, crew_or_agent, agent_id: Optional[str] = None):
        """Attach debugger to CrewAI crew or agent"""
        if agent_id is None:
            agent_id = f"crewai_{len(self._attached_agents)}"
            
        self._attached_agents[agent_id] = crew_or_agent
        self.agent_states[agent_id] = AgentState(agent_id)
        
        debugged_entity = self.integration.instrument_agent(crew_or_agent, agent_id)
        
        print(f"🚢 CrewAI debugger attached to '{agent_id}'")
        return debugged_entity


class AutoGPTDebugger(AgentDebugger):
    """Specialized debugger for AutoGPT agents"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.integration = AutoGPTIntegration(self)
        
    def attach(self, agent, agent_id: Optional[str] = None):
        """Attach debugger to AutoGPT agent"""
        if agent_id is None:
            agent_id = f"autogpt_{len(self._attached_agents)}"
            
        self._attached_agents[agent_id] = agent
        self.agent_states[agent_id] = AgentState(agent_id)
        
        debugged_agent = self.integration.instrument_agent(agent, agent_id)
        
        print(f"🤖 AutoGPT debugger attached to '{agent_id}'")
        return debugged_agent


class LlamaIndexDebugger(AgentDebugger):
    """Specialized debugger for LlamaIndex agents and query engines"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.integration = LlamaIndexIntegration(self)
        
    def attach(self, agent_or_engine, agent_id: Optional[str] = None):
        """Attach debugger to LlamaIndex agent or query engine"""
        if agent_id is None:
            agent_id = f"llamaindex_{len(self._attached_agents)}"
            
        self._attached_agents[agent_id] = agent_or_engine
        self.agent_states[agent_id] = AgentState(agent_id)
        
        debugged_entity = self.integration.instrument_agent(agent_or_engine, agent_id)
        
        print(f"🦙 LlamaIndex debugger attached to '{agent_id}'")
        return debugged_entity


# Universal integration detector
def auto_detect_framework(agent: Any) -> Optional[str]:
    """Automatically detect which framework an agent belongs to"""
    module = inspect.getmodule(agent)
    if module:
        module_name = module.__name__
        
        if 'langchain' in module_name:
            return 'langchain'
        elif 'crewai' in module_name:
            return 'crewai'
        elif 'autogpt' in module_name:
            return 'autogpt'
        elif 'llama_index' in module_name or 'llamaindex' in module_name:
            return 'llamaindex'
    
    # Check for framework-specific attributes
    if hasattr(agent, 'invoke') and hasattr(agent, 'ainvoke'):  # LangChain LCEL
        return 'langchain'
    elif hasattr(agent, 'role') and hasattr(agent, 'goal'):  # CrewAI Agent
        return 'crewai'
    elif hasattr(agent, 'ai_name') and hasattr(agent, 'execute_command'):  # AutoGPT
        return 'autogpt'
    elif hasattr(agent, 'query') and hasattr(agent, 'retrieve'):  # LlamaIndex
        return 'llamaindex'
    
    return None


def smart_debug(agent: Any, mode: str = "console", **kwargs) -> Any:
    """Automatically detect framework and attach appropriate debugger"""
    framework = auto_detect_framework(agent)
    
    if framework == 'langchain':
        debugger = LangChainDebugger(mode=mode, **kwargs)
    elif framework == 'crewai':
        debugger = CrewAIDebugger(mode=mode, **kwargs)
    elif framework == 'autogpt':
        debugger = AutoGPTDebugger(mode=mode, **kwargs)
    elif framework == 'llamaindex':
        debugger = LlamaIndexDebugger(mode=mode, **kwargs)
    else:
        print(f"⚠️ Framework not detected, using generic debugger")
        debugger = AgentDebugger(mode=mode, **kwargs)
    
    return debugger.attach(agent)


# Testing utilities for integrations
class IntegrationTester:
    """Test suite for framework integrations"""
    
    def __init__(self, integration: BaseIntegration):
        self.integration = integration
        
    def test_instrumentation(self, agent: Any, test_methods: List[str]) -> Dict[str, bool]:
        """Test that all expected methods are properly instrumented"""
        results = {}
        
        for method_name in test_methods:
            original_exists = hasattr(agent, method_name)
            if original_exists:
                original_method = getattr(agent, method_name)
                
                # Check if method was wrapped (has different id)
                is_wrapped = (
                    method_name in self.integration.original_methods or
                    hasattr(original_method, '__wrapped__') or
                    original_method.__name__ != method_name
                )
                results[method_name] = is_wrapped
            else:
                results[method_name] = False
                
        return results
        
    def test_event_generation(self, agent: Any, test_inputs: List[Any]) -> List[TraceEvent]:
        """Test that events are properly generated during execution"""
        initial_event_count = len(self.integration.debugger.trace_events)
        
        # Run test inputs through the agent
        for test_input in test_inputs:
            try:
                if hasattr(agent, 'run'):
                    agent.run(test_input)
                elif hasattr(agent, 'invoke'):
                    agent.invoke(test_input)
                elif hasattr(agent, 'query'):
                    agent.query(test_input)
                elif hasattr(agent, 'chat'):
                    agent.chat(test_input)
            except Exception as e:
                print(f"Test input failed: {e}")
                
        # Return new events generated
        new_events = self.integration.debugger.trace_events[initial_event_count:]
        return new_events
        
    def run_integration_test(self, agent: Any, agent_id: str = "test_agent") -> Dict[str, Any]:
        """Run complete integration test suite"""
        # Instrument the agent
        instrumented_agent = self.integration.instrument_agent(agent, agent_id)
        
        # Test method instrumentation
        expected_methods = ['run', 'invoke', 'query', 'chat', 'execute_task', 'kickoff']
        instrumentation_results = self.test_instrumentation(
            instrumented_agent, 
            expected_methods
        )
        
        # Test event generation
        test_inputs = ["test query", "another test", "final test"]
        generated_events = self.test_event_generation(instrumented_agent, test_inputs)
        
        # Restore agent
        self.integration.restore_agent(instrumented_agent)
        
        return {
            'instrumentation_success': any(instrumentation_results.values()),
            'instrumented_methods': [k for k, v in instrumentation_results.items() if v],
            'events_generated': len(generated_events),
            'event_types': [e.event_type.value for e in generated_events],
            'test_passed': len(generated_events) > 0
        }


class MultiAgentOrchestrator:
    """Simple orchestrator for coordinating multiple agents with shared debugging.

    - Broadcasts messages between agents
    - Emits INTER_AGENT_MESSAGE events
    - Supports global breakpoints via the same debugger
    """

    def __init__(self, debugger: AgentDebugger):
        self.debugger = debugger
        self.agents: Dict[str, Any] = {}

    def register(self, agent_id: str, agent: Any):
        self.agents[agent_id] = agent

    def send(self, sender_id: str, receiver_id: str, content: str) -> Any:
        # Emit inter-agent message event
        event = TraceEvent(
            event_type=EventType.INTER_AGENT_MESSAGE,
            agent_id=sender_id,
            step_id=f"msg_{int(datetime.now().timestamp())}",
            data={
                'from': sender_id,
                'to': receiver_id,
                'content_preview': content[:200] + "..." if len(content) > 200 else content
            }
        )
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

        # Try common invocation methods
        if hasattr(receiver, 'invoke'):
            return receiver.invoke({'input': content})
        if hasattr(receiver, 'run'):
            return receiver.run(content)
        if hasattr(receiver, '__call__'):
            return receiver(content)
        raise TypeError("Receiver does not support invoke/run/call")


# Example usage and testing
if __name__ == "__main__":
    pass