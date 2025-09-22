"""
AgentDebugger - A Revolutionary Python Framework for AI Agent Debugging
=====================================================================

A comprehensive debugging framework that provides step-by-step visibility
into AI agent behavior, similar to pdb for Python code.

Author: AI Assistant
Version: 1.0.0
License: MIT
"""

import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union
import threading
import copy
from contextlib import contextmanager


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


@dataclass
class Breakpoint:
    """Represents a breakpoint in agent execution"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    breakpoint_type: BreakpointType = BreakpointType.BEFORE_TOOL
    condition: Optional[Callable[[TraceEvent], bool]] = None
    tool_name: Optional[str] = None
    enabled: bool = True
    hit_count: int = 0
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


class MockRegistry:
    """Registry for mocked tool outputs and LLM responses"""
    
    def __init__(self):
        self._tool_mocks: Dict[str, Any] = {}
        self._llm_mocks: Dict[str, Any] = {}
        self._replay_mode: bool = False
        self._replay_data: List[TraceEvent] = []
        
    def mock_tool(self, tool_name: str, output: Any):
        """Mock the output of a specific tool"""
        self._tool_mocks[tool_name] = output
        
    def mock_llm(self, prompt_pattern: str, response: Any):
        """Mock LLM response for prompts matching a pattern"""
        self._llm_mocks[prompt_pattern] = response
        
    def get_tool_mock(self, tool_name: str) -> Optional[Any]:
        """Get mocked output for a tool"""
        return self._tool_mocks.get(tool_name)
        
    def get_llm_mock(self, prompt: str) -> Optional[Any]:
        """Get mocked LLM response for a prompt"""
        for pattern, response in self._llm_mocks.items():
            if pattern in prompt:
                return response
        return None
        
    def set_replay_mode(self, replay_data: List[TraceEvent]):
        """Enable replay mode with historical trace data"""
        self._replay_mode = True
        self._replay_data = replay_data
        
    def is_replay_mode(self) -> bool:
        return self._replay_mode


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
            'state': self._show_state
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
            print(f"  [{trace_event.timestamp.strftime('%H:%M:%S')}] {trace_event.event_type.value}: {trace_event.data}")
            
    def _show_state(self, event: TraceEvent, state: AgentState):
        """Show current agent state"""
        print(f"\n🤖 Agent State:")
        print(f"  ID: {state.agent_id}")
        print(f"  Current Step: {state.current_step}")
        print(f"  Execution Stack: {state.execution_stack}")
        print(f"  Memory Keys: {list(state.memory.keys())}")
        print(f"  Tool Outputs: {list(state.tool_outputs.keys())}")
        
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
  h, help     - Show this help
  q, quit     - Quit debugger
        """)
        
    def _quit(self, event: TraceEvent, state: AgentState):
        """Quit debugger"""
        print("Quitting debugger...")
        state.is_paused = False


