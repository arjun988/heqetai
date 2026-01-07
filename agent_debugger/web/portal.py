"""
AgentDebugger Web Portal implementation.
"""

import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room

from ..debugger import AgentDebugger
from ..context import ContextType, ContextPriority
from ..events import Breakpoint, BreakpointType, EventType, TraceEvent
from ..state import AgentState


app = Flask(__name__, template_folder="../../templates", static_folder="../../static")
app.config["SECRET_KEY"] = "agentdebugger_secret_key_2024"
socketio = SocketIO(app, cors_allowed_origins="*")


class WebPortalDebugger(AgentDebugger):
    """Extended AgentDebugger with web portal integration"""

    def __init__(self, **kwargs):
        super().__init__(mode="web", enable_context_management=True, **kwargs)
        self.web_clients: List[str] = []
        self.event_buffer: List[TraceEvent] = []
        self.max_buffer_size = 1000

    def _emit_event(self, event: TraceEvent):
        super()._emit_event(event)
        self.event_buffer.append(event)
        if len(self.event_buffer) > self.max_buffer_size:
            self.event_buffer.pop(0)
        socketio.emit(
            "trace_event",
            {
                "event": self._serialize_event(event),
                "timestamp": event.timestamp.isoformat(),
            },
            namespace="/",
        )

        # Emit performance update if performance monitoring is enabled
        if self.performance_monitor:
            self._emit_performance_update()

    def _serialize_event(self, event: TraceEvent) -> Dict[str, Any]:
        return {
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type.value,
            "agent_id": event.agent_id,
            "step_id": event.step_id,
            "data": event.data,
            "parent_event_id": event.parent_event_id,
            "metadata": event.metadata,
            "duration": event.duration,
        }

    def _trigger_breakpoint(self, event: TraceEvent, agent_id: str):
        super()._trigger_breakpoint(event, agent_id)
        socketio.emit(
            "breakpoint_hit",
            {
                "event": self._serialize_event(event),
                "agent_id": agent_id,
                "agent_state": self._serialize_agent_state(self.agent_states[agent_id]),
            },
            namespace="/",
        )

    def _serialize_agent_state(self, state: AgentState) -> Dict[str, Any]:
        last_llm_call = None
        if state.last_llm_call:
            last_llm_call = {
                "prompt": state.last_llm_call.get("prompt", ""),
                "response": state.last_llm_call.get("response", ""),
                "timestamp": (
                    state.last_llm_call.get("timestamp").isoformat()
                    if state.last_llm_call.get("timestamp")
                    else None
                ),
                "duration": state.last_llm_call.get("duration", 0),
            }

        return {
            "agent_id": state.agent_id,
            "memory": state.memory,
            "execution_stack": state.execution_stack,
            "current_step": state.current_step,
            "tool_outputs": state.tool_outputs,
            "reasoning_log": state.reasoning_log,
            "is_paused": state.is_paused,
            "last_llm_call": last_llm_call,
            "created_at": state.created_at.isoformat(),
            "tasks_completed": state.tasks_completed,
            "errors_encountered": state.errors_encountered,
            "performance_stats": state.performance_stats,
        }

    def get_web_summary(self) -> Dict[str, Any]:
        summary = {
            "total_events": len(self.trace_events),
            "active_agents": len(self.agent_states),
            "breakpoints": len(self.breakpoints),
            "events_by_type": self._get_events_by_type(),
            "agent_stats": self._get_agent_stats(),
            "performance_summary": self._get_performance_summary(),
            "recent_events": [
                self._serialize_event(e) for e in self.trace_events[-10:]
            ],
        }

        # Add context summary if context management is enabled
        if self.context_manager:
            summary["context_summary"] = self.get_context_summary()

        return summary

    def cleanup_memory(self):
        print("🧹 Cleaning up web portal memory...")
        self.trace_events.clear()
        self.agent_states.clear()
        self.breakpoints.clear()
        self._attached_agents.clear()
        self.event_buffer.clear()
        self.mock_registry.clear_mocks()
        if self.performance_monitor:
            self.performance_monitor.metrics = {
                "tool_execution_times": [],
                "llm_response_times": [],
                "memory_access_times": [],
                "reasoning_times": [],
            }
            self.performance_monitor.start_times.clear()
        print("🎉 Web portal memory cleanup completed!")
        socketio.emit(
            "debugger_cleaned",
            {
                "message": "Debugger memory has been cleaned",
                "timestamp": datetime.now().isoformat(),
            },
            namespace="/",
        )

    def _get_events_by_type(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for event in self.trace_events:
            et = event.event_type.value
            counts[et] = counts.get(et, 0) + 1
        return counts

    def _get_agent_stats(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        for agent_id, state in self.agent_states.items():
            stats[agent_id] = {
                "tasks_completed": state.tasks_completed,
                "errors_encountered": state.errors_encountered,
                "is_paused": state.is_paused,
                "created_at": state.created_at.isoformat(),
                "memory_size": len(state.memory),
                "tool_outputs_count": len(state.tool_outputs),
            }
        return stats

    def _get_performance_summary(self) -> Dict[str, Any]:
        if not self.performance_monitor:
            return {}

        # Update system metrics before getting stats
        self.performance_monitor.update_system_metrics()

        # Get comprehensive statistics
        comprehensive_stats = self.performance_monitor.get_comprehensive_statistics()

        # Fix total_events synchronization - use actual trace events count
        session_info = comprehensive_stats.get("session_info", {})
        session_info["total_events"] = len(self.trace_events)

        # Get chart data
        chart_data = self._get_chart_data()

        result = {
            "core_metrics": comprehensive_stats.get("core_metrics", {}),
            "agent_metrics": comprehensive_stats.get("agent_metrics", {}),
            "system_metrics": comprehensive_stats.get("system_metrics", {}),
            "memory_metrics": comprehensive_stats.get("memory_metrics", {}),
            "session_info": session_info,
            "alerts": comprehensive_stats.get("alerts", []),
            "performance_trends": comprehensive_stats.get("performance_trends", {}),
            "chart_data": chart_data,
        }

        return result

    def _get_chart_data(self) -> Dict[str, Any]:
        """Get chart data for all metric types"""
        if not self.performance_monitor:
            return {}

        chart_data = {}

        # Core performance charts
        for metric in [
            "tool_execution_times",
            "llm_response_times",
            "memory_access_times",
            "reasoning_times",
        ]:
            data = self.performance_monitor.get_chart_data(metric)
            chart_data[metric] = data

        # System metrics charts
        for metric in ["cpu_usage", "memory_usage", "disk_io", "network_io"]:
            data = self.performance_monitor.get_chart_data(metric)
            chart_data[metric] = data

        # Memory metrics charts
        for metric in ["context_size", "agent_memory_size", "total_memory_usage"]:
            data = self.performance_monitor.get_chart_data(metric)
            chart_data[metric] = data

        return chart_data

    def _emit_performance_update(self):
        """Emit performance update via WebSocket"""
        try:
            # Update system metrics
            self.performance_monitor.update_system_metrics()

            # Get current performance data
            performance_data = self.performance_monitor.get_comprehensive_statistics()

            # Emit performance update
            socketio.emit(
                "performance_update",
                {"metrics": performance_data, "timestamp": datetime.now().isoformat()},
                namespace="/",
            )

            # Check for new alerts
            if performance_data.get("alerts"):
                latest_alerts = performance_data["alerts"][-5:]  # Last 5 alerts
                for alert in latest_alerts:
                    socketio.emit("performance_alert", alert, namespace="/")

        except Exception as e:
            print(f"Error emitting performance update: {e}")


debugger_instance: Optional[AgentDebugger] = None
debugger_lock = (
    None  # Using SocketIO/event loop; external locking not required for this module
)


def init_web_debugger() -> WebPortalDebugger:
    global debugger_instance
    if debugger_instance is None:
        debugger_instance = WebPortalDebugger(
            enable_replay=True, enable_performance_monitoring=True
        )
    return debugger_instance


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/summary")
@app.route("/api/dashboard")
def get_summary():
    debugger = init_web_debugger()
    return jsonify(debugger.get_web_summary())


@app.route("/api/agents")
def get_agents():
    debugger = init_web_debugger()
    agents: List[Dict[str, Any]] = []
    for agent_id, state in debugger.agent_states.items():
        serialized = debugger._serialize_agent_state(state)
        serialized["agent_id"] = agent_id
        agents.append(serialized)
    return jsonify(agents)


@app.route("/api/events")
def get_events():
    debugger = init_web_debugger()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    event_type = request.args.get("type")
    agent_id = request.args.get("agent_id")
    events = debugger.trace_events
    if event_type:
        events = [e for e in events if e.event_type.value == event_type]
    if agent_id:
        events = [e for e in events if e.agent_id == agent_id]
    start = (page - 1) * per_page
    end = start + per_page
    page_events = events[start:end]
    return jsonify(
        {
            "events": [debugger._serialize_event(e) for e in page_events],
            "total": len(events),
            "page": page,
            "per_page": per_page,
            "has_next": end < len(events),
            "has_prev": page > 1,
        }
    )


@app.route("/api/breakpoints", methods=["GET", "POST", "DELETE"])
def manage_breakpoints():
    debugger = init_web_debugger()
    if request.method == "GET":
        breakpoints: List[Dict[str, Any]] = []
        for bp in debugger.breakpoints:
            breakpoints.append(
                {
                    "id": bp.id,
                    "breakpoint_type": bp.breakpoint_type.value,
                    "tool_name": bp.tool_name,
                    "agent_id": bp.agent_id,
                    "enabled": bp.enabled,
                    "hit_count": bp.hit_count,
                    "temporary": bp.temporary,
                    "metadata": bp.metadata,
                }
            )
        return jsonify(breakpoints)
    elif request.method == "POST":
        data = request.json
        bp_type = BreakpointType(data["breakpoint_type"])
        breakpoint = Breakpoint(
            breakpoint_type=bp_type,
            tool_name=data.get("tool_name"),
            agent_id=data.get("agent_id"),
            enabled=data.get("enabled", True),
            temporary=data.get("temporary", False),
            metadata=data.get("metadata", {}),
        )
        debugger.add_breakpoint(breakpoint)
        socketio.emit(
            "breakpoint_added",
            {
                "breakpoint": {
                    "id": breakpoint.id,
                    "breakpoint_type": breakpoint.breakpoint_type.value,
                    "tool_name": breakpoint.tool_name,
                    "agent_id": breakpoint.agent_id,
                    "enabled": breakpoint.enabled,
                    "hit_count": breakpoint.hit_count,
                    "temporary": breakpoint.temporary,
                    "metadata": breakpoint.metadata,
                }
            },
            namespace="/",
        )
        return jsonify({"success": True, "breakpoint_id": breakpoint.id})
    elif request.method == "DELETE":
        breakpoint_id = request.json.get("breakpoint_id")
        debugger.remove_breakpoint(breakpoint_id)
        socketio.emit(
            "breakpoint_removed", {"breakpoint_id": breakpoint_id}, namespace="/"
        )
        return jsonify({"success": True})


@app.route("/api/agent/<agent_id>/control", methods=["POST"])
def control_agent(agent_id):
    try:
        debugger = init_web_debugger()
        if agent_id not in debugger.agent_states:
            return jsonify({"error": "Agent not found"}), 404
        if not request.json:
            return jsonify({"error": "No JSON data provided"}), 400
        action = request.json.get("action")
        if not action:
            return jsonify({"error": "No action specified"}), 400
        state = debugger.agent_states[agent_id]
        if action == "pause":
            state.is_paused = True
        elif action == "resume":
            state.is_paused = False
        elif action == "step":
            state.is_paused = False
        else:
            return jsonify({"error": f"Unknown action: {action}"}), 400
        socketio.emit(
            "agent_state_changed",
            {"agent_id": agent_id, "state": debugger._serialize_agent_state(state)},
            namespace="/",
        )
        return jsonify(
            {"success": True, "action": action, "is_paused": state.is_paused}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/mock", methods=["GET", "POST", "DELETE"])
def manage_mocks():
    debugger = init_web_debugger()
    if request.method == "GET":
        return jsonify(
            {
                "tool_mocks": debugger.mock_registry._tool_mocks,
                "llm_mocks": debugger.mock_registry._llm_mocks,
                "replay_mode": debugger.mock_registry.is_replay_mode(),
            }
        )
    elif request.method == "POST":
        data = request.json
        mock_type = data.get("type")
        name = data.get("name")
        output = data.get("output")
        if mock_type == "tool":
            debugger.mock_registry.mock_tool(name, output)
        elif mock_type == "llm":
            debugger.mock_registry.mock_llm(name, output)
        socketio.emit(
            "mock_added",
            {"type": mock_type, "name": name, "output": output},
            namespace="/",
        )
        return jsonify({"success": True})
    elif request.method == "DELETE":
        debugger.mock_registry.clear_mocks()
        socketio.emit("mocks_cleared", {}, namespace="/")
        return jsonify({"success": True})


@app.route("/api/cleanup", methods=["POST"])
def cleanup_debugger():
    try:
        debugger = init_web_debugger()
        debugger.cleanup_memory()
        return jsonify(
            {
                "success": True,
                "message": "Debugger memory cleaned successfully",
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/export")
def export_trace():
    debugger = init_web_debugger()
    filename = f"trace_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    debugger.export_trace(filename)
    return jsonify({"success": True, "filename": filename})


@app.route("/api/performance")
def get_performance_data():
    """Get comprehensive performance data"""
    debugger = init_web_debugger()
    if not debugger.performance_monitor:
        return jsonify({"error": "Performance monitoring not enabled"}), 400

    # Use the performance summary method which includes chart data
    performance_data = debugger._get_performance_summary()

    return jsonify(performance_data)


@app.route("/api/performance/charts/<metric_type>")
def get_performance_chart(metric_type):
    """Get chart data for specific metric type"""
    debugger = init_web_debugger()
    if not debugger.performance_monitor:
        return jsonify({"error": "Performance monitoring not enabled"}), 400

    time_range = int(request.args.get("time_range", 60))  # minutes
    chart_data = debugger.performance_monitor.get_chart_data(metric_type, time_range)

    return jsonify(chart_data)


@app.route("/api/performance/alerts")
def get_performance_alerts():
    """Get performance alerts"""
    debugger = init_web_debugger()
    if not debugger.performance_monitor:
        return jsonify({"error": "Performance monitoring not enabled"}), 400

    alerts = debugger.performance_monitor.alerts
    return jsonify(
        {"alerts": alerts[-50:], "total_alerts": len(alerts)}  # Last 50 alerts
    )


@app.route("/api/performance/agents/<agent_id>")
def get_agent_performance(agent_id):
    """Get performance data for specific agent"""
    debugger = init_web_debugger()
    if not debugger.performance_monitor:
        return jsonify({"error": "Performance monitoring not enabled"}), 400

    if agent_id not in debugger.performance_monitor.agent_metrics:
        return jsonify({"error": "Agent not found"}), 404

    agent_data = debugger.performance_monitor.agent_metrics[agent_id]
    efficiency_score = debugger.performance_monitor.calculate_efficiency_score(agent_id)

    return jsonify(
        {
            "agent_id": agent_id,
            "metrics": debugger.performance_monitor._get_metric_stats(agent_data),
            "efficiency_score": efficiency_score,
            "total_tasks": len(agent_data["task_completion_times"]),
            "total_errors": sum(agent_data["error_count"]),
            "avg_memory_usage": sum(agent_data["memory_usage"])
            / max(1, len(agent_data["memory_usage"])),
        }
    )


@app.route("/api/performance/system")
def get_system_performance():
    """Get system performance metrics"""
    debugger = init_web_debugger()
    if not debugger.performance_monitor:
        return jsonify({"error": "Performance monitoring not enabled"}), 400

    # Update system metrics
    debugger.performance_monitor.update_system_metrics()

    system_stats = debugger.performance_monitor._get_metric_stats(
        debugger.performance_monitor.system_metrics
    )

    return jsonify(
        {
            "system_metrics": system_stats,
            "current_cpu": psutil.cpu_percent() if "psutil" in globals() else 0,
            "current_memory": (
                psutil.virtual_memory().percent if "psutil" in globals() else 0
            ),
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/api/replay", methods=["POST"])
def replay_trace():
    debugger = init_web_debugger()
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    try:
        temp_filename = f"temp_replay_{uuid.uuid4().hex}.json"
        file.save(temp_filename)
        debugger.replay_from_file(temp_filename)
        os.remove(temp_filename)
        socketio.emit("replay_started", {"filename": file.filename}, namespace="/")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Context Management API Endpoints


@app.route("/api/contexts", methods=["GET", "POST", "PUT", "DELETE"])
def manage_contexts():
    debugger = init_web_debugger()
    if not debugger.context_manager:
        return jsonify({"error": "Context management is not enabled"}), 400

    if request.method == "GET":
        # Get contexts with optional filters
        query = request.args.get("query", "")
        type_filter = request.args.get("type")
        agent_filter = request.args.get("agent_id")
        tag_filter = request.args.getlist("tags")
        priority_filter = request.args.getlist("priority")

        # Convert string filters to enums
        type_enum = ContextType(type_filter) if type_filter else None
        priority_enums = (
            [ContextPriority(p) for p in priority_filter] if priority_filter else None
        )

        contexts = debugger.search_contexts(
            query=query,
            type_filter=type_enum,
            agent_filter=agent_filter,
            tag_filter=tag_filter,
            priority_filter=priority_enums,
        )

        return jsonify([context.to_dict() for context in contexts])

    elif request.method == "POST":
        # Add new context
        data = request.json
        try:
            context_id = debugger.add_context(
                type=ContextType(data["type"]),
                key=data["key"],
                value=data["value"],
                priority=ContextPriority(data.get("priority", "medium")),
                expires_in=None,  # Could be added later
                tags=data.get("tags", []),
                metadata=data.get("metadata", {}),
                agent_id=data.get("agent_id"),
                step_id=data.get("step_id"),
            )

            socketio.emit(
                "context_added",
                {"context_id": context_id, "type": data["type"], "key": data["key"]},
                namespace="/",
            )

            return jsonify({"success": True, "context_id": context_id})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    elif request.method == "PUT":
        # Update context
        data = request.json
        context_id = data.get("context_id")
        if not context_id:
            return jsonify({"error": "context_id is required"}), 400

        updates = {k: v for k, v in data.items() if k != "context_id"}
        success = debugger.update_context(context_id, **updates)

        if success:
            socketio.emit(
                "context_updated",
                {"context_id": context_id, "updates": updates},
                namespace="/",
            )
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Context not found"}), 404

    elif request.method == "DELETE":
        # Delete context
        data = request.json
        context_id = data.get("context_id")
        if not context_id:
            return jsonify({"error": "context_id is required"}), 400

        success = debugger.delete_context(context_id)
        if success:
            socketio.emit("context_deleted", {"context_id": context_id}, namespace="/")
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Context not found"}), 404


@app.route("/api/contexts/summary")
def get_context_summary():
    debugger = init_web_debugger()
    if not debugger.context_manager:
        return jsonify({"error": "Context management is not enabled"}), 400

    return jsonify(debugger.get_context_summary())


@app.route("/api/contexts/export")
def export_contexts():
    debugger = init_web_debugger()
    if not debugger.context_manager:
        return jsonify({"error": "Context management is not enabled"}), 400

    format_type = request.args.get("format", "json")
    include_expired = request.args.get("include_expired", "false").lower() == "true"

    # Get filters from query parameters
    filters = {}
    if request.args.get("type"):
        filters["type"] = request.args.get("type")
    if request.args.get("agent_id"):
        filters["agent_id"] = request.args.get("agent_id")
    if request.args.getlist("tags"):
        filters["tags"] = request.args.getlist("tags")

    try:
        exported_data = debugger.export_contexts(
            format=format_type,
            include_expired=include_expired,
            filters=filters if filters else None,
        )

        return jsonify(
            {
                "success": True,
                "data": exported_data,
                "format": format_type,
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/contexts/import", methods=["POST"])
def import_contexts():
    debugger = init_web_debugger()
    if not debugger.context_manager:
        return jsonify({"error": "Context management is not enabled"}), 400

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    format_type = request.form.get("format", "json")

    try:
        # Read file content
        file_content = file.read().decode("utf-8")

        # Import contexts
        imported_count = debugger.import_contexts(file_content, format_type)

        socketio.emit(
            "contexts_imported",
            {"count": imported_count, "format": format_type},
            namespace="/",
        )

        return jsonify(
            {"success": True, "imported_count": imported_count, "format": format_type}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/contexts/clear", methods=["POST"])
def clear_contexts():
    debugger = init_web_debugger()
    if not debugger.context_manager:
        return jsonify({"error": "Context management is not enabled"}), 400

    data = request.json or {}
    type_filter = data.get("type")
    agent_filter = data.get("agent_id")
    tag_filter = data.get("tags", [])

    # Convert string to enum if provided
    type_enum = ContextType(type_filter) if type_filter else None

    try:
        cleared_count = debugger.clear_contexts(
            type_filter=type_enum, agent_filter=agent_filter, tag_filter=tag_filter
        )

        socketio.emit(
            "contexts_cleared",
            {
                "count": cleared_count,
                "filters": {
                    "type": type_filter,
                    "agent_id": agent_filter,
                    "tags": tag_filter,
                },
            },
            namespace="/",
        )

        return jsonify({"success": True, "cleared_count": cleared_count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@socketio.on("connect")
def handle_connect(auth=None):
    join_room("debugger_clients")
    debugger = init_web_debugger()
    emit("debugger_state", debugger.get_web_summary())


@socketio.on("disconnect")
def handle_disconnect():
    leave_room("debugger_clients")


@socketio.on("request_update")
def handle_update_request():
    debugger = init_web_debugger()
    emit("debugger_state", debugger.get_web_summary())


@socketio.on("agent_command")
def handle_agent_command(data):
    debugger = init_web_debugger()
    agent_id = data.get("agent_id")
    command = data.get("command")
    if agent_id not in debugger.agent_states:
        emit("error", {"message": "Agent not found"})
        return
    state = debugger.agent_states[agent_id]
    if command == "pause":
        state.is_paused = True
    elif command == "resume":
        state.is_paused = False
    elif command == "step":
        state.is_paused = False
    socketio.emit(
        "agent_state_changed",
        {"agent_id": agent_id, "state": debugger._serialize_agent_state(state)},
    )


def create_web_debugger(framework: str = "generic", **kwargs) -> WebPortalDebugger:
    return WebPortalDebugger(**kwargs)


def attach_agent_to_web(
    agent, agent_id: Optional[str] = None, framework: str = "generic"
):
    debugger = init_web_debugger()
    return debugger.attach(agent, agent_id)


if __name__ == "__main__":
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static/css", exist_ok=True)
    os.makedirs("static/js", exist_ok=True)
    print("🌐 Starting AgentDebugger Web Portal...")
    print("📊 Dashboard: http://localhost:5000")
    print("🔧 API: http://localhost:5000/api/")
    print("📡 WebSocket: ws://localhost:5000/socket.io/")
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
