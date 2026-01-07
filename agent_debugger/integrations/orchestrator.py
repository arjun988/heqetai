"""
Multi-agent orchestrator for AgentDebugger.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..debugger import AgentDebugger
from ..events import EventType, TraceEvent
from ..state import AgentState
from .utils import auto_detect_framework


class MultiAgentOrchestrator:
    """Enhanced orchestrator for coordinating multiple agents with shared debugging and framework awareness"""

    def __init__(self, debugger: AgentDebugger):
        self.debugger = debugger
        self.agents: Dict[str, Any] = {}
        self.agent_frameworks: Dict[str, str] = {}
        self.message_history: List[Dict[str, Any]] = []

    def register(self, agent_id: str, agent: Any, framework: Optional[str] = None):
        """Register an agent with optional framework specification"""
        self.agents[agent_id] = agent
        if framework:
            self.agent_frameworks[agent_id] = framework
        else:
            self.agent_frameworks[agent_id] = auto_detect_framework(agent) or "unknown"

        # Auto-attach debugger if not already attached
        if agent_id not in self.debugger.agent_states:
            self.debugger.attach(agent, agent_id)

    def send(
        self, sender_id: str, receiver_id: str, content: str, message_type: str = "task"
    ) -> Any:
        """Send message between agents with enhanced tracking"""
        # Enhanced inter-agent message event
        event = TraceEvent(
            event_type=EventType.INTER_AGENT_MESSAGE,
            agent_id=sender_id,
            step_id=f"msg_{int(datetime.now().timestamp())}",
            data={
                "from": sender_id,
                "to": receiver_id,
                "content_preview": (
                    content[:200] + "..." if len(content) > 200 else content
                ),
                "message_type": message_type,
                "sender_framework": self.agent_frameworks.get(sender_id, "unknown"),
                "receiver_framework": self.agent_frameworks.get(receiver_id, "unknown"),
            },
        )

        # Record message in history
        self.message_history.append(
            {
                "timestamp": datetime.now(),
                "from": sender_id,
                "to": receiver_id,
                "content": content,
                "type": message_type,
            }
        )

        # Use debugger internal emitter when available; otherwise append
        if hasattr(self.debugger, "_emit_event"):
            self.debugger._emit_event(event)
        else:
            self.debugger.trace_events.append(event)

        # Optional break on inter-agent messages via conditional breakpoint
        if self.debugger._should_break(event):
            self.debugger._trigger_breakpoint(event, sender_id)

        receiver = self.agents.get(receiver_id)
        if receiver is None:
            raise ValueError(f"Receiver '{receiver_id}' not registered")

        # Framework-aware invocation
        try:
            receiver_framework = self.agent_frameworks.get(receiver_id, "unknown")

            if receiver_framework == "langchain":
                if hasattr(receiver, "invoke"):
                    return receiver.invoke({"input": content})
                elif hasattr(receiver, "run"):
                    return receiver.run(content)

            elif receiver_framework == "crewai":
                if hasattr(receiver, "execute_task"):
                    # Create a simple task object
                    task = type("Task", (), {"description": content})()
                    return receiver.execute_task(task)

            elif receiver_framework == "autogpt":
                if hasattr(receiver, "execute_command"):
                    return receiver.execute_command(
                        "process_message", {"content": content}
                    )

            elif receiver_framework == "llamaindex":
                if hasattr(receiver, "query"):
                    return receiver.query(content)
                elif hasattr(receiver, "chat"):
                    return receiver.chat(content)

            # Fallback to common methods
            if hasattr(receiver, "invoke"):
                return receiver.invoke({"input": content})
            if hasattr(receiver, "run"):
                return receiver.run(content)
            if hasattr(receiver, "__call__"):
                return receiver(content)

            raise TypeError(
                f"Receiver {receiver_id} does not support standard invocation methods"
            )

        except Exception as e:
            error_event = TraceEvent(
                event_type=EventType.ERROR,
                agent_id=sender_id,
                step_id=event.step_id,
                data={
                    "error": f"Message delivery failed: {str(e)}",
                    "operation": "inter_agent_communication",
                },
            )
            self.debugger.trace_events.append(error_event)
            raise

    def broadcast(
        self, sender_id: str, content: str, message_type: str = "broadcast"
    ) -> Dict[str, Any]:
        """Broadcast message to all agents"""
        results = {}
        for receiver_id in self.agents:
            if receiver_id != sender_id:
                try:
                    result = self.send(sender_id, receiver_id, content, message_type)
                    results[receiver_id] = result
                except Exception as e:
                    results[receiver_id] = f"Error: {e}"
        return results

    def get_communication_graph(self) -> Dict[str, Any]:
        """Get communication graph data for visualization"""
        nodes = [
            {"id": agent_id, "framework": framework}
            for agent_id, framework in self.agent_frameworks.items()
        ]

        edges = []
        for message in self.message_history:
            edges.append(
                {
                    "source": message["from"],
                    "target": message["to"],
                    "type": message["type"],
                    "timestamp": message["timestamp"].isoformat(),
                }
            )

        return {"nodes": nodes, "edges": edges}
