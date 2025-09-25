"""
Compatibility shim: expose integrations from the new agent_debugger package.
"""

from agent_debugger.integrations import (
    BaseIntegration,
    LangChainIntegration,
    LangChainDebugger,
    CrewAIIntegration,
    CrewAIDebugger,
    AutoGPTIntegration,
    AutoGPTDebugger,
    LlamaIndexIntegration,
    LlamaIndexDebugger,
    HuggingFaceIntegration,
    HuggingFaceDebugger,
    MultiAgentOrchestrator,
    auto_detect_framework,
    smart_debug,
)

__all__ = [
    'BaseIntegration',
    'LangChainIntegration',
    'LangChainDebugger',
    'CrewAIIntegration',
    'CrewAIDebugger',
    'AutoGPTIntegration',
    'AutoGPTDebugger',
    'LlamaIndexIntegration',
    'LlamaIndexDebugger',
    'HuggingFaceIntegration',
    'HuggingFaceDebugger',
    'MultiAgentOrchestrator',
    'auto_detect_framework',
    'smart_debug',
]