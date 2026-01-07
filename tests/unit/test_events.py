"""
Unit tests for the event system and trace events.
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from agent_debugger import (
    Breakpoint,
    BreakpointType,
    EventType,
    TraceEvent,
)


class TestTraceEvent:
    """Test the TraceEvent class."""

    def test_trace_event_creation(self):
        """Test creating a trace event."""
        event = TraceEvent(
            event_type=EventType.TOOL_CALL,
            agent_id="test_agent",
            data={"tool": "web_search", "input": "test query"},
        )

        assert event.event_type == EventType.TOOL_CALL
        assert event.agent_id == "test_agent"
        assert event.data == {"tool": "web_search", "input": "test query"}
        assert event.parent_event_id is None
        assert isinstance(event.timestamp, datetime)
        assert event.id is not None

    def test_trace_event_with_parent(self):
        """Test creating a trace event with a parent."""
        parent_event = TraceEvent(
            event_type=EventType.AGENT_START, agent_id="test_agent", data={}
        )

        child_event = TraceEvent(
            event_type=EventType.TOOL_CALL,
            agent_id="test_agent",
            data={"tool": "web_search"},
            parent_event_id=parent_event.id,
        )

        assert child_event.parent_event_id == parent_event.id

    def test_trace_event_custom_timestamp(self):
        """Test creating a trace event with custom timestamp."""
        custom_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        event = TraceEvent(
            event_type=EventType.TOOL_CALL,
            agent_id="test_agent",
            data={},
            timestamp=custom_time,
        )

        assert event.timestamp == custom_time

    def test_trace_event_to_dict(self):
        """Test converting trace event to dictionary."""
        event = TraceEvent(
            event_type=EventType.TOOL_CALL,
            agent_id="test_agent",
            data={"tool": "web_search", "result": "success"},
        )

        event_dict = event.to_dict()

        assert event_dict["event_type"] == "tool_call"
        assert event_dict["agent_id"] == "test_agent"
        assert event_dict["data"] == {"tool": "web_search", "result": "success"}
        assert "timestamp" in event_dict
        assert "id" in event_dict

    def test_trace_event_from_dict(self):
        """Test creating trace event from dictionary."""
        event_dict = {
            "event_type": "tool_call",
            "agent_id": "test_agent",
            "data": {"tool": "web_search"},
            "timestamp": "2023-01-01T12:00:00Z",
            "id": "test-id",
        }

        event = TraceEvent.from_dict(event_dict)

        assert event.event_type == EventType.TOOL_CALL
        assert event.agent_id == "test_agent"
        assert event.data == {"tool": "web_search"}
        assert event.id == "test-id"

    def test_trace_event_string_representation(self):
        """Test string representation of trace event."""
        event = TraceEvent(
            event_type=EventType.TOOL_CALL,
            agent_id="test_agent",
            data={"tool": "web_search"},
        )

        str_repr = str(event)
        assert "TraceEvent" in str_repr
        assert "tool_call" in str_repr
        assert "test_agent" in str_repr

    def test_event_type_enum_values(self):
        """Test that EventType enum has expected values."""
        expected_types = [
            "agent_start",
            "agent_end",
            "tool_call",
            "tool_result",
            "memory_read",
            "memory_write",
            "reasoning_step",
            "error",
            "breakpoint_hit",
            "user_input",
            "before_tool_execution",
            "after_tool_execution",
            "state_change",
            "performance_metric",
            "custom",
        ]

        for event_type in expected_types:
            assert hasattr(EventType, event_type.upper())

    def test_event_type_string_conversion(self):
        """Test converting EventType to string."""
        assert str(EventType.TOOL_CALL) == "tool_call"
        assert str(EventType.AGENT_START) == "agent_start"
        assert str(EventType.ERROR) == "error"


class TestBreakpoint:
    """Test the Breakpoint class."""

    def test_breakpoint_creation_simple(self):
        """Test creating a simple breakpoint."""
        breakpoint = Breakpoint(breakpoint_type=BreakpointType.BEFORE_TOOL)

        assert breakpoint.breakpoint_type == BreakpointType.BEFORE_TOOL
        assert breakpoint.condition is None
        assert breakpoint.tool_name is None
        assert breakpoint.enabled is True

    def test_breakpoint_creation_with_tool(self):
        """Test creating a breakpoint for a specific tool."""
        breakpoint = Breakpoint(
            breakpoint_type=BreakpointType.BEFORE_TOOL, tool_name="web_search"
        )

        assert breakpoint.breakpoint_type == BreakpointType.BEFORE_TOOL
        assert breakpoint.tool_name == "web_search"

    def test_breakpoint_creation_with_condition(self):
        """Test creating a breakpoint with a condition."""

        def error_condition(event):
            return "error" in str(event.data).lower()

        breakpoint = Breakpoint(
            breakpoint_type=BreakpointType.CONDITIONAL, condition=error_condition
        )

        assert breakpoint.breakpoint_type == BreakpointType.CONDITIONAL
        assert breakpoint.condition == error_condition

    def test_breakpoint_creation_disabled(self):
        """Test creating a disabled breakpoint."""
        breakpoint = Breakpoint(
            breakpoint_type=BreakpointType.BEFORE_TOOL, enabled=False
        )

        assert breakpoint.enabled is False

    def test_matches_event_before_tool(self):
        """Test breakpoint matching for BEFORE_TOOL events."""
        breakpoint = Breakpoint(
            breakpoint_type=BreakpointType.BEFORE_TOOL, tool_name="web_search"
        )

        # Matching event
        event = TraceEvent(
            event_type=EventType.BEFORE_TOOL_EXECUTION,
            agent_id="test_agent",
            data={"tool_name": "web_search"},
        )
        assert breakpoint.matches_event(event) is True

        # Non-matching event (wrong tool)
        event2 = TraceEvent(
            event_type=EventType.BEFORE_TOOL_EXECUTION,
            agent_id="test_agent",
            data={"tool_name": "file_read"},
        )
        assert breakpoint.matches_event(event2) is False

        # Non-matching event (wrong type)
        event3 = TraceEvent(
            event_type=EventType.TOOL_CALL,
            agent_id="test_agent",
            data={"tool_name": "web_search"},
        )
        assert breakpoint.matches_event(event3) is False

    def test_matches_event_after_tool(self):
        """Test breakpoint matching for AFTER_TOOL events."""
        breakpoint = Breakpoint(breakpoint_type=BreakpointType.AFTER_TOOL)

        event = TraceEvent(
            event_type=EventType.AFTER_TOOL_EXECUTION,
            agent_id="test_agent",
            data={"tool_name": "web_search", "result": "success"},
        )
        assert breakpoint.matches_event(event) is True

    def test_matches_event_on_error(self):
        """Test breakpoint matching for ERROR events."""
        breakpoint = Breakpoint(breakpoint_type=BreakpointType.ON_ERROR)

        event = TraceEvent(
            event_type=EventType.ERROR,
            agent_id="test_agent",
            data={"error": "Something went wrong"},
        )
        assert breakpoint.matches_event(event) is True

    def test_matches_event_conditional(self):
        """Test breakpoint matching for conditional breakpoints."""

        def has_error_data(event):
            return "error" in event.data.get("message", "").lower()

        breakpoint = Breakpoint(
            breakpoint_type=BreakpointType.CONDITIONAL, condition=has_error_data
        )

        # Matching event
        event1 = TraceEvent(
            event_type=EventType.TOOL_RESULT,
            agent_id="test_agent",
            data={"message": "An error occurred"},
        )
        assert breakpoint.matches_event(event1) is True

        # Non-matching event
        event2 = TraceEvent(
            event_type=EventType.TOOL_RESULT,
            agent_id="test_agent",
            data={"message": "Success"},
        )
        assert breakpoint.matches_event(event2) is False

    def test_matches_event_disabled(self):
        """Test that disabled breakpoints don't match."""
        breakpoint = Breakpoint(
            breakpoint_type=BreakpointType.BEFORE_TOOL, enabled=False
        )

        event = TraceEvent(
            event_type=EventType.BEFORE_TOOL_EXECUTION,
            agent_id="test_agent",
            data={"tool_name": "web_search"},
        )
        assert breakpoint.matches_event(event) is False

    def test_enable_disable_breakpoint(self):
        """Test enabling and disabling breakpoints."""
        breakpoint = Breakpoint(breakpoint_type=BreakpointType.BEFORE_TOOL)

        assert breakpoint.enabled is True

        breakpoint.disable()
        assert breakpoint.enabled is False

        breakpoint.enable()
        assert breakpoint.enabled is True

    def test_breakpoint_string_representation(self):
        """Test string representation of breakpoint."""
        breakpoint = Breakpoint(
            breakpoint_type=BreakpointType.BEFORE_TOOL, tool_name="web_search"
        )

        str_repr = str(breakpoint)
        assert "Breakpoint" in str_repr
        assert "before_tool" in str_repr
        assert "web_search" in str_repr

    def test_breakpoint_equality(self):
        """Test breakpoint equality comparison."""
        bp1 = Breakpoint(
            breakpoint_type=BreakpointType.BEFORE_TOOL, tool_name="web_search"
        )
        bp2 = Breakpoint(
            breakpoint_type=BreakpointType.BEFORE_TOOL, tool_name="web_search"
        )
        bp3 = Breakpoint(
            breakpoint_type=BreakpointType.AFTER_TOOL, tool_name="web_search"
        )

        assert bp1 == bp2
        assert bp1 != bp3

    def test_breakpoint_type_enum_values(self):
        """Test that BreakpointType enum has expected values."""
        expected_types = [
            "before_tool",
            "after_tool",
            "on_error",
            "on_memory_write",
            "on_state_change",
            "conditional",
        ]

        for bp_type in expected_types:
            assert hasattr(BreakpointType, bp_type.upper())

    def test_breakpoint_type_string_conversion(self):
        """Test converting BreakpointType to string."""
        assert str(BreakpointType.BEFORE_TOOL) == "before_tool"
        assert str(BreakpointType.ON_ERROR) == "on_error"
        assert str(BreakpointType.CONDITIONAL) == "conditional"
