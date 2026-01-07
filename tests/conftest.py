"""
Shared test fixtures and configuration for agentdebugger tests.
"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent_debugger import (
    AgentDebugger,
    EventType,
    BreakpointType,
    TraceEvent,
    Breakpoint,
    AgentState,
    MockRegistry,
    PerformanceMonitor,
    DebugConsole,
)


@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    agent = Mock()
    agent.name = "TestAgent"
    agent.run = Mock(return_value="Test result")
    agent.get_state = Mock(return_value={"memory": {}, "tools": []})
    return agent


@pytest.fixture
def debugger():
    """Create a debugger instance for testing."""
    return AgentDebugger(mode="headless")


@pytest.fixture
def mock_registry():
    """Create a mock registry for testing."""
    return MockRegistry()


@pytest.fixture
def performance_monitor():
    """Create a performance monitor for testing."""
    return PerformanceMonitor()


@pytest.fixture
def debug_console():
    """Create a debug console for testing."""
    return DebugConsole()


@pytest.fixture
def sample_trace_event():
    """Create a sample trace event for testing."""
    return TraceEvent(
        event_type=EventType.TOOL_CALL,
        agent_id="test_agent",
        data={
            "tool_name": "web_search",
            "input": "test query",
            "output": "test result"
        }
    )


@pytest.fixture
def sample_breakpoint():
    """Create a sample breakpoint for testing."""
    return Breakpoint(
        breakpoint_type=BreakpointType.BEFORE_TOOL,
        tool_name="web_search"
    )


@pytest.fixture
def agent_state():
    """Create a sample agent state for testing."""
    return AgentState(
        agent_id="test_agent",
        memory={"key": "value"},
        tools=["web_search", "file_read"],
        current_task="Test task"
    )


@pytest.fixture
def mock_langchain_agent():
    """Create a mock LangChain agent for testing."""
    agent = Mock()
    agent.name = "LangChainAgent"
    agent.run = Mock(return_value="LangChain result")
    agent.get_chain = Mock(return_value=Mock())
    agent.memory = Mock()
    agent.tools = [Mock(), Mock()]
    return agent


@pytest.fixture
def mock_crewai_agent():
    """Create a mock CrewAI agent for testing."""
    agent = Mock()
    agent.name = "CrewAIAgent"
    agent.execute_task = Mock(return_value="CrewAI result")
    agent.role = "Researcher"
    agent.goal = "Gather information"
    return agent


@pytest.fixture
def mock_autogpt_agent():
    """Create a mock AutoGPT agent for testing."""
    agent = Mock()
    agent.name = "AutoGPTAgent"
    agent.run = Mock(return_value="AutoGPT result")
    agent.memory = Mock()
    agent.commands = ["web_search", "file_operations"]
    return agent


@pytest.fixture
def mock_llamaindex_agent():
    """Create a mock LlamaIndex agent for testing."""
    agent = Mock()
    agent.name = "LlamaIndexAgent"
    agent.query = Mock(return_value="LlamaIndex result")
    agent.index = Mock()
    agent.chat_engine = Mock()
    return agent


@pytest.fixture
def mock_huggingface_agent():
    """Create a mock HuggingFace agent for testing."""
    agent = Mock()
    agent.name = "HuggingFaceAgent"
    agent.run = Mock(return_value="HuggingFace result")
    agent.pipeline = Mock()
    agent.model = Mock()
    return agent
