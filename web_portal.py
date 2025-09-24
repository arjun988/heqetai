"""
AgentDebugger Web Portal
========================

A comprehensive web-based debugging interface for the AgentDebugger framework.
Provides real-time monitoring, interactive controls, and visualization of agent execution.

Features:
- Real-time trace event streaming
- Interactive breakpoint management
- Agent state monitoring
- Performance analytics
- Mock registry controls
- Trace replay functionality
- Multi-agent orchestration view
"""

import json
import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
import os
from dataclasses import asdict

# Import AgentDebugger components
from main import (
    AgentDebugger, TraceEvent, EventType, BreakpointType, Breakpoint, 
    AgentState, MockRegistry, PerformanceMonitor
)
from integration import (
    LangChainDebugger, CrewAIDebugger, AutoGPTDebugger, 
    LlamaIndexDebugger, HuggingFaceDebugger, smart_debug
)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'agentdebugger_secret_key_2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global debugger instance
debugger_instance: Optional[AgentDebugger] = None
debugger_lock = threading.Lock()

class WebPortalDebugger(AgentDebugger):
    """Extended AgentDebugger with web portal integration"""
    
    def __init__(self, **kwargs):
        super().__init__(mode="web", **kwargs)
        self.web_clients: List[str] = []
        self.event_buffer: List[TraceEvent] = []
        self.max_buffer_size = 1000
        
    def _emit_event(self, event: TraceEvent):
        """Override to emit events to web clients"""
        super()._emit_event(event)
        
        # Add to buffer for web clients
        self.event_buffer.append(event)
        if len(self.event_buffer) > self.max_buffer_size:
            self.event_buffer.pop(0)
            
        # Emit to all connected web clients
        socketio.emit('trace_event', {
            'event': self._serialize_event(event),
            'timestamp': event.timestamp.isoformat()
        }, namespace='/')
        
    def _serialize_event(self, event: TraceEvent) -> Dict[str, Any]:
        """Serialize TraceEvent for JSON transmission"""
        return {
            'id': event.id,
            'timestamp': event.timestamp.isoformat(),
            'event_type': event.event_type.value,
            'agent_id': event.agent_id,
            'step_id': event.step_id,
            'data': event.data,
            'parent_event_id': event.parent_event_id,
            'metadata': event.metadata,
            'duration': event.duration
        }
        
    def _trigger_breakpoint(self, event: TraceEvent, agent_id: str):
        """Override to notify web clients of breakpoints"""
        super()._trigger_breakpoint(event, agent_id)
        
        # Emit breakpoint event to web clients
        socketio.emit('breakpoint_hit', {
            'event': self._serialize_event(event),
            'agent_id': agent_id,
            'agent_state': self._serialize_agent_state(self.agent_states[agent_id])
        }, namespace='/')
        
    def _serialize_agent_state(self, state: AgentState) -> Dict[str, Any]:
        """Serialize AgentState for JSON transmission"""
        # Safely serialize last_llm_call
        last_llm_call = None
        if state.last_llm_call:
            last_llm_call = {
                'prompt': state.last_llm_call.get('prompt', ''),
                'response': state.last_llm_call.get('response', ''),
                'timestamp': state.last_llm_call.get('timestamp').isoformat() if state.last_llm_call.get('timestamp') else None,
                'duration': state.last_llm_call.get('duration', 0)
            }
        
        return {
            'agent_id': state.agent_id,
            'memory': state.memory,
            'execution_stack': state.execution_stack,
            'current_step': state.current_step,
            'tool_outputs': state.tool_outputs,
            'reasoning_log': state.reasoning_log,
            'is_paused': state.is_paused,
            'last_llm_call': last_llm_call,
            'created_at': state.created_at.isoformat(),
            'tasks_completed': state.tasks_completed,
            'errors_encountered': state.errors_encountered,
            'performance_stats': state.performance_stats
        }
        
    def get_web_summary(self) -> Dict[str, Any]:
        """Get summary data optimized for web display"""
        return {
            'total_events': len(self.trace_events),
            'active_agents': len(self.agent_states),
            'breakpoints': len(self.breakpoints),
            'events_by_type': self._get_events_by_type(),
            'agent_stats': self._get_agent_stats(),
            'performance_summary': self._get_performance_summary(),
            'recent_events': [self._serialize_event(e) for e in self.trace_events[-10:]]
        }
        
    def cleanup_memory(self):
        """Clean up all memory and reset the debugger state"""
        print("🧹 Cleaning up web portal memory...")
        
        # Clear trace events
        self.trace_events.clear()
        print(f"   ✅ Cleared {len(self.trace_events)} trace events")
        
        # Clear agent states
        self.agent_states.clear()
        print(f"   ✅ Cleared {len(self.agent_states)} agent states")
        
        # Clear breakpoints
        self.breakpoints.clear()
        print(f"   ✅ Cleared {len(self.breakpoints)} breakpoints")
        
        # Clear attached agents
        self._attached_agents.clear()
        print(f"   ✅ Cleared {len(self._attached_agents)} attached agents")
        
        # Clear event buffer
        self.event_buffer.clear()
        print(f"   ✅ Cleared {len(self.event_buffer)} buffered events")
        
        # Clear mock registry
        self.mock_registry.clear_mocks()
        print("   ✅ Cleared mock registry")
        
        # Reset performance monitor
        if self.performance_monitor:
            self.performance_monitor.metrics = {
                'tool_execution_times': [],
                'llm_response_times': [],
                'memory_access_times': [],
                'reasoning_times': []
            }
            self.performance_monitor.start_times.clear()
            print("   ✅ Reset performance monitor")
        
        # Reset integration metadata
        self.integration_metadata = {
            'integration_type': self.__class__.__name__,
            'instrumentation_count': 0,
            'error_count': 0
        }
        print("   ✅ Reset integration metadata")
        
        print("🎉 Web portal memory cleanup completed!")
        
        # Notify web clients of cleanup
        socketio.emit('debugger_cleaned', {
            'message': 'Debugger memory has been cleaned',
            'timestamp': datetime.now().isoformat()
        }, namespace='/')
        
    def _get_events_by_type(self) -> Dict[str, int]:
        """Get count of events by type"""
        counts = {}
        for event in self.trace_events:
            event_type = event.event_type.value
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts
        
    def _get_agent_stats(self) -> Dict[str, Any]:
        """Get statistics for all agents"""
        stats = {}
        for agent_id, state in self.agent_states.items():
            stats[agent_id] = {
                'tasks_completed': state.tasks_completed,
                'errors_encountered': state.errors_encountered,
                'is_paused': state.is_paused,
                'created_at': state.created_at.isoformat(),
                'memory_size': len(state.memory),
                'tool_outputs_count': len(state.tool_outputs)
            }
        return stats
        
    def _get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.performance_monitor:
            return {}
            
        stats = self.performance_monitor.get_statistics()
        return {
            'tool_execution_times': stats.get('tool_execution_times', {}),
            'llm_response_times': stats.get('llm_response_times', {}),
            'memory_access_times': stats.get('memory_access_times', {}),
            'reasoning_times': stats.get('reasoning_times', {})
        }

