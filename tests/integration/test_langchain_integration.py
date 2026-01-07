"""
Integration tests for LangChain debugger integration.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from agent_debugger.integrations.langchain import LangChainIntegration
from agent_debugger import AgentDebugger, EventType, TraceEvent


class TestLangChainIntegration:
    """Test LangChain integration functionality."""

    @pytest.fixture
    def langchain_integration(self, debugger):
        """Create a LangChain integration instance."""
        return LangChainIntegration(debugger)

    @pytest.fixture
    def mock_langchain_agent(self):
        """Create a mock LangChain agent."""
        agent = Mock()
        agent.name = "TestLangChainAgent"
        agent.invoke = Mock(return_value={"output": "test response"})
        agent.run = Mock(return_value="legacy response")
        agent.__call__ = Mock(return_value={"result": "chain response"})
        agent.predict = Mock(return_value="prediction response")
        return agent

    @pytest.fixture
    def mock_async_langchain_agent(self):
        """Create a mock async LangChain agent."""
        agent = Mock()
        agent.name = "AsyncLangChainAgent"
        agent.ainvoke = Mock(return_value={"output": "async response"})
        return agent

    def test_langchain_integration_initialization(self, debugger):
        """Test LangChain integration initialization."""
        integration = LangChainIntegration(debugger)

        assert integration.debugger == debugger
        assert len(integration.instrumented_agents) == 0
        assert len(integration.original_methods) == 0

    def test_instrument_runnable_agent(self, langchain_integration, mock_langchain_agent):
        """Test instrumenting a LangChain Runnable agent."""
        # Mock the invoke method to have our agent
        mock_langchain_agent.invoke = Mock(return_value={"output": "instrumented response"})

        # Mock the proxy creation
        with patch.object(langchain_integration, '_create_proxy') as mock_proxy:
            mock_proxy.return_value = Mock()
            instrumented = langchain_integration.instrument_agent(mock_langchain_agent, "test_agent")

            mock_proxy.assert_called_once()
            assert instrumented is not mock_langchain_agent

    def test_instrument_async_runnable_agent(self, langchain_integration, mock_async_langchain_agent):
        """Test instrumenting an async LangChain Runnable agent."""
        with patch.object(langchain_integration, '_create_proxy') as mock_proxy:
            mock_proxy.return_value = Mock()
            instrumented = langchain_integration.instrument_agent(mock_async_langchain_agent, "async_agent")

            mock_proxy.assert_called_once()
            assert instrumented is not mock_async_langchain_agent

    def test_instrument_legacy_agent(self, langchain_integration, mock_langchain_agent):
        """Test instrumenting a legacy LangChain agent."""
        # Remove newer methods to force legacy path
        del mock_langchain_agent.invoke
        del mock_langchain_agent.__call__

        with patch.object(langchain_integration, '_wrap_method') as mock_wrap:
            instrumented = langchain_integration.instrument_agent(mock_langchain_agent, "legacy_agent")

            # Should call _wrap_method for the run method
            assert mock_wrap.called
            assert instrumented == mock_langchain_agent

    def test_instrument_chain(self, langchain_integration, mock_langchain_agent):
        """Test instrumenting a LangChain chain."""
        # Remove newer methods to force chain path
        del mock_langchain_agent.invoke
        del mock_langchain_agent.run

        with patch.object(langchain_integration, '_wrap_method') as mock_wrap:
            instrumented = langchain_integration.instrument_agent(mock_langchain_agent, "chain_agent")

            assert mock_wrap.called
            assert instrumented == mock_langchain_agent

    def test_instrument_llm_chain(self, langchain_integration, mock_langchain_agent):
        """Test instrumenting an LLMChain."""
        # Remove newer methods to force LLMChain path
        del mock_langchain_agent.invoke
        del mock_langchain_agent.run
        del mock_langchain_agent.__call__

        with patch.object(langchain_integration, '_wrap_method') as mock_wrap:
            instrumented = langchain_integration.instrument_agent(mock_langchain_agent, "llm_chain")

            assert mock_wrap.called
            assert instrumented == mock_langchain_agent

    def test_extract_langchain_events(self, langchain_integration):
        """Test extracting events from LangChain execution data."""
        execution_data = {
            "input": "test input",
            "output": "test output",
            "intermediate_steps": [
                {"action": "tool1", "result": "result1"},
                {"action": "tool2", "result": "result2"}
            ],
            "total_tokens": 150,
            "model_name": "gpt-3.5-turbo"
        }

        events = langchain_integration.extract_events("test_agent", execution_data)

        assert len(events) >= 1  # At least one event should be generated
        assert all(isinstance(event, TraceEvent) for event in events)
        assert all(event.agent_id == "test_agent" for event in events)

    def test_get_agent_state_langchain(self, langchain_integration, mock_langchain_agent):
        """Test getting agent state for LangChain agent."""
        langchain_integration.instrumented_agents["test_agent"] = mock_langchain_agent

        # Mock the agent to have memory and tools
        mock_langchain_agent.memory = Mock()
        mock_langchain_agent.memory.buffer = "Memory content"
        mock_langchain_agent.tools = [Mock(name="tool1"), Mock(name="tool2")]

        state = langchain_integration.get_agent_state("test_agent")

        assert state is not None
        assert state.agent_id == "test_agent"
        assert "memory" in state.memory
        assert len(state.tools) == 2

    def test_get_agent_state_not_found(self, langchain_integration):
        """Test getting agent state for non-existent agent."""
        state = langchain_integration.get_agent_state("nonexistent")
        assert state is None

    def test_list_instrumented_agents(self, langchain_integration, mock_langchain_agent):
        """Test listing instrumented agents."""
        langchain_integration.instrumented_agents["agent1"] = mock_langchain_agent
        langchain_integration.instrumented_agents["agent2"] = Mock()

        agents = langchain_integration.list_instrumented_agents()
        assert len(agents) == 2
        assert "agent1" in agents
        assert "agent2" in agents

    def test_uninstrument_agent(self, langchain_integration, mock_langchain_agent):
        """Test uninstrumenting an agent."""
        langchain_integration.instrumented_agents["test_agent"] = mock_langchain_agent
        langchain_integration.original_methods["test_agent"] = {"run": Mock()}

        langchain_integration.uninstrument_agent("test_agent")

        assert "test_agent" not in langchain_integration.instrumented_agents
        assert "test_agent" not in langchain_integration.original_methods

    def test_uninstrument_all_agents(self, langchain_integration, mock_langchain_agent):
        """Test uninstrumenting all agents."""
        langchain_integration.instrumented_agents["agent1"] = mock_langchain_agent
        langchain_integration.instrumented_agents["agent2"] = Mock()
        langchain_integration.original_methods["agent1"] = {"run": Mock()}
        langchain_integration.original_methods["agent2"] = {"invoke": Mock()}

        langchain_integration.uninstrument_all()

        assert len(langchain_integration.instrumented_agents) == 0
        assert len(langchain_integration.original_methods) == 0

    def test_is_agent_instrumented(self, langchain_integration, mock_langchain_agent):
        """Test checking if an agent is instrumented."""
        assert langchain_integration.is_agent_instrumented("test_agent") is False

        langchain_integration.instrumented_agents["test_agent"] = mock_langchain_agent
        assert langchain_integration.is_agent_instrumented("test_agent") is True

    def test_get_integration_info(self, langchain_integration):
        """Test getting integration information."""
        info = langchain_integration.get_integration_info()

        assert "name" in info
        assert "version" in info
        assert "supported_versions" in info
        assert "capabilities" in info

    def test_health_check(self, langchain_integration):
        """Test health check functionality."""
        # Mock some instrumented agents
        langchain_integration.instrumented_agents["agent1"] = Mock()
        langchain_integration.instrumented_agents["agent2"] = Mock()

        health = langchain_integration.health_check()

        assert health["status"] == "healthy"
        assert health["instrumented_agents"] == 2
        assert "timestamp" in health

    def test_debugger_events_integration(self, langchain_integration, mock_langchain_agent):
        """Test that integration properly emits events to debugger."""
        with patch.object(langchain_integration.debugger, 'record_event') as mock_record:
            langchain_integration._emit_framework_event(
                "test_event",
                "test_agent",
                {"key": "value"}
            )

            mock_record.assert_called_once()
            event = mock_record.call_args[0][0]
            assert isinstance(event, TraceEvent)
            assert event.event_type == EventType.CUSTOM
            assert event.agent_id == "test_agent"
            assert event.data["key"] == "value"

    @patch('langchain.schema.BaseMessage')
    def test_handle_langchain_message_conversion(self, mock_message, langchain_integration):
        """Test handling LangChain message objects."""
        # Mock a LangChain message
        mock_message.content = "Test message"
        mock_message.type = "human"

        # Test conversion in extract_events
        execution_data = {
            "input": mock_message,
            "output": "response",
            "intermediate_steps": []
        }

        events = langchain_integration.extract_events("test_agent", execution_data)

        # Should not crash and should generate events
        assert isinstance(events, list)

    def test_error_handling_in_instrumentation(self, langchain_integration):
        """Test error handling during agent instrumentation."""
        # Pass None as agent
        result = langchain_integration.instrument_agent(None, "test_agent")

        # Should handle gracefully
        assert result is None

    def test_multiple_agents_same_type(self, langchain_integration, mock_langchain_agent):
        """Test instrumenting multiple agents of the same type."""
        agent1 = Mock()
        agent1.invoke = Mock(return_value="response1")
        agent2 = Mock()
        agent2.invoke = Mock(return_value="response2")

        with patch.object(langchain_integration, '_create_proxy') as mock_proxy:
            mock_proxy.return_value = Mock()
            langchain_integration.instrument_agent(agent1, "agent1")
            langchain_integration.instrument_agent(agent2, "agent2")

            # Should have both agents instrumented
            assert len(langchain_integration.instrumented_agents) == 2
            assert mock_proxy.call_count == 2
