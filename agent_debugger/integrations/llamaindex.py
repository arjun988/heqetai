"""
LlamaIndex integration for AgentDebugger.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..debugger import AgentDebugger
from ..events import EventType, TraceEvent
from ..state import AgentState
from .base import BaseIntegration


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