# Initialize web debugger
def init_web_debugger():
    """Initialize the web debugger instance"""
    global debugger_instance
    with debugger_lock:
        if debugger_instance is None:
            debugger_instance = WebPortalDebugger(
                enable_replay=True,
                enable_performance_monitoring=True
            )
    return debugger_instance

# Web Routes
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/summary')
def get_summary():
    """Get debugger summary"""
    debugger = init_web_debugger()
    return jsonify(debugger.get_web_summary())

@app.route('/api/agents')
def get_agents():
    """Get all agent states"""
    debugger = init_web_debugger()
    agents = {}
    for agent_id, state in debugger.agent_states.items():
        agents[agent_id] = debugger._serialize_agent_state(state)
    return jsonify(agents)

@app.route('/api/events')
def get_events():
    """Get trace events with pagination"""
    debugger = init_web_debugger()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    event_type = request.args.get('type')
    agent_id = request.args.get('agent_id')
    
    events = debugger.trace_events
    
    # Filter by type
    if event_type:
        events = [e for e in events if e.event_type.value == event_type]
    
    # Filter by agent
    if agent_id:
        events = [e for e in events if e.agent_id == agent_id]
    
    # Paginate
    start = (page - 1) * per_page
    end = start + per_page
    page_events = events[start:end]
    
    return jsonify({
        'events': [debugger._serialize_event(e) for e in page_events],
        'total': len(events),
        'page': page,
        'per_page': per_page,
        'has_next': end < len(events),
        'has_prev': page > 1
    })

