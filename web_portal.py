"""
Compatibility shim: expose the web portal from the new agent_debugger.web package.
"""

from agent_debugger.web import (
    WebPortalDebugger,
    app,
    attach_agent_to_web,
    create_web_debugger,
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
]
