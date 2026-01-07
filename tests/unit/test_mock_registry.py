"""
Unit tests for the MockRegistry functionality.
"""
import pytest
from unittest.mock import Mock, patch

from agent_debugger import MockRegistry


class TestMockRegistry:
    """Test the MockRegistry class."""

    def test_mock_registry_initialization(self):
        """Test mock registry initialization."""
        registry = MockRegistry()

        assert len(registry.tool_mocks) == 0
        assert len(registry.llm_mocks) == 0
        assert registry.enabled is True

    def test_mock_tool(self):
        """Test mocking a tool."""
        registry = MockRegistry()

        # Mock a tool
        registry.mock_tool("web_search", "Mocked search results")

        assert "web_search" in registry.tool_mocks
        assert registry.tool_mocks["web_search"] == "Mocked search results"

    def test_mock_tool_with_function(self):
        """Test mocking a tool with a function."""
        registry = MockRegistry()

        def mock_search(query):
            return f"Mock result for: {query}"

        registry.mock_tool("web_search", mock_search)

        assert "web_search" in registry.tool_mocks
        assert callable(registry.tool_mocks["web_search"])

        # Test calling the mock function
        result = registry.tool_mocks["web_search"]("test query")
        assert result == "Mock result for: test query"

    def test_unmock_tool(self):
        """Test removing a tool mock."""
        registry = MockRegistry()

        registry.mock_tool("web_search", "Mocked results")
        assert "web_search" in registry.tool_mocks

        registry.unmock_tool("web_search")
        assert "web_search" not in registry.tool_mocks

    def test_unmock_tool_not_mocked(self):
        """Test removing a mock for a tool that isn't mocked."""
        registry = MockRegistry()

        # Should not raise an error
        registry.unmock_tool("nonexistent_tool")

    def test_get_tool_mock(self):
        """Test getting a tool mock."""
        registry = MockRegistry()

        registry.mock_tool("web_search", "Mocked results")

        mock = registry.get_tool_mock("web_search")
        assert mock == "Mocked results"

    def test_get_tool_mock_not_mocked(self):
        """Test getting a mock for a tool that isn't mocked."""
        registry = MockRegistry()

        mock = registry.get_tool_mock("nonexistent_tool")
        assert mock is None

    def test_is_tool_mocked(self):
        """Test checking if a tool is mocked."""
        registry = MockRegistry()

        assert registry.is_tool_mocked("web_search") is False

        registry.mock_tool("web_search", "Mocked results")
        assert registry.is_tool_mocked("web_search") is True

        registry.unmock_tool("web_search")
        assert registry.is_tool_mocked("web_search") is False

    def test_mock_llm(self):
        """Test mocking an LLM."""
        registry = MockRegistry()

        registry.mock_llm("summarize", "Mocked summary")

        assert "summarize" in registry.llm_mocks
        assert registry.llm_mocks["summarize"] == "Mocked summary"

    def test_mock_llm_with_function(self):
        """Test mocking an LLM with a function."""
        registry = MockRegistry()

        def mock_summarize(text):
            return f"Summary of: {text[:50]}..."

        registry.mock_llm("summarize", mock_summarize)

        assert "summarize" in registry.llm_mocks
        assert callable(registry.llm_mocks["summarize"])

        # Test calling the mock function
        result = registry.llm_mocks["summarize"]("This is a long text that should be summarized")
        assert result == "Summary of: This is a long text that should be summarized..."

    def test_unmock_llm(self):
        """Test removing an LLM mock."""
        registry = MockRegistry()

        registry.mock_llm("summarize", "Mocked summary")
        assert "summarize" in registry.llm_mocks

        registry.unmock_llm("summarize")
        assert "summarize" not in registry.llm_mocks

    def test_unmock_llm_not_mocked(self):
        """Test removing a mock for an LLM that isn't mocked."""
        registry = MockRegistry()

        # Should not raise an error
        registry.unmock_llm("nonexistent_llm")

    def test_get_llm_mock(self):
        """Test getting an LLM mock."""
        registry = MockRegistry()

        registry.mock_llm("summarize", "Mocked summary")

        mock = registry.get_llm_mock("summarize")
        assert mock == "Mocked summary"

    def test_get_llm_mock_not_mocked(self):
        """Test getting a mock for an LLM that isn't mocked."""
        registry = MockRegistry()

        mock = registry.get_llm_mock("nonexistent_llm")
        assert mock is None

    def test_is_llm_mocked(self):
        """Test checking if an LLM is mocked."""
        registry = MockRegistry()

        assert registry.is_llm_mocked("summarize") is False

        registry.mock_llm("summarize", "Mocked summary")
        assert registry.is_llm_mocked("summarize") is True

        registry.unmock_llm("summarize")
        assert registry.is_llm_mocked("summarize") is False

    def test_clear_all_mocks(self):
        """Test clearing all mocks."""
        registry = MockRegistry()

        registry.mock_tool("web_search", "Mocked search")
        registry.mock_tool("file_read", "Mocked file")
        registry.mock_llm("summarize", "Mocked summary")
        registry.mock_llm("translate", "Mocked translation")

        assert len(registry.tool_mocks) == 2
        assert len(registry.llm_mocks) == 2

        registry.clear_all_mocks()

        assert len(registry.tool_mocks) == 0
        assert len(registry.llm_mocks) == 0

    def test_clear_tool_mocks(self):
        """Test clearing only tool mocks."""
        registry = MockRegistry()

        registry.mock_tool("web_search", "Mocked search")
        registry.mock_llm("summarize", "Mocked summary")

        registry.clear_tool_mocks()

        assert len(registry.tool_mocks) == 0
        assert len(registry.llm_mocks) == 1

    def test_clear_llm_mocks(self):
        """Test clearing only LLM mocks."""
        registry = MockRegistry()

        registry.mock_tool("web_search", "Mocked search")
        registry.mock_llm("summarize", "Mocked summary")

        registry.clear_llm_mocks()

        assert len(registry.tool_mocks) == 1
        assert len(registry.llm_mocks) == 0

    def test_enable_disable_registry(self):
        """Test enabling and disabling the registry."""
        registry = MockRegistry()

        assert registry.enabled is True

        registry.disable()
        assert registry.enabled is False

        registry.enable()
        assert registry.enabled is True

    def test_get_mocked_tools_list(self):
        """Test getting list of mocked tools."""
        registry = MockRegistry()

        registry.mock_tool("web_search", "Mocked search")
        registry.mock_tool("file_read", "Mocked file")

        mocked_tools = registry.get_mocked_tools()
        assert set(mocked_tools) == {"web_search", "file_read"}

    def test_get_mocked_llms_list(self):
        """Test getting list of mocked LLMs."""
        registry = MockRegistry()

        registry.mock_llm("summarize", "Mocked summary")
        registry.mock_llm("translate", "Mocked translation")

        mocked_llms = registry.get_mocked_llms()
        assert set(mocked_llms) == {"summarize", "translate"}

    def test_registry_string_representation(self):
        """Test string representation of mock registry."""
        registry = MockRegistry()

        registry.mock_tool("web_search", "Mocked search")
        registry.mock_llm("summarize", "Mocked summary")

        str_repr = str(registry)
        assert "MockRegistry" in str_repr
        assert "2 tool mocks" in str_repr
        assert "2 LLM mocks" in str_repr

    def test_registry_disabled_behavior(self):
        """Test registry behavior when disabled."""
        registry = MockRegistry()
        registry.disable()

        # Mocks should still be stored but not returned when disabled
        registry.mock_tool("web_search", "Mocked search")

        # When disabled, get_tool_mock should return None
        assert registry.get_tool_mock("web_search") is None
        assert registry.is_tool_mocked("web_search") is False

    def test_mock_with_callable_returning_none(self):
        """Test mocking with a callable that returns None."""
        registry = MockRegistry()

        def mock_function_returns_none():
            return None

        registry.mock_tool("web_search", mock_function_returns_none)

        result = registry.get_tool_mock("web_search")()
        assert result is None

    def test_multiple_mocks_same_tool(self):
        """Test that multiple mocks for the same tool override previous ones."""
        registry = MockRegistry()

        registry.mock_tool("web_search", "First mock")
        assert registry.get_tool_mock("web_search") == "First mock"

        registry.mock_tool("web_search", "Second mock")
        assert registry.get_tool_mock("web_search") == "Second mock"

    def test_mock_with_complex_data(self):
        """Test mocking with complex data structures."""
        registry = MockRegistry()

        complex_mock = {
            "results": [
                {"title": "Result 1", "url": "http://example.com/1"},
                {"title": "Result 2", "url": "http://example.com/2"}
            ],
            "total_count": 2
        }

        registry.mock_tool("web_search", complex_mock)

        result = registry.get_tool_mock("web_search")
        assert result == complex_mock
        assert len(result["results"]) == 2

    def test_registry_copy(self):
        """Test creating a copy of the registry."""
        registry = MockRegistry()

        registry.mock_tool("web_search", "Mocked search")
        registry.mock_llm("summarize", "Mocked summary")

        # Create a copy
        copy_registry = registry.copy()

        assert copy_registry.tool_mocks == registry.tool_mocks
        assert copy_registry.llm_mocks == registry.llm_mocks
        assert copy_registry.enabled == registry.enabled

        # Modifying copy shouldn't affect original
        copy_registry.mock_tool("file_read", "New mock")
        assert "file_read" not in registry.tool_mocks
        assert "file_read" in copy_registry.tool_mocks
