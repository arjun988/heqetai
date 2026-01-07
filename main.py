"""
Compatibility shim: expose the public API from the new agent_debugger package.
"""

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

__all__ = [
    "AgentDebugger",
    "EventType",
    "BreakpointType",
    "TraceEvent",
    "Breakpoint",
    "AgentState",
    "MockRegistry",
    "PerformanceMonitor",
    "DebugConsole",
]
