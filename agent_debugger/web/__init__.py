"""
Web UI for AgentDebugger.
"""

from .portal import (
    WebPortalDebugger,
    init_web_debugger,
    create_web_debugger,
    attach_agent_to_web,
    app,
    socketio,
    debugger_instance,
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
