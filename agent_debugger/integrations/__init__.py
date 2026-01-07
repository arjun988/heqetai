"""
AgentDebugger Framework Integrations
"""

from .autogpt import AutoGPTDebugger, AutoGPTIntegration
from .base import BaseIntegration
from .crewai import CrewAIDebugger, CrewAIIntegration
from .huggingface import HuggingFaceDebugger, HuggingFaceIntegration
from .langchain import LangChainDebugger, LangChainIntegration
from .llamaindex import LlamaIndexDebugger, LlamaIndexIntegration
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