@app.route('/api/breakpoints', methods=['GET', 'POST', 'DELETE'])
def manage_breakpoints():
    """Manage breakpoints"""
    debugger = init_web_debugger()
    
    if request.method == 'GET':
        breakpoints = []
        for bp in debugger.breakpoints:
            breakpoints.append({
                'id': bp.id,
                'breakpoint_type': bp.breakpoint_type.value,
                'tool_name': bp.tool_name,
                'agent_id': bp.agent_id,
                'enabled': bp.enabled,
                'hit_count': bp.hit_count,
                'temporary': bp.temporary,
                'metadata': bp.metadata
            })
        return jsonify(breakpoints)
    
    elif request.method == 'POST':
        data = request.json
        bp_type = BreakpointType(data['breakpoint_type'])
        
        breakpoint = Breakpoint(
            breakpoint_type=bp_type,
            tool_name=data.get('tool_name'),
            agent_id=data.get('agent_id'),
            enabled=data.get('enabled', True),
            temporary=data.get('temporary', False),
            metadata=data.get('metadata', {})
        )
        
        debugger.add_breakpoint(breakpoint)
        
        # Notify web clients
        socketio.emit('breakpoint_added', {
            'breakpoint': {
                'id': breakpoint.id,
                'breakpoint_type': breakpoint.breakpoint_type.value,
                'tool_name': breakpoint.tool_name,
                'agent_id': breakpoint.agent_id,
                'enabled': breakpoint.enabled,
                'hit_count': breakpoint.hit_count,
                'temporary': breakpoint.temporary,
                'metadata': breakpoint.metadata
            }
        }, namespace='/')
        
        return jsonify({'success': True, 'breakpoint_id': breakpoint.id})
    
    elif request.method == 'DELETE':
        breakpoint_id = request.json.get('breakpoint_id')
        debugger.remove_breakpoint(breakpoint_id)
        
        # Notify web clients
        socketio.emit('breakpoint_removed', {
            'breakpoint_id': breakpoint_id
        }, namespace='/')
        
        return jsonify({'success': True})

