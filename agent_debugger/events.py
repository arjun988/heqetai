"""
Core event and breakpoint types and data structures for AgentDebugger.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Callable


class EventType(Enum):
    """Types of events that can be traced in agent execution"""

    REASONING_START = "reasoning_start"
    REASONING_END = "reasoning_end"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END = "tool_call_end"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    LLM_CALL_START = "llm_call_start"
    LLM_CALL_END = "llm_call_end"
    ERROR = "error"
    BREAKPOINT = "breakpoint"
    INTER_AGENT_MESSAGE = "inter_agent_message"
    AGENT_CREATED = "agent_created"
    AGENT_DESTROYED = "agent_destroyed"
    TASK_START = "task_start"
    TASK_END = "task_end"
    CONTEXT_SWITCH = "context_switch"


class BreakpointType(Enum):
    """Types of breakpoints supported"""

    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    BEFORE_MEMORY_WRITE = "before_memory_write"
    AFTER_MEMORY_WRITE = "after_memory_write"
    AFTER_REASONING = "after_reasoning"
    BEFORE_REASONING = "before_reasoning"
    BEFORE_LLM = "before_llm"
    AFTER_LLM = "after_llm"
    ON_ERROR = "on_error"
    CONDITIONAL = "conditional"
    ON_AGENT_CREATE = "on_agent_create"
    ON_TASK_START = "on_task_start"


@dataclass
class TraceEvent:
    """Represents a single event in agent execution trace"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: EventType = EventType.REASONING_START
    agent_id: str = ""
    step_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    parent_event_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration: Optional[float] = None  # Duration in seconds for end events


@dataclass
class Breakpoint:
    """Represents a breakpoint in agent execution"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    breakpoint_type: BreakpointType = BreakpointType.BEFORE_TOOL
    condition: Optional[Callable[["TraceEvent"], bool]] = None
    tool_name: Optional[str] = None
    agent_id: Optional[str] = None
    enabled: bool = True
    hit_count: int = 0
    temporary: bool = False  # One-time breakpoint
    metadata: Dict[str, Any] = field(default_factory=dict)
