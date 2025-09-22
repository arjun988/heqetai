"""
AgentDebugger - A Revolutionary Python Framework for AI Agent Debugging
=====================================================================

A comprehensive debugging framework that provides step-by-step visibility
into AI agent behavior, similar to pdb for Python code.

Author: AI Assistant
Version: 2.0.0
License: MIT
"""

import json
import time
import uuid
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union, AsyncGenerator
import threading
import copy
from contextlib import contextmanager
import inspect
import re


class EventType(Enum):
    """Types of events that can be traced in agent execution"""
    REASONING_START = "reasoning_start"
    REASONING_END = "reasoning_end"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END = "tool_call_end"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    LLM_CALL_START = "llm_call_start"
    LLM_CALL_END = "llm_call_end"
    ERROR = "error"
    BREAKPOINT = "breakpoint"
    INTER_AGENT_MESSAGE = "inter_agent_message"
    AGENT_CREATED = "agent_created"
    AGENT_DESTROYED = "agent_destroyed"
    TASK_START = "task_start"
    TASK_END = "task_end"
    CONTEXT_SWITCH = "context_switch"


class BreakpointType(Enum):
    """Types of breakpoints supported"""
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    BEFORE_MEMORY_WRITE = "before_memory_write"
    AFTER_MEMORY_WRITE = "after_memory_write"
    AFTER_REASONING = "after_reasoning"
    BEFORE_REASONING = "before_reasoning"
    BEFORE_LLM = "before_llm"
    AFTER_LLM = "after_llm"
    ON_ERROR = "on_error"
    CONDITIONAL = "conditional"
    ON_AGENT_CREATE = "on_agent_create"
    ON_TASK_START = "on_task_start"