@app.route('/api/agent/<agent_id>/control', methods=['POST'])
def control_agent(agent_id):
    """Control agent execution (pause, resume, step)"""
    try:
        debugger = init_web_debugger()
        
        if agent_id not in debugger.agent_states:
            return jsonify({'error': 'Agent not found'}), 404
        
        # Get action from request data
        if not request.json:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        action = request.json.get('action')
        if not action:
            return jsonify({'error': 'No action specified'}), 400
            
        state = debugger.agent_states[agent_id]
        
        if action == 'pause':
            state.is_paused = True
        elif action == 'resume':
            state.is_paused = False
        elif action == 'step':
            state.is_paused = False  # Resume for one step
            # Note: Actual step control would need more sophisticated implementation
        else:
            return jsonify({'error': f'Unknown action: {action}'}), 400
        
        # Notify web clients
        socketio.emit('agent_state_changed', {
            'agent_id': agent_id,
            'state': debugger._serialize_agent_state(state)
        }, namespace='/')
        
        return jsonify({'success': True, 'action': action, 'is_paused': state.is_paused})
        
    except Exception as e:
        print(f"Error in control_agent: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/mock', methods=['GET', 'POST', 'DELETE'])
def manage_mocks():
    """Manage mock registry"""
    debugger = init_web_debugger()
    
    if request.method == 'GET':
        return jsonify({
            'tool_mocks': debugger.mock_registry._tool_mocks,
            'llm_mocks': debugger.mock_registry._llm_mocks,
            'replay_mode': debugger.mock_registry.is_replay_mode()
        })
    
    elif request.method == 'POST':
        data = request.json
        mock_type = data.get('type')  # 'tool' or 'llm'
        name = data.get('name')
        output = data.get('output')
        
        if mock_type == 'tool':
            debugger.mock_registry.mock_tool(name, output)
        elif mock_type == 'llm':
            debugger.mock_registry.mock_llm(name, output)
        
        # Notify web clients
        socketio.emit('mock_added', {
            'type': mock_type,
            'name': name,
            'output': output
        }, namespace='/')
        
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        debugger.mock_registry.clear_mocks()
        
        # Notify web clients
        socketio.emit('mocks_cleared', {}, namespace='/')
        
        return jsonify({'success': True})

@app.route('/api/cleanup', methods=['POST'])
def cleanup_debugger():
    """Clean up debugger memory"""
    try:
        debugger = init_web_debugger()
        debugger.cleanup_memory()
        
        return jsonify({
            'success': True,
            'message': 'Debugger memory cleaned successfully',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"Error during cleanup: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export')
def export_trace():
    """Export trace data"""
    debugger = init_web_debugger()
    format_type = request.args.get('format', 'json')
    
    if format_type == 'json':
        filename = f"trace_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        debugger.export_trace(filename)
        return jsonify({'success': True, 'filename': filename})
    
    return jsonify({'error': 'Unsupported format'}), 400

@app.route('/api/replay', methods=['POST'])
def replay_trace():
    """Replay trace from file"""
    debugger = init_web_debugger()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Save uploaded file temporarily
        temp_filename = f"temp_replay_{uuid.uuid4().hex}.json"
        file.save(temp_filename)
        
        # Load and replay
        debugger.replay_from_file(temp_filename)
        
        # Clean up temp file
        os.remove(temp_filename)
        
        # Notify web clients
        socketio.emit('replay_started', {
            'filename': file.filename
        }, namespace='/')
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    join_room('debugger_clients')
    
    # Send current state to new client
    debugger = init_web_debugger()
    emit('debugger_state', debugger.get_web_summary())

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")
    leave_room('debugger_clients')

@socketio.on('request_update')
def handle_update_request():
    """Handle client update request"""
    debugger = init_web_debugger()
    emit('debugger_state', debugger.get_web_summary())

@socketio.on('agent_command')
def handle_agent_command(data):
    """Handle agent control commands"""
    debugger = init_web_debugger()
    agent_id = data.get('agent_id')
    command = data.get('command')
    
    if agent_id not in debugger.agent_states:
        emit('error', {'message': 'Agent not found'})
        return
    
    state = debugger.agent_states[agent_id]
    
    if command == 'pause':
        state.is_paused = True
    elif command == 'resume':
        state.is_paused = False
    elif command == 'step':
        state.is_paused = False
    
    # Broadcast state change
    socketio.emit('agent_state_changed', {
        'agent_id': agent_id,
        'state': debugger._serialize_agent_state(state)
    })

# Utility functions for web integration
def create_web_debugger(framework: str = "generic", **kwargs) -> WebPortalDebugger:
    """Create a web-enabled debugger for specific framework"""
    debugger_map = {
        'langchain': LangChainDebugger,
        'crewai': CrewAIDebugger,
        'autogpt': AutoGPTDebugger,
        'llamaindex': LlamaIndexDebugger,
        'transformers': HuggingFaceDebugger,
        'generic': WebPortalDebugger
    }
    
    debugger_class = debugger_map.get(framework, WebPortalDebugger)
    
    # For framework-specific debuggers, we need to create them and then convert to WebPortalDebugger
    if debugger_class != WebPortalDebugger:
        # Create the framework-specific debugger first
        framework_debugger = debugger_class(**kwargs)
        # Then create a WebPortalDebugger and copy the integration
        web_debugger = WebPortalDebugger(**kwargs)
        web_debugger.integration = framework_debugger.integration
        web_debugger.framework = framework
        return web_debugger
    else:
        # For generic debugger, create directly
        return WebPortalDebugger(**kwargs)

def attach_agent_to_web(agent, agent_id: str = None, framework: str = "generic"):
    """Attach an agent to the web debugger"""
    global debugger_instance
    
    with debugger_lock:
        if debugger_instance is None:
            debugger_instance = create_web_debugger(framework)
        
        debugged_agent = debugger_instance.attach(agent, agent_id)
        
        # Get the actual agent_id that was assigned
        actual_agent_id = agent_id or f"agent_{len(debugger_instance._attached_agents) - 1}"
        
        # Notify web clients of new agent
        socketio.emit('agent_attached', {
            'agent_id': actual_agent_id,
            'agent_type': type(agent).__name__,
            'framework': framework
        }, namespace='/')
        
        return debugged_agent

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    print("🌐 Starting AgentDebugger Web Portal...")
    print("📊 Dashboard: http://localhost:5000")
    print("🔧 API: http://localhost:5000/api/")
    print("📡 WebSocket: ws://localhost:5000/socket.io/")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