class AgentDebugger:
    """Main debugger class that wraps and monitors agent execution"""
    
    def __init__(self, mode: str = "console", enable_replay: bool = True):
        self.mode = mode
        self.enable_replay = enable_replay
        self.trace_events: List[TraceEvent] = []
        self.breakpoints: List[Breakpoint] = []
        self.agent_states: Dict[str, AgentState] = {}
        self.mock_registry = MockRegistry()
        self.console = DebugConsole(self) if mode == "console" else None
        self._attached_agents: Dict[str, Any] = {}
        if self.mode == "console":
            print("🟢 Console debug mode enabled. Execution will pause at breakpoints (type 'h' when paused).")
        self._global_listeners: List[Callable[[TraceEvent], None]] = []
        
    def attach(self, agent, agent_id: Optional[str] = None):
        """Attach debugger to an agent"""
        if agent_id is None:
            agent_id = f"agent_{len(self._attached_agents)}"
            
        self._attached_agents[agent_id] = agent
        self.agent_states[agent_id] = AgentState(agent_id)
        
        # Wrap agent methods with debugging instrumentation
        self._instrument_agent(agent, agent_id)
        
        print(f"🔧 Debugger attached to agent '{agent_id}'")
        return agent
        
    def _instrument_agent(self, agent, agent_id: str):
        """Add debugging instrumentation to agent methods"""
        # This would vary based on the agent framework
        # Here's a generic approach that wraps common methods
        
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
            event = TraceEvent(
                event_type=EventType.TOOL_CALL_START,
                agent_id=agent_id,
                step_id=f"tool_{int(time.time())}",
                data={
                    'tool_name': tool_name,
                    'args': args,
                    'kwargs': kwargs
                }
            )
            self.trace_events.append(event)
            
            # Check breakpoints
            if self._should_break(event):
                self._trigger_breakpoint(event, agent_id)
                
            try:
                # Execute original tool
                result = original_method(tool_name, *args, **kwargs)
                
                # Create trace event for tool call end
                end_event = TraceEvent(
                    event_type=EventType.TOOL_CALL_END,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={
                        'tool_name': tool_name,
                        'result': result
                    },
                    parent_event_id=event.id
                )
                self.trace_events.append(end_event)
                
                # Update agent state
                state = self.agent_states[agent_id]
                state.tool_outputs[tool_name] = result
                
                return result
                
            except Exception as e:
                # Create error event
                error_event = TraceEvent(
                    event_type=EventType.ERROR,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={
                        'tool_name': tool_name,
                        'error': str(e),
                        'error_type': type(e).__name__
                    },
                    parent_event_id=event.id
                )
                self.trace_events.append(error_event)
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
            event = TraceEvent(
                event_type=EventType.LLM_CALL_START,
                agent_id=agent_id,
                step_id=f"llm_{int(time.time())}",
                data={
                    'prompt': prompt[:200] + "..." if len(prompt) > 200 else prompt,
                    'full_prompt_length': len(prompt)
                }
            )
            self.trace_events.append(event)
            
            # Execute original method
            response = original_method(prompt, *args, **kwargs)
            
            # Create end event
            end_event = TraceEvent(
                event_type=EventType.LLM_CALL_END,
                agent_id=agent_id,
                step_id=event.step_id,
                data={
                    'response': response[:200] + "..." if len(str(response)) > 200 else str(response),
                    'full_response_length': len(str(response))
                },
                parent_event_id=event.id
            )
            self.trace_events.append(end_event)
            
            # Update agent state
            state = self.agent_states[agent_id]
            state.last_llm_call = {
                'prompt': prompt,
                'response': response,
                'timestamp': event.timestamp
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
            self.trace_events.append(event)
            
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
        
    def _should_break(self, event: TraceEvent) -> bool:
        """Check if execution should break at this event"""
        for bp in self.breakpoints:
            if not bp.enabled:
                continue
                
            should_break = False
            
            # Check breakpoint type match
            if bp.breakpoint_type == BreakpointType.BEFORE_TOOL and event.event_type == EventType.TOOL_CALL_START:
                if bp.tool_name is None or bp.tool_name == event.data.get('tool_name'):
                    should_break = True
                    
            elif bp.breakpoint_type == BreakpointType.AFTER_TOOL and event.event_type == EventType.TOOL_CALL_END:
                should_break = True
                
            elif bp.breakpoint_type == BreakpointType.BEFORE_MEMORY_WRITE and event.event_type == EventType.MEMORY_WRITE:
                should_break = True
                
            elif bp.breakpoint_type == BreakpointType.ON_ERROR and event.event_type == EventType.ERROR:
                should_break = True

            elif bp.breakpoint_type == BreakpointType.BEFORE_REASONING and event.event_type == EventType.REASONING_START:
                should_break = True

            elif bp.breakpoint_type == BreakpointType.BEFORE_LLM and event.event_type == EventType.LLM_CALL_START:
                should_break = True

            elif bp.breakpoint_type == BreakpointType.AFTER_LLM and event.event_type == EventType.LLM_CALL_END:
                should_break = True
                
            # Check conditional breakpoints
            if bp.breakpoint_type == BreakpointType.CONDITIONAL and bp.condition:
                should_break = bp.condition(event)
                
            if should_break:
                bp.hit_count += 1
                return True
                
        return False
        
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
        
    def get_trace_summary(self) -> Dict[str, Any]:
        """Get a summary of the execution trace"""
        events_by_type = {}
        for event in self.trace_events:
            event_type = event.event_type.value
            if event_type not in events_by_type:
                events_by_type[event_type] = []
            events_by_type[event_type].append(event)
            
        return {
            'total_events': len(self.trace_events),
            'events_by_type': {k: len(v) for k, v in events_by_type.items()},
            'execution_time': (
                self.trace_events[-1].timestamp - self.trace_events[0].timestamp
            ).total_seconds() if self.trace_events else 0,
            'agents': list(self.agent_states.keys())
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
                    'metadata': event.metadata
                }
                for event in self.trace_events
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(trace_data, f, indent=2)
        print(f"📄 Trace exported to {filename}")

    def clear_traces(self, keep_last: int = 0):
        """Clear trace events, optionally keeping the last N events."""
        if keep_last <= 0 or keep_last >= len(self.trace_events):
            self.trace_events = self.trace_events[-max(keep_last, 0):]
        else:
            self.trace_events = self.trace_events[-keep_last:]
        print(f"🧹 Cleared traces, kept last {min(keep_last, len(self.trace_events))} events")

    def add_global_listener(self, listener: Callable[[TraceEvent], None]):
        """Register a callback invoked for every new trace event."""
        self._global_listeners.append(listener)

    def _emit_event(self, event: TraceEvent):
        """Append event and notify listeners."""
        self.trace_events.append(event)
        for listener in self._global_listeners:
            try:
                listener(event)
            except Exception:
                pass
        
    def replay_from_file(self, filename: str):
        """Load and replay trace from JSON file"""
        with open(filename, 'r') as f:
            trace_data = json.load(f)
            
        # Convert back to TraceEvent objects
        replay_events = []
        for event_data in trace_data['events']:
            event = TraceEvent(
                id=event_data['id'],
                timestamp=datetime.fromisoformat(event_data['timestamp']),
                event_type=EventType(event_data['event_type']),
                agent_id=event_data['agent_id'],
                step_id=event_data['step_id'],
                data=event_data['data'],
                parent_event_id=event_data.get('parent_event_id'),
                metadata=event_data.get('metadata', {})
            )
            replay_events.append(event)
            
        self.mock_registry.set_replay_mode(replay_events)
        print(f"🎬 Replay mode enabled with {len(replay_events)} events")


# Convenience functions and decorators
def debug_agent(agent, mode: str = "console", **kwargs):
    """Convenience function to quickly debug an agent"""
    debugger = AgentDebugger(mode=mode, **kwargs)
    return debugger.attach(agent)


def breakpoint_on_tool(tool_name: str):
    """Decorator to create a breakpoint on specific tool usage"""
    def decorator(func):
        # This would be implemented based on the specific agent framework
        return func
    return decorator


# Example agent class for demonstration
class ExampleAgent:
    """Example agent implementation for testing the debugger"""
    
    def __init__(self, name: str, goal: str, tools: List[str]):
        self.name = name
        self.goal = goal
        self.tools = tools
        self.memory = {}
        
    def execute_tool(self, tool_name: str, query: str) -> str:
        """Mock tool execution"""
        if tool_name == "web_search":
            return f"Search results for: {query}"
        elif tool_name == "summarizer":
            return f"Summary of: {query}"
        else:
            return f"Tool {tool_name} executed with: {query}"
            
    def call_llm(self, prompt: str) -> str:
        """Mock LLM call"""
        return f"LLM response to: {prompt[:50]}..."
        
    def update_memory(self, key: str, value: Any):
        """Update agent memory"""
        self.memory[key] = value
        
    def run(self, task: str) -> str:
        """Run the agent on a task"""
        print(f"🤖 {self.name} starting task: {task}")
        
        # Simulate reasoning
        reasoning = self.call_llm(f"How should I approach: {task}")
        
        # Simulate tool usage
        if "web_search" in self.tools:
            search_results = self.execute_tool("web_search", task)
            self.update_memory("search_results", search_results)
            
        if "summarizer" in self.tools:
            summary = self.execute_tool("summarizer", task)
            self.update_memory("summary", summary)
            
        final_response = self.call_llm(f"Based on the results, provide final answer for: {task}")
        
        print(f"✅ {self.name} completed task")
        return final_response


if __name__ == "__main__":
    pass