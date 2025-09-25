"""
Core AgentDebugger class and instrumentation wrappers.
"""

import json
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .console import DebugConsole
from .events import Breakpoint, EventType, TraceEvent
from .mocks import MockRegistry
from .performance import PerformanceMonitor
from .state import AgentState


class AgentDebugger:
    """Main debugger class that wraps and monitors agent execution"""

    def __init__(self, mode: str = "console", enable_replay: bool = True,
                 enable_performance_monitoring: bool = True):
        self.mode = mode
        self.enable_replay = enable_replay
        self.enable_performance_monitoring = enable_performance_monitoring
        self.trace_events: List[TraceEvent] = []
        self.breakpoints: List[Breakpoint] = []
        self.agent_states: Dict[str, AgentState] = {}
        self.mock_registry = MockRegistry()
        self.performance_monitor = PerformanceMonitor() if enable_performance_monitoring else None
        self.console = DebugConsole(self) if mode == "console" else None
        self._attached_agents: Dict[str, Any] = {}
        self._watched_variables: Dict[str, Any] = {}
        self._event_handlers: Dict[EventType, List[Callable]] = {}
        self._console_quit: bool = False

        if self.mode == "console":
            print("🟢 Console debug mode enabled. Execution will pause at breakpoints (type 'h' when paused).")

    def attach(self, agent, agent_id: Optional[str] = None):
        """Attach debugger to an agent"""
        if agent_id is None:
            agent_id = f"agent_{len(self._attached_agents)}"

        self._attached_agents[agent_id] = agent
        self.agent_states[agent_id] = AgentState(agent_id)

        creation_event = TraceEvent(
            event_type=EventType.AGENT_CREATED,
            agent_id=agent_id,
            step_id=f"create_{int(time.time())}",
            data={'agent_type': type(agent).__name__}
        )
        self._emit_event(creation_event)

        self._instrument_agent(agent, agent_id)
        print(f"🔧 Debugger attached to agent '{agent_id}'")
        return agent

    def _instrument_agent(self, agent, agent_id: str):
        original_methods = {}

        if hasattr(agent, 'execute_tool'):
            original_methods['execute_tool'] = agent.execute_tool
            agent.execute_tool = self._wrap_tool_execution(agent.execute_tool, agent_id)

        if hasattr(agent, 'call_llm'):
            original_methods['call_llm'] = agent.call_llm
            agent.call_llm = self._wrap_llm_call(agent.call_llm, agent_id)

        if hasattr(agent, 'update_memory'):
            original_methods['update_memory'] = agent.update_memory
            agent.update_memory = self._wrap_memory_update(agent.update_memory, agent_id)

        if hasattr(agent, 'execute_task'):
            original_methods['execute_task'] = agent.execute_task
            agent.execute_task = self._wrap_task_execution(agent.execute_task, agent_id)

        agent._agentdb_original_methods = original_methods

    def _wrap_tool_execution(self, original_method, agent_id: str):
        def wrapped_tool_execution(tool_name: str, *args, **kwargs):
            mock_output = self.mock_registry.get_tool_mock(tool_name)
            if mock_output is not None:
                print(f"🎭 Using mocked output for tool '{tool_name}'")
                return mock_output

            start_time = datetime.now()
            event = TraceEvent(
                event_type=EventType.TOOL_CALL_START,
                agent_id=agent_id,
                step_id=f"tool_{int(time.time())}_{tool_name}",
                data={'tool_name': tool_name, 'args': args, 'kwargs': kwargs}
            )
            if self.performance_monitor:
                self.performance_monitor.start_timing('tool_execution', event.id)
            self._emit_event(event)

            if self._should_break(event):
                self._trigger_breakpoint(event, agent_id)

            try:
                result = original_method(tool_name, *args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                end_event = TraceEvent(
                    event_type=EventType.TOOL_CALL_END,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={'tool_name': tool_name, 'result': result, 'duration': duration},
                    parent_event_id=event.id,
                    duration=duration
                )
                self._emit_event(end_event)
                if self.performance_monitor:
                    self.performance_monitor.record_metric('tool_execution_times', duration)
                    agent_state = self.agent_states[agent_id]
                    agent_state.performance_stats['total_tool_time'] += duration
                state = self.agent_states[agent_id]
                state.tool_outputs[tool_name] = result
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                error_event = TraceEvent(
                    event_type=EventType.ERROR,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={'tool_name': tool_name, 'error': str(e), 'error_type': type(e).__name__, 'duration': duration},
                    parent_event_id=event.id,
                    duration=duration
                )
                self._emit_event(error_event)
                state = self.agent_states[agent_id]
                state.errors_encountered += 1
                raise

        return wrapped_tool_execution

    def _wrap_llm_call(self, original_method, agent_id: str):
        def wrapped_llm_call(prompt: str, *args, **kwargs):
            mock_response = self.mock_registry.get_llm_mock(prompt)
            if mock_response is not None:
                print(f"🎭 Using mocked LLM response")
                return mock_response

            start_time = datetime.now()
            event = TraceEvent(
                event_type=EventType.LLM_CALL_START,
                agent_id=agent_id,
                step_id=f"llm_{int(time.time())}",
                data={'prompt': prompt[:200] + "..." if len(prompt) > 200 else prompt, 'full_prompt_length': len(prompt)}
            )
            if self.performance_monitor:
                self.performance_monitor.start_timing('llm_call', event.id)
            self._emit_event(event)

            response = original_method(prompt, *args, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            end_event = TraceEvent(
                event_type=EventType.LLM_CALL_END,
                agent_id=agent_id,
                step_id=event.step_id,
                data={'response': response[:200] + "..." if len(str(response)) > 200 else str(response), 'full_response_length': len(str(response)), 'duration': duration},
                parent_event_id=event.id,
                duration=duration
            )
            self._emit_event(end_event)

            if self.performance_monitor:
                self.performance_monitor.record_metric('llm_response_times', duration)
                agent_state = self.agent_states[agent_id]
                agent_state.performance_stats['total_llm_time'] += duration
                agent_state.performance_stats['avg_response_time'] = (
                    agent_state.performance_stats['total_llm_time'] / (agent_state.tasks_completed + 1)
                )

            state = self.agent_states[agent_id]
            state.last_llm_call = {'prompt': prompt, 'response': response, 'timestamp': event.timestamp, 'duration': duration}
            return response

        return wrapped_llm_call

    def _wrap_memory_update(self, original_method, agent_id: str):
        def wrapped_memory_update(key: str, value: Any, *args, **kwargs):
            event = TraceEvent(
                event_type=EventType.MEMORY_WRITE,
                agent_id=agent_id,
                step_id=f"memory_{int(time.time())}",
                data={'key': key, 'value': str(value)[:100] + "..." if len(str(value)) > 100 else str(value), 'operation': 'write'}
            )
            self._emit_event(event)

            if self._should_break(event):
                self._trigger_breakpoint(event, agent_id)

            result = original_method(key, value, *args, **kwargs)
            state = self.agent_states[agent_id]
            state.memory[key] = value
            return result

        return wrapped_memory_update

    def _wrap_task_execution(self, original_method, agent_id: str):
        def wrapped_task_execution(task_description: str, *args, **kwargs):
            start_time = datetime.now()
            event = TraceEvent(
                event_type=EventType.TASK_START,
                agent_id=agent_id,
                step_id=f"task_{int(time.time())}",
                data={'task_description': task_description, 'args': args, 'kwargs': kwargs}
            )
            self._emit_event(event)
            try:
                result = original_method(task_description, *args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                end_event = TraceEvent(
                    event_type=EventType.TASK_END,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={'result': result, 'duration': duration},
                    parent_event_id=event.id,
                    duration=duration
                )
                self._emit_event(end_event)
                state = self.agent_states[agent_id]
                state.tasks_completed += 1
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                error_event = TraceEvent(
                    event_type=EventType.ERROR,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={'task': task_description, 'error': str(e), 'duration': duration},
                    parent_event_id=event.id,
                    duration=duration
                )
                self._emit_event(error_event)
                state = self.agent_states[agent_id]
                state.errors_encountered += 1
                raise

        return wrapped_task_execution

    def _should_break(self, event: TraceEvent) -> bool:
        if self.mode == "console" and getattr(self, "_console_quit", False):
            return False
        breakpoints_to_remove: List[str] = []
        should_break = False
        for bp in self.breakpoints:
            if not bp.enabled:
                continue
            matches = False
            if bp.breakpoint_type == bp.breakpoint_type.BEFORE_TOOL and event.event_type == EventType.TOOL_CALL_START:
                if bp.tool_name is None or bp.tool_name == event.data.get('tool_name'):
                    matches = True
            elif bp.breakpoint_type == bp.breakpoint_type.AFTER_TOOL and event.event_type == EventType.TOOL_CALL_END:
                matches = True
            elif bp.breakpoint_type == bp.breakpoint_type.BEFORE_MEMORY_WRITE and event.event_type == EventType.MEMORY_WRITE:
                matches = True
            elif bp.breakpoint_type == bp.breakpoint_type.ON_ERROR and event.event_type == EventType.ERROR:
                matches = True
            elif bp.breakpoint_type == bp.breakpoint_type.BEFORE_REASONING and event.event_type == EventType.REASONING_START:
                matches = True
            elif bp.breakpoint_type == bp.breakpoint_type.BEFORE_LLM and event.event_type == EventType.LLM_CALL_START:
                matches = True
            elif bp.breakpoint_type == bp.breakpoint_type.AFTER_LLM and event.event_type == EventType.LLM_CALL_END:
                matches = True
            elif bp.breakpoint_type == bp.breakpoint_type.ON_AGENT_CREATE and event.event_type == EventType.AGENT_CREATED:
                matches = True
            elif bp.breakpoint_type == bp.breakpoint_type.ON_TASK_START and event.event_type == EventType.TASK_START:
                matches = True

            if bp.agent_id and bp.agent_id != event.agent_id:
                matches = False

            if bp.condition and bp.breakpoint_type == bp.breakpoint_type.CONDITIONAL:
                matches = bp.condition(event)

            if matches:
                bp.hit_count += 1
                should_break = True
                if bp.temporary:
                    breakpoints_to_remove.append(bp.id)

        for bp_id in breakpoints_to_remove:
            self.remove_breakpoint(bp_id)
        return should_break

    def _trigger_breakpoint(self, event: TraceEvent, agent_id: str):
        state = self.agent_states[agent_id]
        state.is_paused = True
        print(f"\n⏸️  Debugger paused on {event.event_type.value} for agent '{agent_id}'.")
        if self.console:
            self.console.start(event, state)

    def add_breakpoint(self, breakpoint: Breakpoint):
        self.breakpoints.append(breakpoint)

    def remove_breakpoint(self, breakpoint_id: str):
        self.breakpoints = [bp for bp in self.breakpoints if bp.id != breakpoint_id]

    def add_event_handler(self, event_type: EventType, handler: Callable[[TraceEvent], None]):
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def get_trace_summary(self) -> Dict[str, Any]:
        events_by_type: Dict[str, List[TraceEvent]] = {}
        for event in self.trace_events:
            et = event.event_type.value
            if et not in events_by_type:
                events_by_type[et] = []
            events_by_type[et].append(event)
        agent_stats = {}
        for agent_id, state in self.agent_states.items():
            agent_stats[agent_id] = {
                'tasks_completed': state.tasks_completed,
                'errors_encountered': state.errors_encountered,
                'created_at': state.created_at.isoformat()
            }
        return {
            'total_events': len(self.trace_events),
            'events_by_type': {k: len(v) for k, v in events_by_type.items()},
            'execution_time': (self.trace_events[-1].timestamp - self.trace_events[0].timestamp).total_seconds() if self.trace_events else 0,
            'agents': list(self.agent_states.keys()),
            'agent_stats': agent_stats,
            'performance_stats': self.performance_monitor.get_statistics() if self.performance_monitor else {}
        }

    def export_trace(self, filename: str):
        trace_data = {
            'summary': self.get_trace_summary(),
            'events': [
                {
                    'id': event.id,
                    'timestamp': event.timestamp.isoformat(),
                    'event_type': event.event_type.value,
                    'agent_id': event.agent_id,
                    'step_id': event.step_id,
                    'data': event.data,
                    'parent_event_id': event.parent_event_id,
                    'metadata': event.metadata,
                    'duration': event.duration
                }
                for event in self.trace_events
            ]
        }
        with open(filename, 'w') as f:
            json.dump(trace_data, f, indent=2)
        print(f"📄 Trace exported to {filename}")

    def replay_from_file(self, filename: str):
        try:
            with open(filename, 'r') as f:
                trace_data = json.load(f)
            events: List[TraceEvent] = []
            for event_data in trace_data['events']:
                event = TraceEvent(
                    id=event_data['id'],
                    timestamp=datetime.fromisoformat(event_data['timestamp']),
                    event_type=EventType(event_data['event_type']),
                    agent_id=event_data['agent_id'],
                    step_id=event_data['step_id'],
                    data=event_data['data'],
                    parent_event_id=event_data.get('parent_event_id'),
                    metadata=event_data.get('metadata', {}),
                    duration=event_data.get('duration')
                )
                events.append(event)
            self.mock_registry.set_replay_mode(events)
            print(f"🎬 Replay mode activated with {len(events)} events")
        except Exception as e:
            print(f"❌ Failed to load replay file: {e}")

    def _emit_event(self, event: TraceEvent):
        self.trace_events.append(event)
        if event.event_type in self._event_handlers:
            for handler in self._event_handlers[event.event_type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Error in event handler: {e}")


