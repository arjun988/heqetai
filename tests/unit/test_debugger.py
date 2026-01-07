"""
Unit tests for the core AgentDebugger functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from agent_debugger import (
    AgentDebugger,
    EventType,
    BreakpointType,
    TraceEvent,
    Breakpoint,
    AgentState,
)


class TestAgentDebugger:
    """Test the main AgentDebugger class."""

    def test_debugger_initialization(self):
        """Test debugger initialization with different modes."""
        debugger = AgentDebugger(mode="console")
        assert debugger.mode == "console"
        assert debugger.enable_replay is True
        assert debugger.max_trace_events == 10000
        assert debugger.auto_export is False
        assert debugger.export_path == "./traces/"
        assert len(debugger.breakpoints) == 0
        assert len(debugger.trace_events) == 0

    def test_debugger_initialization_custom_params(self):
        """Test debugger initialization with custom parameters."""
        debugger = AgentDebugger(
            mode="web",
            enable_replay=False,
            max_trace_events=5000,
            auto_export=True,
            export_path="/tmp/traces"
        )
        assert debugger.mode == "web"
        assert debugger.enable_replay is False
        assert debugger.max_trace_events == 5000
        assert debugger.auto_export is True
        assert debugger.export_path == "/tmp/traces"

    def test_attach_agent(self, debugger, mock_agent):
        """Test attaching an agent to the debugger."""
        attached_agent = debugger.attach(mock_agent)

        # Should return the original agent (for now)
        assert attached_agent == mock_agent

        # Should record the attachment
        assert len(debugger.attached_agents) == 1
        assert "mock" in debugger.attached_agents

    def test_attach_agent_with_custom_id(self, debugger, mock_agent):
        """Test attaching an agent with a custom ID."""
        attached_agent = debugger.attach(mock_agent, agent_id="custom_agent")

        assert attached_agent == mock_agent
        assert "custom_agent" in debugger.attached_agents

    def test_add_breakpoint(self, debugger):
        """Test adding breakpoints."""
        breakpoint = Breakpoint(breakpoint_type=BreakpointType.BEFORE_TOOL)
        debugger.add_breakpoint(breakpoint)

        assert len(debugger.breakpoints) == 1
        assert debugger.breakpoints[0] == breakpoint

    def test_remove_breakpoint(self, debugger):
        """Test removing breakpoints."""
        breakpoint1 = Breakpoint(breakpoint_type=BreakpointType.BEFORE_TOOL)
        breakpoint2 = Breakpoint(breakpoint_type=BreakpointType.AFTER_TOOL)

        debugger.add_breakpoint(breakpoint1)
        debugger.add_breakpoint(breakpoint2)

        assert len(debugger.breakpoints) == 2

        debugger.remove_breakpoint(breakpoint1)
        assert len(debugger.breakpoints) == 1
        assert breakpoint1 not in debugger.breakpoints

    def test_clear_breakpoints(self, debugger):
        """Test clearing all breakpoints."""
        debugger.add_breakpoint(Breakpoint(breakpoint_type=BreakpointType.BEFORE_TOOL))
        debugger.add_breakpoint(Breakpoint(breakpoint_type=BreakpointType.AFTER_TOOL))

        assert len(debugger.breakpoints) == 2

        debugger.clear_breakpoints()
        assert len(debugger.breakpoints) == 0

    def test_record_event(self, debugger):
        """Test recording trace events."""
        event = TraceEvent(
            event_type=EventType.TOOL_CALL,
            agent_id="test_agent",
            data={"tool": "web_search", "input": "test"}
        )

        debugger.record_event(event)

        assert len(debugger.trace_events) == 1
        assert debugger.trace_events[0] == event

    def test_record_event_buffer_limit(self):
        """Test that events are limited by buffer size."""
        debugger = AgentDebugger(max_trace_events=2)

        debugger.record_event(TraceEvent(EventType.TOOL_CALL, "agent1", {}))
        debugger.record_event(TraceEvent(EventType.TOOL_CALL, "agent1", {}))
        debugger.record_event(TraceEvent(EventType.TOOL_CALL, "agent1", {}))

        # Should only keep the last 2 events
        assert len(debugger.trace_events) == 2

    def test_get_trace_summary(self, debugger):
        """Test getting trace summary statistics."""
        # Add some events
        debugger.record_event(TraceEvent(EventType.TOOL_CALL, "agent1", {"tool": "search"}))
        debugger.record_event(TraceEvent(EventType.TOOL_CALL, "agent2", {"tool": "read"}))
        debugger.record_event(TraceEvent(EventType.MEMORY_WRITE, "agent1", {"key": "data"}))

        summary = debugger.get_trace_summary()

        assert summary["total_events"] == 3
        assert summary["agents"] == {"agent1", "agent2"}
        assert summary["event_types"][EventType.TOOL_CALL] == 2
        assert summary["event_types"][EventType.MEMORY_WRITE] == 1

    def test_export_trace_json(self, debugger, tmp_path):
        """Test exporting trace to JSON."""
        debugger.record_event(TraceEvent(EventType.TOOL_CALL, "agent1", {"test": "data"}))

        export_path = tmp_path / "trace.json"
        debugger.export_trace(str(export_path))

        assert export_path.exists()

        import json
        with open(export_path) as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]["event_type"] == "tool_call"
        assert data[0]["agent_id"] == "agent1"

    def test_export_trace_csv(self, debugger, tmp_path):
        """Test exporting trace to CSV."""
        debugger.record_event(TraceEvent(EventType.TOOL_CALL, "agent1", {"test": "data"}))

        export_path = tmp_path / "trace.csv"
        debugger.export_trace(str(export_path), format="csv")

        assert export_path.exists()

        with open(export_path) as f:
            content = f.read()

        assert "event_type,agent_id,timestamp,data" in content
        assert "tool_call,agent1," in content

    def test_clear_traces(self, debugger):
        """Test clearing trace events."""
        debugger.record_event(TraceEvent(EventType.TOOL_CALL, "agent1", {}))
        debugger.record_event(TraceEvent(EventType.TOOL_CALL, "agent1", {}))

        assert len(debugger.trace_events) == 2

        debugger.clear_traces()
        assert len(debugger.trace_events) == 0

    def test_clear_traces_keep_last(self, debugger):
        """Test clearing traces while keeping the last N events."""
        debugger.record_event(TraceEvent(EventType.TOOL_CALL, "agent1", {"id": 1}))
        debugger.record_event(TraceEvent(EventType.TOOL_CALL, "agent1", {"id": 2}))
        debugger.record_event(TraceEvent(EventType.TOOL_CALL, "agent1", {"id": 3}))

        debugger.clear_traces(keep_last=2)
        assert len(debugger.trace_events) == 2

        # Should keep the last 2 events
        event_ids = [event.data["id"] for event in debugger.trace_events]
        assert event_ids == [2, 3]

    def test_is_breakpoint_hit(self, debugger):
        """Test breakpoint hit detection."""
        # Add a breakpoint for tool calls
        breakpoint = Breakpoint(breakpoint_type=BreakpointType.BEFORE_TOOL, tool_name="web_search")
        debugger.add_breakpoint(breakpoint)

        # Create an event that should trigger the breakpoint
        event = TraceEvent(
            event_type=EventType.BEFORE_TOOL_EXECUTION,
            agent_id="agent1",
            data={"tool_name": "web_search"}
        )

        # Mock the condition check
        with patch.object(breakpoint, 'matches_event', return_value=True):
            assert debugger.is_breakpoint_hit(event) is True

    def test_is_breakpoint_hit_no_match(self, debugger):
        """Test breakpoint hit detection when no breakpoint matches."""
        breakpoint = Breakpoint(breakpoint_type=BreakpointType.BEFORE_TOOL, tool_name="web_search")
        debugger.add_breakpoint(breakpoint)

        event = TraceEvent(
            event_type=EventType.BEFORE_TOOL_EXECUTION,
            agent_id="agent1",
            data={"tool_name": "file_read"}  # Different tool
        )

        with patch.object(breakpoint, 'matches_event', return_value=False):
            assert debugger.is_breakpoint_hit(event) is False

    def test_pause_execution(self, debugger):
        """Test pausing execution at breakpoints."""
        debugger.pause_execution("Test breakpoint hit")

        # In headless mode, this should not block
        assert debugger.is_paused is True

    def test_resume_execution(self, debugger):
        """Test resuming execution."""
        debugger.pause_execution("Test")
        assert debugger.is_paused is True

        debugger.resume_execution()
        assert debugger.is_paused is False

    @patch('builtins.input', return_value='c')
    def test_wait_for_command_console_mode(self, mock_input):
        """Test waiting for user command in console mode."""
        debugger = AgentDebugger(mode="console")
        debugger.pause_execution("Test")

        # Should return the command
        command = debugger.wait_for_command()
        assert command == 'c'

    def test_get_agent_state(self, debugger, mock_agent):
        """Test getting agent state."""
        debugger.attach(mock_agent, "test_agent")

        state = debugger.get_agent_state("test_agent")
        assert state is not None
        assert state.agent_id == "test_agent"

    def test_get_agent_state_not_found(self, debugger):
        """Test getting agent state for non-existent agent."""
        state = debugger.get_agent_state("nonexistent")
        assert state is None

    def test_update_agent_state(self, debugger, mock_agent):
        """Test updating agent state."""
        debugger.attach(mock_agent, "test_agent")

        new_state = {"memory": {"new_key": "new_value"}, "tools": ["tool1"]}
        debugger.update_agent_state("test_agent", new_state)

        # Verify the state was updated
        state = debugger.get_agent_state("test_agent")
        assert state.memory == {"new_key": "new_value"}
        assert state.tools == ["tool1"]

    def test_list_agents(self, debugger, mock_agent):
        """Test listing attached agents."""
        debugger.attach(mock_agent, "agent1")
        debugger.attach(Mock(), "agent2")

        agents = debugger.list_agents()
        assert len(agents) == 2
        assert "agent1" in agents
        assert "agent2" in agents

    def test_enable_replay(self, debugger):
        """Test enabling replay functionality."""
        debugger.enable_replay = False
        debugger.enable_replay_feature()

        assert debugger.enable_replay is True

    def test_disable_replay(self, debugger):
        """Test disabling replay functionality."""
        debugger.enable_replay = True
        debugger.disable_replay_feature()

        assert debugger.enable_replay is False

    def test_set_max_trace_events(self, debugger):
        """Test setting maximum trace events."""
        debugger.set_max_trace_events(5000)
        assert debugger.max_trace_events == 5000

    def test_get_performance_stats(self, debugger, performance_monitor):
        """Test getting performance statistics."""
        debugger.performance_monitor = performance_monitor

        # Mock some performance data
        performance_monitor.get_stats = Mock(return_value={
            "total_events": 100,
            "avg_processing_time": 0.5,
            "memory_usage": "50MB"
        })

        stats = debugger.get_performance_stats()
        assert stats["total_events"] == 100
        assert stats["avg_processing_time"] == 0.5

    def test_enable_auto_export(self, debugger, tmp_path):
        """Test enabling auto export."""
        export_dir = tmp_path / "exports"
        debugger.enable_auto_export(str(export_dir))

        assert debugger.auto_export is True
        assert debugger.export_path == str(export_dir)

    def test_disable_auto_export(self, debugger):
        """Test disabling auto export."""
        debugger.enable_auto_export("/tmp/test")
        assert debugger.auto_export is True

        debugger.disable_auto_export()
        assert debugger.auto_export is False