@dataclass
class TraceEvent:
    """Represents a single event in agent execution trace"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: EventType = EventType.REASONING_START
    agent_id: str = ""
    step_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    parent_event_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration: Optional[float] = None  # Duration in seconds for end events


@dataclass
class Breakpoint:
    """Represents a breakpoint in agent execution"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    breakpoint_type: BreakpointType = BreakpointType.BEFORE_TOOL
    condition: Optional[Callable[[TraceEvent], bool]] = None
    tool_name: Optional[str] = None
    agent_id: Optional[str] = None
    enabled: bool = True
    hit_count: int = 0
    temporary: bool = False  # One-time breakpoint
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentState:
    """Tracks the current state of an agent during execution"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.memory: Dict[str, Any] = {}
        self.execution_stack: List[str] = []
        self.current_step: Optional[str] = None
        self.tool_outputs: Dict[str, Any] = {}
        self.reasoning_log: List[str] = []
        self.is_paused: bool = False
        self.last_llm_call: Optional[Dict[str, Any]] = None
        self.created_at: datetime = datetime.now()
        self.tasks_completed: int = 0
        self.errors_encountered: int = 0
        self.performance_stats: Dict[str, float] = {
            'total_tool_time': 0.0,
            'total_llm_time': 0.0,
            'avg_response_time': 0.0
        }


class MockRegistry:
    """Registry for mocked tool outputs and LLM responses"""
    
    def __init__(self):
        self._tool_mocks: Dict[str, Any] = {}
        self._llm_mocks: Dict[str, Any] = {}
        self._replay_mode: bool = False
        self._replay_data: List[TraceEvent] = []
        self._replay_index: int = 0
        self._mock_callbacks: Dict[str, Callable] = {}
        
    def mock_tool(self, tool_name: str, output: Any, callback: Optional[Callable] = None):
        """Mock the output of a specific tool"""
        self._tool_mocks[tool_name] = output
        if callback:
            self._mock_callbacks[tool_name] = callback
        
    def mock_llm(self, prompt_pattern: str, response: Any, callback: Optional[Callable] = None):
        """Mock LLM response for prompts matching a pattern"""
        self._llm_mocks[prompt_pattern] = response
        if callback:
            self._mock_callbacks[f"llm_{prompt_pattern}"] = callback
        
    def get_tool_mock(self, tool_name: str) -> Optional[Any]:
        """Get mocked output for a tool"""
        mock = self._tool_mocks.get(tool_name)
        if mock is not None and tool_name in self._mock_callbacks:
            # Execute callback for dynamic mocking
            return self._mock_callbacks[tool_name]()
        return mock
        
    def get_llm_mock(self, prompt: str) -> Optional[Any]:
        """Get mocked LLM response for a prompt"""
        for pattern, response in self._llm_mocks.items():
            if pattern in prompt:
                callback_key = f"llm_{pattern}"
                if callback_key in self._mock_callbacks:
                    return self._mock_callbacks[callback_key](prompt)
                return response
        return None
        
    def set_replay_mode(self, replay_data: List[TraceEvent]):
        """Enable replay mode with historical trace data"""
        self._replay_mode = True
        self._replay_data = replay_data
        self._replay_index = 0
        
    def get_next_replay_event(self) -> Optional[TraceEvent]:
        """Get next event in replay mode"""
        if self._replay_mode and self._replay_index < len(self._replay_data):
            event = self._replay_data[self._replay_index]
            self._replay_index += 1
            return event
        return None
        
    def is_replay_mode(self) -> bool:
        return self._replay_mode

    def clear_mocks(self):
        """Clear all mocks and callbacks"""
        self._tool_mocks.clear()
        self._llm_mocks.clear()
        self._mock_callbacks.clear()


class PerformanceMonitor:
    """Monitor and analyze agent performance metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {
            'tool_execution_times': [],
            'llm_response_times': [],
            'memory_access_times': [],
            'reasoning_times': []
        }
        self.start_times: Dict[str, datetime] = {}
        
    def start_timing(self, event_type: str, event_id: str):
        """Start timing for a specific event"""
        self.start_times[event_id] = datetime.now()
        
    def end_timing(self, event_id: str) -> Optional[float]:
        """End timing and return duration"""
        if event_id in self.start_times:
            duration = (datetime.now() - self.start_times[event_id]).total_seconds()
            del self.start_times[event_id]
            return duration
        return None
        
    def record_metric(self, metric_type: str, value: float):
        """Record a performance metric"""
        if metric_type in self.metrics:
            self.metrics[metric_type].append(value)
            
    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics"""
        stats = {}
        for metric_type, values in self.metrics.items():
            if values:
                stats[metric_type] = {
                    'count': len(values),
                    'mean': sum(values) / len(values),
                    'max': max(values),
                    'min': min(values),
                    'latest': values[-1] if values else 0
                }
            else:
                stats[metric_type] = {'count': 0, 'mean': 0, 'max': 0, 'min': 0, 'latest': 0}
        return stats


class DebugConsole:
    """Interactive debugging console similar to pdb"""
    
    def __init__(self, debugger):
        self.debugger = debugger
        self.commands = {
            'n': self._next_step,
            'next': self._next_step,
            's': self._step_into,
            'step': self._step_into,
            'c': self._continue,
            'continue': self._continue,
            'm': self._show_memory,
            'memory': self._show_memory,
            'e': self._edit_next,
            'edit': self._edit_next,
            'o': self._override_output,
            'override': self._override_output,
            'b': self._set_breakpoint,
            'breakpoint': self._set_breakpoint,
            'l': self._list_breakpoints,
            'list': self._list_breakpoints,
            'h': self._help,
            'help': self._help,
            'q': self._quit,
            'quit': self._quit,
            'trace': self._show_trace,
            'state': self._show_state,
            'p': self._performance,
            'performance': self._performance,
            'watch': self._watch_variable,
            'mock': self._mock_tool,
            'replay': self._replay_trace,
            'export': self._export_trace,
            'agents': self._list_agents
        }
        
    def start(self, current_event: TraceEvent, agent_state: AgentState):
        """Start the interactive debugging session"""
        print(f"\n🐛 AgentDebugger Console - Paused at {current_event.event_type.value}")
        print(f"Agent: {current_event.agent_id}")
        print(f"Step: {current_event.step_id}")
        print(f"Event: {current_event.data}")
        print("\nType 'h' for help, 'c' to continue")
        
        while agent_state.is_paused:
            try:
                command = input("\n(agentdb) ").strip().lower()
                if command in self.commands:
                    self.commands[command](current_event, agent_state)
                elif command.startswith('watch '):
                    self._watch_variable(current_event, agent_state, command[6:])
                elif command.startswith('mock '):
                    self._mock_tool(current_event, agent_state, command[5:])
                else:
                    print(f"Unknown command: {command}. Type 'h' for help.")
            except KeyboardInterrupt:
                print("\nUse 'q' to quit or 'c' to continue")
            except EOFError:
                break
    
    def _next_step(self, event: TraceEvent, state: AgentState):
        """Continue to next step"""
        print("Continuing to next step...")
        state.is_paused = False
        
    def _step_into(self, event: TraceEvent, state: AgentState):
        """Step into sub-agent execution"""
        print("Stepping into sub-execution...")
        state.is_paused = False
        
    def _continue(self, event: TraceEvent, state: AgentState):
        """Continue execution"""
        print("Continuing execution...")
        state.is_paused = False
        
    def _show_memory(self, event: TraceEvent, state: AgentState):
        """Show current memory state"""
        print("\n📚 Memory State:")
        for key, value in state.memory.items():
            print(f"  {key}: {value}")
            
    def _edit_next(self, event: TraceEvent, state: AgentState):
        """Edit the next operation before execution"""
        if event.event_type == EventType.TOOL_CALL_START:
            print(f"Current tool call: {event.data}")
            new_input = input("Enter new input (or press Enter to keep current): ")
            if new_input.strip():
                event.data['input'] = new_input
                print("Tool input updated!")
        else:
            print("No editable operation at current step")
            
    def _override_output(self, event: TraceEvent, state: AgentState):
        """Override tool output manually"""
        tool_name = input("Tool name to override: ")
        output = input("Override output: ")
        self.debugger.mock_registry.mock_tool(tool_name, output)
        print(f"Tool '{tool_name}' output overridden!")
        
    def _set_breakpoint(self, event: TraceEvent, state: AgentState):
        """Set a new breakpoint"""
        print("Available breakpoint types:")
        for bp_type in BreakpointType:
            print(f"  - {bp_type.value}")
        bp_type_str = input("Breakpoint type: ")
        try:
            bp_type = BreakpointType(bp_type_str)
            breakpoint = Breakpoint(breakpoint_type=bp_type)
            self.debugger.add_breakpoint(breakpoint)
            print(f"Breakpoint {breakpoint.id} added!")
        except ValueError:
            print("Invalid breakpoint type")
            
    def _list_breakpoints(self, event: TraceEvent, state: AgentState):
        """List all breakpoints"""
        print("\n🔴 Active Breakpoints:")
        for bp in self.debugger.breakpoints:
            status = "✓" if bp.enabled else "✗"
            print(f"  {status} {bp.id}: {bp.breakpoint_type.value} (hits: {bp.hit_count})")
            
    def _show_trace(self, event: TraceEvent, state: AgentState):
        """Show execution trace"""
        print("\n📊 Execution Trace:")
        for trace_event in self.debugger.trace_events[-10:]:  # Last 10 events
            duration = f" ({trace_event.duration:.2f}s)" if trace_event.duration else ""
            print(f"  [{trace_event.timestamp.strftime('%H:%M:%S')}{duration}] {trace_event.agent_id} - {trace_event.event_type.value}")
            
    def _show_state(self, event: TraceEvent, state: AgentState):
        """Show current agent state"""
        print(f"\n🤖 Agent State:")
        print(f"  ID: {state.agent_id}")
        print(f"  Current Step: {state.current_step}")
        print(f"  Execution Stack: {state.execution_stack}")
        print(f"  Memory Keys: {list(state.memory.keys())}")
        print(f"  Tool Outputs: {list(state.tool_outputs.keys())}")
        print(f"  Tasks Completed: {state.tasks_completed}")
        print(f"  Errors: {state.errors_encountered}")
        
    def _performance(self, event: TraceEvent, state: AgentState):
        """Show performance metrics"""
        stats = self.debugger.performance_monitor.get_statistics()
        print("\n📈 Performance Metrics:")
        for metric, values in stats.items():
            if values['count'] > 0:
                print(f"  {metric}: {values['mean']:.3f}s avg ({values['count']} samples)")
                
    def _watch_variable(self, event: TraceEvent, state: AgentState, variable_name: str = ""):
        """Watch a variable for changes"""
        if not variable_name:
            variable_name = input("Variable name to watch: ")
        
        def watch_condition(event: TraceEvent) -> bool:
            return (event.event_type == EventType.MEMORY_WRITE and 
                   event.data.get('key') == variable_name)
        
        bp = Breakpoint(
            breakpoint_type=BreakpointType.CONDITIONAL,
            condition=watch_condition,
            temporary=True
        )
        self.debugger.add_breakpoint(bp)
        print(f"👀 Watching variable '{variable_name}' for changes")
        
    def _mock_tool(self, event: TraceEvent, state: AgentState, tool_name: str = ""):
        """Mock a tool with custom output"""
        if not tool_name:
            tool_name = input("Tool name to mock: ")
        output = input(f"Mock output for {tool_name}: ")
        self.debugger.mock_registry.mock_tool(tool_name, output)
        print(f"🎭 Tool '{tool_name}' mocked with output: {output}")
        
    def _replay_trace(self, event: TraceEvent, state: AgentState):
        """Replay trace from file"""
        filename = input("Trace file to replay: ")
        try:
            self.debugger.replay_from_file(filename)
            print(f"🎬 Replay mode activated with {filename}")
        except Exception as e:
            print(f"❌ Failed to replay: {e}")
            
    def _export_trace(self, event: TraceEvent, state: AgentState):
        """Export current trace"""
        filename = input("Export filename: ")
        self.debugger.export_trace(filename)
        
    def _list_agents(self, event: TraceEvent, state: AgentState):
        """List all registered agents"""
        print("\n🤖 Registered Agents:")
        for agent_id, agent_state in self.debugger.agent_states.items():
            status = "⏸️" if agent_state.is_paused else "▶️"
            print(f"  {status} {agent_id} (tasks: {agent_state.tasks_completed}, errors: {agent_state.errors_encountered})")
        
    def _help(self, event: TraceEvent, state: AgentState):
        """Show help message"""
        print("""
