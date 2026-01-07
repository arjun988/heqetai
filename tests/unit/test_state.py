"""
Unit tests for the agent state management.
"""
import pytest
from datetime import datetime

from agent_debugger import AgentState


class TestAgentState:
    """Test the AgentState class."""

    def test_agent_state_creation(self):
        """Test creating an agent state."""
        state = AgentState(
            agent_id="test_agent",
            memory={"key": "value"},
            tools=["web_search", "file_read"],
            current_task="Test task"
        )

        assert state.agent_id == "test_agent"
        assert state.memory == {"key": "value"}
        assert state.tools == ["web_search", "file_read"]
        assert state.current_task == "Test task"
        assert isinstance(state.timestamp, datetime)

    def test_agent_state_creation_minimal(self):
        """Test creating an agent state with minimal data."""
        state = AgentState(agent_id="test_agent")

        assert state.agent_id == "test_agent"
        assert state.memory == {}
        assert state.tools == []
        assert state.current_task is None

    def test_agent_state_update_memory(self):
        """Test updating agent memory."""
        state = AgentState(agent_id="test_agent")

        state.update_memory("new_key", "new_value")
        assert state.memory["new_key"] == "new_value"

        # Update existing key
        state.update_memory("new_key", "updated_value")
        assert state.memory["new_key"] == "updated_value"

    def test_agent_state_add_tool(self):
        """Test adding tools to agent state."""
        state = AgentState(agent_id="test_agent")

        state.add_tool("web_search")
        assert "web_search" in state.tools

        # Add duplicate tool (should not duplicate)
        state.add_tool("web_search")
        assert state.tools.count("web_search") == 1

    def test_agent_state_remove_tool(self):
        """Test removing tools from agent state."""
        state = AgentState(
            agent_id="test_agent",
            tools=["web_search", "file_read", "calculator"]
        )

        state.remove_tool("file_read")
        assert "file_read" not in state.tools
        assert len(state.tools) == 2

        # Remove non-existent tool (should not error)
        state.remove_tool("nonexistent")
        assert len(state.tools) == 2

    def test_agent_state_set_current_task(self):
        """Test setting the current task."""
        state = AgentState(agent_id="test_agent")

        state.set_current_task("New task")
        assert state.current_task == "New task"

    def test_agent_state_clear_memory(self):
        """Test clearing agent memory."""
        state = AgentState(
            agent_id="test_agent",
            memory={"key1": "value1", "key2": "value2"}
        )

        state.clear_memory()
        assert state.memory == {}

    def test_agent_state_clear_tools(self):
        """Test clearing agent tools."""
        state = AgentState(
            agent_id="test_agent",
            tools=["web_search", "file_read"]
        )

        state.clear_tools()
        assert state.tools == []

    def test_agent_state_to_dict(self):
        """Test converting agent state to dictionary."""
        state = AgentState(
            agent_id="test_agent",
            memory={"key": "value"},
            tools=["web_search"],
            current_task="Test task"
        )

        state_dict = state.to_dict()

        assert state_dict["agent_id"] == "test_agent"
        assert state_dict["memory"] == {"key": "value"}
        assert state_dict["tools"] == ["web_search"]
        assert state_dict["current_task"] == "Test task"
        assert "timestamp" in state_dict

    def test_agent_state_from_dict(self):
        """Test creating agent state from dictionary."""
        state_dict = {
            "agent_id": "test_agent",
            "memory": {"key": "value"},
            "tools": ["web_search"],
            "current_task": "Test task",
            "timestamp": "2023-01-01T12:00:00Z"
        }

        state = AgentState.from_dict(state_dict)

        assert state.agent_id == "test_agent"
        assert state.memory == {"key": "value"}
        assert state.tools == ["web_search"]
        assert state.current_task == "Test task"

    def test_agent_state_copy(self):
        """Test creating a copy of agent state."""
        original = AgentState(
            agent_id="test_agent",
            memory={"key": "value"},
            tools=["web_search"],
            current_task="Test task"
        )

        copy_state = original.copy()

        assert copy_state.agent_id == original.agent_id
        assert copy_state.memory == original.memory
        assert copy_state.tools == original.tools
        assert copy_state.current_task == original.current_task

        # Modifying copy shouldn't affect original
        copy_state.update_memory("new_key", "new_value")
        assert "new_key" not in original.memory
        assert "new_key" in copy_state.memory

    def test_agent_state_equality(self):
        """Test agent state equality comparison."""
        state1 = AgentState(
            agent_id="test_agent",
            memory={"key": "value"},
            tools=["web_search"]
        )

        state2 = AgentState(
            agent_id="test_agent",
            memory={"key": "value"},
            tools=["web_search"]
        )

        state3 = AgentState(
            agent_id="different_agent",
            memory={"key": "value"},
            tools=["web_search"]
        )

        assert state1 == state2
        assert state1 != state3

    def test_agent_state_string_representation(self):
        """Test string representation of agent state."""
        state = AgentState(
            agent_id="test_agent",
            memory={"key": "value"},
            tools=["web_search", "file_read"],
            current_task="Test task"
        )

        str_repr = str(state)
        assert "AgentState" in str_repr
        assert "test_agent" in str_repr
        assert "Test task" in str_repr

    def test_agent_state_has_tool(self):
        """Test checking if agent has a specific tool."""
        state = AgentState(
            agent_id="test_agent",
            tools=["web_search", "file_read"]
        )

        assert state.has_tool("web_search") is True
        assert state.has_tool("calculator") is False

    def test_agent_state_get_memory_value(self):
        """Test getting a value from memory."""
        state = AgentState(
            agent_id="test_agent",
            memory={"key1": "value1", "key2": "value2"}
        )

        assert state.get_memory_value("key1") == "value1"
        assert state.get_memory_value("nonexistent") is None
        assert state.get_memory_value("nonexistent", "default") == "default"

    def test_agent_state_memory_size(self):
        """Test getting memory size."""
        state = AgentState(
            agent_id="test_agent",
            memory={"key1": "value1", "key2": "value2", "key3": "value3"}
        )

        assert state.memory_size() == 3

        state.clear_memory()
        assert state.memory_size() == 0

    def test_agent_state_tool_count(self):
        """Test getting tool count."""
        state = AgentState(
            agent_id="test_agent",
            tools=["web_search", "file_read", "calculator"]
        )

        assert state.tool_count() == 3

        state.clear_tools()
        assert state.tool_count() == 0

    def test_agent_state_is_empty(self):
        """Test checking if agent state is empty."""
        empty_state = AgentState(agent_id="test_agent")
        assert empty_state.is_empty() is True

        non_empty_state = AgentState(
            agent_id="test_agent",
            memory={"key": "value"}
        )
        assert non_empty_state.is_empty() is False

        non_empty_state2 = AgentState(
            agent_id="test_agent",
            tools=["web_search"]
        )
        assert non_empty_state2.is_empty() is False

    def test_agent_state_merge(self):
        """Test merging two agent states."""
        state1 = AgentState(
            agent_id="test_agent",
            memory={"key1": "value1", "shared": "old_value"},
            tools=["web_search"]
        )

        state2 = AgentState(
            agent_id="test_agent",
            memory={"key2": "value2", "shared": "new_value"},
            tools=["file_read"]
        )

        merged = state1.merge(state2)

        assert merged.agent_id == "test_agent"
        assert merged.memory == {
            "key1": "value1",
            "key2": "value2",
            "shared": "new_value"  # state2 wins for conflicts
        }
        assert set(merged.tools) == {"web_search", "file_read"}

    def test_agent_state_diff(self):
        """Test getting the difference between two agent states."""
        state1 = AgentState(
            agent_id="test_agent",
            memory={"key1": "value1", "shared": "same"},
            tools=["web_search", "file_read"]
        )

        state2 = AgentState(
            agent_id="test_agent",
            memory={"key2": "value2", "shared": "same"},
            tools=["web_search", "calculator"]
        )

        diff = state1.diff(state2)

        assert "memory" in diff
        assert "tools" in diff
        assert diff["memory"]["added"] == {"key2": "value2"}
        assert diff["memory"]["removed"] == {"key1": "value1"}
        assert diff["memory"]["changed"] == {}
        assert diff["tools"]["added"] == ["calculator"]
        assert diff["tools"]["removed"] == ["file_read"]
