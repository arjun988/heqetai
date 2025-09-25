"""
Interactive console for AgentDebugger.
"""

from typing import Any

from .events import TraceEvent, EventType, Breakpoint, BreakpointType
from .state import AgentState


class DebugConsole:
    """Interactive debugging console similar to pdb"""

    def __init__(self, debugger: Any):
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
        print("Continuing to next step...")
        state.is_paused = False

    def _step_into(self, event: TraceEvent, state: AgentState):
        print("Stepping into sub-execution...")
        state.is_paused = False

    def _continue(self, event: TraceEvent, state: AgentState):
        print("Continuing execution...")
        state.is_paused = False

    def _show_memory(self, event: TraceEvent, state: AgentState):
        print("\n📚 Memory State:")
        for key, value in state.memory.items():
            print(f"  {key}: {value}")

    def _edit_next(self, event: TraceEvent, state: AgentState):
        if event.event_type == EventType.TOOL_CALL_START:
            print(f"Current tool call: {event.data}")
            new_input = input("Enter new input (or press Enter to keep current): ")
            if new_input.strip():
                event.data['input'] = new_input
                print("Tool input updated!")
        else:
            print("No editable operation at current step")

    def _override_output(self, event: TraceEvent, state: AgentState):
        tool_name = input("Tool name to override: ")
        output = input("Override output: ")
        self.debugger.mock_registry.mock_tool(tool_name, output)
        print(f"Tool '{tool_name}' output overridden!")

    def _set_breakpoint(self, event: TraceEvent, state: AgentState):
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
        print("\n🔴 Active Breakpoints:")
        for bp in self.debugger.breakpoints:
            status = "✓" if bp.enabled else "✗"
            print(f"  {status} {bp.id}: {bp.breakpoint_type.value} (hits: {bp.hit_count})")

    def _show_trace(self, event: TraceEvent, state: AgentState):
        print("\n📊 Execution Trace:")
        for trace_event in self.debugger.trace_events[-10:]:
            duration = f" ({trace_event.duration:.2f}s)" if trace_event.duration else ""
            print(f"  [{trace_event.timestamp.strftime('%H:%M:%S')}{duration}] {trace_event.agent_id} - {trace_event.event_type.value}")

    def _show_state(self, event: TraceEvent, state: AgentState):
        print(f"\n🤖 Agent State:")
        print(f"  ID: {state.agent_id}")
        print(f"  Current Step: {state.current_step}")
        print(f"  Execution Stack: {state.execution_stack}")
        print(f"  Memory Keys: {list(state.memory.keys())}")
        print(f"  Tool Outputs: {list(state.tool_outputs.keys())}")
        print(f"  Tasks Completed: {state.tasks_completed}")
        print(f"  Errors: {state.errors_encountered}")

    def _performance(self, event: TraceEvent, state: AgentState):
        stats = self.debugger.performance_monitor.get_statistics()
        print("\n📈 Performance Metrics:")
        for metric, values in stats.items():
            if values['count'] > 0:
                print(f"  {metric}: {values['mean']:.3f}s avg ({values['count']} samples)")

    def _watch_variable(self, event: TraceEvent, state: AgentState, variable_name: str = ""):
        if not variable_name:
            variable_name = input("Variable name to watch: ")

        def watch_condition(evt: TraceEvent) -> bool:
            return (evt.event_type == EventType.MEMORY_WRITE and evt.data.get('key') == variable_name)

        bp = Breakpoint(
            breakpoint_type=BreakpointType.CONDITIONAL,
            condition=watch_condition,
            temporary=True
        )
        self.debugger.add_breakpoint(bp)
        print(f"👀 Watching variable '{variable_name}' for changes")

    def _mock_tool(self, event: TraceEvent, state: AgentState, tool_name: str = ""):
        if not tool_name:
            tool_name = input("Tool name to mock: ")
        output = input(f"Mock output for {tool_name}: ")
        self.debugger.mock_registry.mock_tool(tool_name, output)
        print(f"🎭 Tool '{tool_name}' mocked with output: {output}")

    def _replay_trace(self, event: TraceEvent, state: AgentState):
        filename = input("Trace file to replay: ")
        try:
            self.debugger.replay_from_file(filename)
            print(f"🎬 Replay mode activated with {filename}")
        except Exception as e:
            print(f"❌ Failed to replay: {e}")

    def _export_trace(self, event: TraceEvent, state: AgentState):
        filename = input("Export filename: ")
        self.debugger.export_trace(filename)

    def _list_agents(self, event: TraceEvent, state: AgentState):
        print("\n🤖 Registered Agents:")
        for agent_id, agent_state in self.debugger.agent_states.items():
            status = "⏸️" if agent_state.is_paused else "▶️"
            print(f"  {status} {agent_id} (tasks: {agent_state.tasks_completed}, errors: {agent_state.errors_encountered})")

    def _help(self, event: TraceEvent, state: AgentState):
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
        print("Quitting debugger...")
        self.debugger._console_quit = True
        state.is_paused = False


