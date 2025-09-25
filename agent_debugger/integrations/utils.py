"""
Utility functions for AgentDebugger integrations.
"""

import inspect
from typing import Any, Dict, Optional

from ..debugger import AgentDebugger
from .langchain import LangChainDebugger
from .crewai import CrewAIDebugger
from .autogpt import AutoGPTDebugger
from .llamaindex import LlamaIndexDebugger
from .huggingface import HuggingFaceDebugger


def auto_detect_framework(agent: Any) -> Optional[str]:
    """Automatically detect which framework an agent belongs to with enhanced detection"""
    module = inspect.getmodule(agent)
    if module:
        module_name = module.__name__
        
        if 'langchain' in module_name:
            return 'langchain'
        elif 'crewai' in module_name:
            return 'crewai'
        elif 'autogpt' in module_name or 'auto_gpt' in module_name:
            return 'autogpt'
        elif 'llama_index' in module_name or 'llamaindex' in module_name:
            return 'llamaindex'
        elif 'openai' in module_name and hasattr(agent, 'chat'):
            return 'openai'
        elif 'transformers' in module_name:
            return 'transformers'
    
    # Enhanced framework-specific attributes detection
    agent_class_name = agent.__class__.__name__.lower()
    
    # LangChain detection
    if (hasattr(agent, 'invoke') and hasattr(agent, 'ainvoke')) or 'chain' in agent_class_name:
        return 'langchain'
    # CrewAI detection
    elif (hasattr(agent, 'role') and hasattr(agent, 'goal')) or 'crew' in agent_class_name:
        return 'crewai'
    # AutoGPT detection
    elif (hasattr(agent, 'ai_name') and hasattr(agent, 'execute_command')) or 'autogpt' in agent_class_name:
        return 'autogpt'
    # LlamaIndex detection
    elif (hasattr(agent, 'query') and hasattr(agent, 'retrieve')) or 'index' in agent_class_name:
        return 'llamaindex'
    # OpenAI detection
    elif hasattr(agent, 'chat') and hasattr(agent, 'model'):
        return 'openai'
    # Transformers pipelines/models detection by common callables
    elif hasattr(agent, '__call__') or hasattr(agent, 'generate'):
        mod = inspect.getmodule(agent.__class__)
        if mod and 'transformers' in mod.__name__:
            return 'transformers'
    
    return None


def smart_debug(agent: Any, mode: str = "console", **kwargs) -> Any:
    """Automatically detect framework and attach appropriate debugger with enhanced features"""
    framework = auto_detect_framework(agent)
    
    debugger_map = {
        'langchain': LangChainDebugger,
        'crewai': CrewAIDebugger,
        'autogpt': AutoGPTDebugger,
        'llamaindex': LlamaIndexDebugger,
        'transformers': HuggingFaceDebugger,
    }
    
    if framework in debugger_map:
        debugger = debugger_map[framework](mode=mode, **kwargs)
        print(f"🔍 Detected framework: {framework}")
    else:
        print(f"⚠️ Framework not detected, using generic debugger")
        debugger = AgentDebugger(mode=mode, **kwargs)
    
    return debugger.attach(agent)
