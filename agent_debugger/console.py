"""
Interactive console for AgentDebugger.
"""

from typing import Any

from .context import ContextType, ContextPriority
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
            'agents': self._list_agents,
            'ctx': self._context_management,
            'context': self._context_management,
            'add_ctx': self._add_context,
            'search_ctx': self._search_contexts,
            'list_ctx': self._list_contexts,
            'clear_ctx': self._clear_contexts,
            'export_ctx': self._export_contexts,
            'import_ctx': self._import_contexts
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
                elif command.startswith('add_ctx '):
                    self._add_context(current_event, agent_state, command[8:])
                elif command.startswith('search_ctx '):
                    self._search_contexts(current_event, agent_state, command[11:])
                elif command.startswith('clear_ctx '):
                    self._clear_contexts(current_event, agent_state, command[10:])
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

    def _context_management(self, event: TraceEvent, state: AgentState):
        """Context management main menu"""
        if not self.debugger.context_manager:
            print("❌ Context management is not enabled")
            return
        
        print("""
🧠 Context Management:
  add_ctx     - Add new context item
  search_ctx  - Search contexts
  list_ctx    - List all contexts
  clear_ctx   - Clear contexts
  export_ctx  - Export contexts
  import_ctx  - Import contexts
  ctx summary - Show context summary
        """)
    
    def _add_context(self, event: TraceEvent, state: AgentState, args: str = ""):
        """Add a new context item"""
        if not self.debugger.context_manager:
            print("❌ Context management is not enabled")
            return
        
        try:
            print("Adding new context item...")
            
            # Get context type
            print("Available types: memory, conversation, knowledge, task, environment, user_preference, system_state")
            type_str = input("Context type: ").strip()
            context_type = ContextType(type_str)
            
            # Get key and value
            key = input("Context key: ").strip()
            value = input("Context value: ").strip()
            
            # Get priority
            print("Available priorities: critical, high, medium, low, archive")
            priority_str = input("Priority (default: medium): ").strip() or "medium"
            priority = ContextPriority(priority_str)
            
            # Get optional fields
            tags_input = input("Tags (comma-separated, optional): ").strip()
            tags = [tag.strip() for tag in tags_input.split(',')] if tags_input else []
            
            agent_id = input(f"Agent ID (optional, current: {event.agent_id}): ").strip() or event.agent_id
            step_id = input(f"Step ID (optional, current: {event.step_id}): ").strip() or event.step_id
            
            # Add context
            context_id = self.debugger.add_context(
                type=context_type,
                key=key,
                value=value,
                priority=priority,
                tags=tags,
                agent_id=agent_id,
                step_id=step_id
            )
            
            print(f"✅ Context added with ID: {context_id}")
            
        except ValueError as e:
            print(f"❌ Invalid input: {e}")
        except Exception as e:
            print(f"❌ Error adding context: {e}")
    
    def _search_contexts(self, event: TraceEvent, state: AgentState, query: str = ""):
        """Search contexts"""
        if not self.debugger.context_manager:
            print("❌ Context management is not enabled")
            return
        
        if not query:
            query = input("Search query: ").strip()
        
        if not query:
            print("❌ Search query cannot be empty")
            return
        
        try:
            contexts = self.debugger.search_contexts(query)
            
            if not contexts:
                print("🔍 No contexts found matching query")
                return
            
            print(f"🔍 Found {len(contexts)} contexts:")
            for ctx in contexts[:10]:  # Show first 10 results
                print(f"  {ctx.id}: {ctx.key} ({ctx.type.value}, {ctx.priority.value})")
                print(f"    Value: {str(ctx.value)[:100]}{'...' if len(str(ctx.value)) > 100 else ''}")
                print(f"    Agent: {ctx.agent_id}, Created: {ctx.created_at}")
                print()
            
            if len(contexts) > 10:
                print(f"... and {len(contexts) - 10} more results")
                
        except Exception as e:
            print(f"❌ Error searching contexts: {e}")
    
    def _list_contexts(self, event: TraceEvent, state: AgentState):
        """List all contexts"""
        if not self.debugger.context_manager:
            print("❌ Context management is not enabled")
            return
        
        try:
            summary = self.debugger.get_context_summary()
            print(f"\n📊 Context Summary:")
            print(f"  Total items: {summary.get('total_items', 0)}")
            print(f"  By type: {summary.get('by_type', {})}")
            print(f"  By priority: {summary.get('by_priority', {})}")
            print(f"  Expired: {summary.get('expired_count', 0)}")
            
            # Get all contexts
            contexts = self.debugger.search_contexts("")
            
            if not contexts:
                print("\n📝 No contexts found")
                return
            
            print(f"\n📝 All Contexts ({len(contexts)}):")
            for ctx in contexts:
                print(f"  {ctx.id}: {ctx.key}")
                print(f"    Type: {ctx.type.value}, Priority: {ctx.priority.value}")
                print(f"    Agent: {ctx.agent_id}, Created: {ctx.created_at}")
                print(f"    Value: {str(ctx.value)[:50]}{'...' if len(str(ctx.value)) > 50 else ''}")
                if ctx.tags:
                    print(f"    Tags: {', '.join(ctx.tags)}")
                print()
                
        except Exception as e:
            print(f"❌ Error listing contexts: {e}")
    
    def _clear_contexts(self, event: TraceEvent, state: AgentState, args: str = ""):
        """Clear contexts with optional filters"""
        if not self.debugger.context_manager:
            print("❌ Context management is not enabled")
            return
        
        try:
            print("Clear contexts with filters:")
            type_filter = input("Type filter (optional): ").strip()
            agent_filter = input("Agent filter (optional): ").strip()
            tag_filter = input("Tag filter (comma-separated, optional): ").strip()
            
            # Convert filters
            type_enum = ContextType(type_filter) if type_filter else None
            tags = [tag.strip() for tag in tag_filter.split(',')] if tag_filter else None
            
            if not type_filter and not agent_filter and not tag_filter:
                confirm = input("Clear ALL contexts? This cannot be undone! (yes/no): ").strip().lower()
                if confirm != 'yes':
                    print("❌ Clear cancelled")
                    return
            
            cleared_count = self.debugger.clear_contexts(
                type_filter=type_enum,
                agent_filter=agent_filter,
                tag_filter=tags
            )
            
            print(f"✅ Cleared {cleared_count} contexts")
            
        except ValueError as e:
            print(f"❌ Invalid filter: {e}")
        except Exception as e:
            print(f"❌ Error clearing contexts: {e}")
    
    def _export_contexts(self, event: TraceEvent, state: AgentState):
        """Export contexts to file"""
        if not self.debugger.context_manager:
            print("❌ Context management is not enabled")
            return
        
        try:
            filename = input("Export filename: ").strip()
            if not filename:
                filename = f"contexts_export_{event.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            
            format_type = input("Format (json/csv, default: json): ").strip() or "json"
            
            exported_data = self.debugger.export_contexts(format=format_type)
            
            with open(filename, 'w') as f:
                f.write(exported_data)
            
            print(f"✅ Contexts exported to {filename}")
            
        except Exception as e:
            print(f"❌ Error exporting contexts: {e}")
    
    def _import_contexts(self, event: TraceEvent, state: AgentState):
        """Import contexts from file"""
        if not self.debugger.context_manager:
            print("❌ Context management is not enabled")
            return
        
        try:
            filename = input("Import filename: ").strip()
            if not filename:
                print("❌ Filename required")
                return
            
            format_type = input("Format (json/csv, default: json): ").strip() or "json"
            
            with open(filename, 'r') as f:
                data = f.read()
            
            imported_count = self.debugger.import_contexts(data, format_type)
            print(f"✅ Imported {imported_count} contexts from {filename}")
            
        except FileNotFoundError:
            print(f"❌ File not found: {filename}")
        except Exception as e:
            print(f"❌ Error importing contexts: {e}")

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
  
🧠 Context Management:
  ctx, context - Context management menu
  add_ctx     - Add new context item
  search_ctx <query> - Search contexts
  list_ctx    - List all contexts
  clear_ctx   - Clear contexts with filters
  export_ctx  - Export contexts to file
  import_ctx  - Import contexts from file
  
  h, help     - Show this help
  q, quit     - Quit debugger
        """)

    def _quit(self, event: TraceEvent, state: AgentState):
        print("Quitting debugger...")
        self.debugger._console_quit = True
        state.is_paused = False


