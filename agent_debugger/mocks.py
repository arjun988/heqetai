"""
Mock registry for tools and LLM responses, and replay support.
"""

from typing import Any, Callable, Dict, List, Optional

from .events import TraceEvent


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


