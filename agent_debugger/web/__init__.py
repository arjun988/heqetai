"""
Web UI for AgentDebugger.
"""

from .portal import (
    WebPortalDebugger,
    app,
    attach_agent_to_web,
    create_web_debugger,
    debugger_instance,
    init_web_debugger,
    socketio,
)

__all__ = [
    "WebPortalDebugger",
    "init_web_debugger",
    "create_web_debugger",
    "attach_agent_to_web",
    "app",
    "socketio",
    "debugger_instance",
]
