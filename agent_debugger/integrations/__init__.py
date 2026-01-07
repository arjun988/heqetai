"""
AgentDebugger Framework Integrations
"""

from .base import BaseIntegration
from .langchain import LangChainIntegration, LangChainDebugger
from .crewai import CrewAIIntegration, CrewAIDebugger
from .autogpt import AutoGPTIntegration, AutoGPTDebugger
from .llamaindex import LlamaIndexIntegration, LlamaIndexDebugger
from .huggingface import HuggingFaceIntegration, HuggingFaceDebugger
from .orchestrator import MultiAgentOrchestrator
from .utils import auto_detect_framework, smart_debug

__all__ = [
    "BaseIntegration",
    "LangChainIntegration",
    "LangChainDebugger",
    "CrewAIIntegration",
    "CrewAIDebugger",
    "AutoGPTIntegration",
    "AutoGPTDebugger",
    "LlamaIndexIntegration",
    "LlamaIndexDebugger",
    "HuggingFaceIntegration",
    "HuggingFaceDebugger",
    "MultiAgentOrchestrator",
    "auto_detect_framework",
    "smart_debug",
]
