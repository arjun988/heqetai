"""
Compatibility shim: expose the web portal from the new agent_debugger.web package.
"""

from agent_debugger.web import (
    WebPortalDebugger,
    init_web_debugger,
    create_web_debugger,
    attach_agent_to_web,
    app,
    socketio,
)

__all__ = [
    'WebPortalDebugger',
    'init_web_debugger',
    'create_web_debugger',
    'attach_agent_to_web',
    'app',
    'socketio',
]