🔧 AgentDebugger Commands:
  n, next     - Continue to next step
  s, step     - Step into sub-agent execution  
  c, continue - Continue execution
  m, memory   - Show memory state
  e, edit     - Edit next operation
  o, override - Override tool output
  b, breakpoint - Set breakpoint
  l, list     - List breakpoints
  trace       - Show execution trace
  state       - Show agent state
  p, performance - Show performance metrics
  watch <var> - Watch variable for changes
  mock <tool> - Mock tool output
  replay      - Replay trace from file
  export      - Export current trace
  agents      - List all agents
  h, help     - Show this help
  q, quit     - Quit debugger
        """)
        
    def _quit(self, event: TraceEvent, state: AgentState):
        """Quit debugger"""
        print("Quitting debugger...")
        self.debugger._console_quit = True
        state.is_paused = False


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
        
        # Emit agent creation event
        creation_event = TraceEvent(
            event_type=EventType.AGENT_CREATED,
            agent_id=agent_id,
            step_id=f"create_{int(time.time())}",
            data={'agent_type': type(agent).__name__}
        )
        self._emit_event(creation_event)
        
        # Wrap agent methods with debugging instrumentation
        self._instrument_agent(agent, agent_id)
        
        print(f"🔧 Debugger attached to agent '{agent_id}'")
        return agent
        
    def _instrument_agent(self, agent, agent_id: str):
        """Add debugging instrumentation to agent methods"""
        original_methods = {}
        
        # Wrap tool execution
        if hasattr(agent, 'execute_tool'):
            original_methods['execute_tool'] = agent.execute_tool
            agent.execute_tool = self._wrap_tool_execution(
                agent.execute_tool, agent_id
            )
            
        # Wrap LLM calls
        if hasattr(agent, 'call_llm'):
            original_methods['call_llm'] = agent.call_llm
            agent.call_llm = self._wrap_llm_call(agent.call_llm, agent_id)
            
        # Wrap memory operations
        if hasattr(agent, 'update_memory'):
            original_methods['update_memory'] = agent.update_memory
            agent.update_memory = self._wrap_memory_update(
                agent.update_memory, agent_id
            )
            
        # Wrap task execution
        if hasattr(agent, 'execute_task'):
            original_methods['execute_task'] = agent.execute_task
            agent.execute_task = self._wrap_task_execution(
                agent.execute_task, agent_id
            )
            
        # Store original methods for restoration
        agent._agentdb_original_methods = original_methods
        
    def _wrap_tool_execution(self, original_method, agent_id: str):
        """Wrap tool execution with debugging"""
        def wrapped_tool_execution(tool_name: str, *args, **kwargs):
            # Check for mocked output first
            mock_output = self.mock_registry.get_tool_mock(tool_name)
            if mock_output is not None:
                print(f"🎭 Using mocked output for tool '{tool_name}'")
                return mock_output
                
            # Create trace event for tool call start
            start_time = datetime.now()
            event = TraceEvent(
                event_type=EventType.TOOL_CALL_START,
                agent_id=agent_id,
                step_id=f"tool_{int(time.time())}_{tool_name}",
                data={
                    'tool_name': tool_name,
                    'args': args,
                    'kwargs': kwargs
                }
            )
            
            # Performance monitoring
            if self.performance_monitor:
                self.performance_monitor.start_timing('tool_execution', event.id)
                
            self._emit_event(event)
            
            # Check breakpoints
            if self._should_break(event):
                self._trigger_breakpoint(event, agent_id)
                
            try:
                # Execute original tool
                result = original_method(tool_name, *args, **kwargs)
                
                # Calculate duration
                duration = (datetime.now() - start_time).total_seconds()
                
                # Create trace event for tool call end
                end_event = TraceEvent(
                    event_type=EventType.TOOL_CALL_END,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={
                        'tool_name': tool_name,
                        'result': result,
                        'duration': duration
                    },
                    parent_event_id=event.id,
                    duration=duration
                )
                self._emit_event(end_event)
                
                # Update performance metrics
                if self.performance_monitor:
                    self.performance_monitor.record_metric('tool_execution_times', duration)
                    agent_state = self.agent_states[agent_id]
                    agent_state.performance_stats['total_tool_time'] += duration
                
                # Update agent state
                state = self.agent_states[agent_id]
                state.tool_outputs[tool_name] = result
                
                return result
                
            except Exception as e:
                # Calculate duration even for errors
                duration = (datetime.now() - start_time).total_seconds()
                
                # Create error event
                error_event = TraceEvent(
                    event_type=EventType.ERROR,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={
                        'tool_name': tool_name,
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'duration': duration
                    },
                    parent_event_id=event.id,
                    duration=duration
                )
                self._emit_event(error_event)
                
                # Update error count
                state = self.agent_states[agent_id]
                state.errors_encountered += 1
                
                raise
                
        return wrapped_tool_execution
        
    def _wrap_llm_call(self, original_method, agent_id: str):
        """Wrap LLM calls with debugging"""
        def wrapped_llm_call(prompt: str, *args, **kwargs):
            # Check for mocked response
            mock_response = self.mock_registry.get_llm_mock(prompt)
            if mock_response is not None:
                print(f"🎭 Using mocked LLM response")
                return mock_response
                
            # Create trace event
            start_time = datetime.now()
            event = TraceEvent(
                event_type=EventType.LLM_CALL_START,
                agent_id=agent_id,
                step_id=f"llm_{int(time.time())}",
                data={
                    'prompt': prompt[:200] + "..." if len(prompt) > 200 else prompt,
                    'full_prompt_length': len(prompt)
                }
            )
            
            if self.performance_monitor:
                self.performance_monitor.start_timing('llm_call', event.id)
                
            self._emit_event(event)
            
            # Execute original method
            response = original_method(prompt, *args, **kwargs)
            
            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()
            
            # Create end event
            end_event = TraceEvent(
                event_type=EventType.LLM_CALL_END,
                agent_id=agent_id,
                step_id=event.step_id,
                data={
                    'response': response[:200] + "..." if len(str(response)) > 200 else str(response),
                    'full_response_length': len(str(response)),
                    'duration': duration
                },
                parent_event_id=event.id,
                duration=duration
            )
            self._emit_event(end_event)
            
            # Update performance metrics
            if self.performance_monitor:
                self.performance_monitor.record_metric('llm_response_times', duration)
                agent_state = self.agent_states[agent_id]
                agent_state.performance_stats['total_llm_time'] += duration
                agent_state.performance_stats['avg_response_time'] = (
                    agent_state.performance_stats['total_llm_time'] / 
                    (agent_state.tasks_completed + 1)
                )
            
            # Update agent state
            state = self.agent_states[agent_id]
            state.last_llm_call = {
                'prompt': prompt,
                'response': response,
                'timestamp': event.timestamp,
                'duration': duration
            }
            
            return response
            
        return wrapped_llm_call
        
    def _wrap_memory_update(self, original_method, agent_id: str):
        """Wrap memory updates with debugging"""
        def wrapped_memory_update(key: str, value: Any, *args, **kwargs):
            # Create trace event
            event = TraceEvent(
                event_type=EventType.MEMORY_WRITE,
                agent_id=agent_id,
                step_id=f"memory_{int(time.time())}",
                data={
                    'key': key,
                    'value': str(value)[:100] + "..." if len(str(value)) > 100 else str(value),
                    'operation': 'write'
                }
            )
            self._emit_event(event)
            
            # Check breakpoints
            if self._should_break(event):
                self._trigger_breakpoint(event, agent_id)
                
            # Execute original method
            result = original_method(key, value, *args, **kwargs)
            
            # Update agent state
            state = self.agent_states[agent_id]
            state.memory[key] = value
            
            return result
            
        return wrapped_memory_update
        
    def _wrap_task_execution(self, original_method, agent_id: str):
        """Wrap task execution with debugging"""
        def wrapped_task_execution(task_description: str, *args, **kwargs):
            # Create task start event
            start_time = datetime.now()
            event = TraceEvent(
                event_type=EventType.TASK_START,
                agent_id=agent_id,
                step_id=f"task_{int(time.time())}",
                data={
                    'task_description': task_description,
                    'args': args,
                    'kwargs': kwargs
                }
            )
            self._emit_event(event)
            
            try:
                # Execute original method
                result = original_method(task_description, *args, **kwargs)
                
                # Calculate duration
                duration = (datetime.now() - start_time).total_seconds()
                
                # Create task end event
                end_event = TraceEvent(
                    event_type=EventType.TASK_END,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={
                        'result': result,
                        'duration': duration
                    },
                    parent_event_id=event.id,
                    duration=duration
                )
                self._emit_event(end_event)
                
                # Update agent state
                state = self.agent_states[agent_id]
                state.tasks_completed += 1
                
                return result
                
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                error_event = TraceEvent(
                    event_type=EventType.ERROR,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={
                        'task': task_description,
                        'error': str(e),
                        'duration': duration
                    },
                    parent_event_id=event.id,
                    duration=duration
                )
                self._emit_event(error_event)
                state = self.agent_states[agent_id]
                state.errors_encountered += 1
                raise
                
        return wrapped_task_execution
        
    def _should_break(self, event: TraceEvent) -> bool:
        """Check if execution should break at this event"""
        if self.mode == "console" and getattr(self, "_console_quit", False):
            return False
        breakpoints_to_remove = []
        should_break = False
        
        for bp in self.breakpoints:
            if not bp.enabled:
                continue
                
            matches = False
            
            # Check breakpoint type match
            if bp.breakpoint_type == BreakpointType.BEFORE_TOOL and event.event_type == EventType.TOOL_CALL_START:
                if bp.tool_name is None or bp.tool_name == event.data.get('tool_name'):
                    matches = True
                    
            elif bp.breakpoint_type == BreakpointType.AFTER_TOOL and event.event_type == EventType.TOOL_CALL_END:
                matches = True
                
            elif bp.breakpoint_type == BreakpointType.BEFORE_MEMORY_WRITE and event.event_type == EventType.MEMORY_WRITE:
                matches = True
                
            elif bp.breakpoint_type == BreakpointType.ON_ERROR and event.event_type == EventType.ERROR:
                matches = True

            elif bp.breakpoint_type == BreakpointType.BEFORE_REASONING and event.event_type == EventType.REASONING_START:
                matches = True

            elif bp.breakpoint_type == BreakpointType.BEFORE_LLM and event.event_type == EventType.LLM_CALL_START:
                matches = True

            elif bp.breakpoint_type == BreakpointType.AFTER_LLM and event.event_type == EventType.LLM_CALL_END:
                matches = True
                
            elif bp.breakpoint_type == BreakpointType.ON_AGENT_CREATE and event.event_type == EventType.AGENT_CREATED:
                matches = True
                
            elif bp.breakpoint_type == BreakpointType.ON_TASK_START and event.event_type == EventType.TASK_START:
                matches = True
                
            # Check agent-specific breakpoints
            if bp.agent_id and bp.agent_id != event.agent_id:
                matches = False
                
            # Check conditional breakpoints
            if bp.breakpoint_type == BreakpointType.CONDITIONAL and bp.condition:
                matches = bp.condition(event)
                
            if matches:
                bp.hit_count += 1
                should_break = True
                
                # Remove temporary breakpoints after first hit
                if bp.temporary:
                    breakpoints_to_remove.append(bp.id)
                
        # Clean up temporary breakpoints
        for bp_id in breakpoints_to_remove:
            self.remove_breakpoint(bp_id)
                
        return should_break
        
    def _trigger_breakpoint(self, event: TraceEvent, agent_id: str):
        """Trigger a breakpoint and start interactive debugging"""
        state = self.agent_states[agent_id]
        state.is_paused = True
        print(f"\n⏸️  Debugger paused on {event.event_type.value} for agent '{agent_id}'.")
        
        if self.console:
            self.console.start(event, state)
            
    def add_breakpoint(self, breakpoint: Breakpoint):
        """Add a new breakpoint"""
        self.breakpoints.append(breakpoint)
        
    def remove_breakpoint(self, breakpoint_id: str):
        """Remove a breakpoint by ID"""
        self.breakpoints = [bp for bp in self.breakpoints if bp.id != breakpoint_id]
        
    def add_event_handler(self, event_type: EventType, handler: Callable[[TraceEvent], None]):
        """Add an event handler for specific event types"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        
    def get_trace_summary(self) -> Dict[str, Any]:
        """Get a summary of the execution trace"""
        events_by_type = {}
        for event in self.trace_events:
            event_type = event.event_type.value
            if event_type not in events_by_type:
                events_by_type[event_type] = []
            events_by_type[event_type].append(event)
            
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
            'execution_time': (
                self.trace_events[-1].timestamp - self.trace_events[0].timestamp
            ).total_seconds() if self.trace_events else 0,
            'agents': list(self.agent_states.keys()),
            'agent_stats': agent_stats,
            'performance_stats': self.performance_monitor.get_statistics() if self.performance_monitor else {}
        }
        
    def export_trace(self, filename: str):
        """Export trace to JSON file"""
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
        """Replay trace from a JSON file"""
        try:
            with open(filename, 'r') as f:
                trace_data = json.load(f)
                
            events = []
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
        """Emit an event to all listeners"""
        self.trace_events.append(event)
        
        # Call event-specific handlers
        if event.event_type in self._event_handlers:
            for handler in self._event_handlers[event.event_type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Error in event handler: {e}")


        