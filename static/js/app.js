/**
 * AgentDebugger Web Portal - Frontend JavaScript
 * Handles real-time communication with the backend via WebSocket
 * and provides interactive debugging interface
 */

class AgentDebuggerApp {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.agents = {};
        this.events = [];
        this.breakpoints = [];
        this.performanceChart = null;
        
        this.init();
    }
    
    init() {
        this.initializeWebSocket();
        this.setupEventHandlers();
        this.loadInitialData();
        this.setupPerformanceChart();
    }
    
    initializeWebSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Connected to AgentDebugger server');
            this.connected = true;
            this.updateConnectionStatus();
            this.socket.emit('request_update');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from AgentDebugger server');
            this.connected = false;
            this.updateConnectionStatus();
        });
        
        this.socket.on('debugger_state', (data) => {
            this.updateDashboard(data);
        });
        
        this.socket.on('trace_event', (data) => {
            this.addTraceEvent(data.event);
        });
        
        this.socket.on('breakpoint_hit', (data) => {
            this.handleBreakpointHit(data);
        });
        
        this.socket.on('agent_state_changed', (data) => {
            this.updateAgentState(data.agent_id, data.state);
        });
        
        this.socket.on('agent_attached', (data) => {
            this.handleAgentAttached(data);
        });
        
        this.socket.on('breakpoint_added', (data) => {
            this.addBreakpointToList(data.breakpoint);
        });
        
        this.socket.on('breakpoint_removed', (data) => {
            this.removeBreakpointFromList(data.breakpoint_id);
        });
        
        this.socket.on('debugger_cleaned', (data) => {
            this.showNotification('Debugger memory has been cleaned', 'info');
            // Refresh all data to show empty state
            this.refreshAgents();
            this.refreshEvents();
            this.refreshBreakpoints();
        });
        
        this.socket.on('error', (data) => {
            this.showError(data.message);
        });
    }
    
    setupEventHandlers() {
        // Event filter change
        document.getElementById('event-filter').addEventListener('change', () => {
            this.refreshEvents();
        });
        
        // Auto-refresh every 10 seconds
        setInterval(() => {
            if (this.connected) {
                this.socket.emit('request_update');
            }
        }, 10000);
    }
    
    async loadInitialData() {
        try {
            // Load summary
            const summaryResponse = await fetch('/api/summary');
            const summary = await summaryResponse.json();
            this.updateDashboard(summary);
            
            // Load agents
            await this.refreshAgents();
            
            // Load events
            await this.refreshEvents();
            
            // Load breakpoints
            await this.refreshBreakpoints();
            
        } catch (error) {
            console.error('Failed to load initial data:', error);
            this.showError('Failed to load initial data');
        }
    }
    
    updateConnectionStatus() {
        const statusElement = document.getElementById('connection-status');
        if (this.connected) {
            statusElement.className = 'badge bg-success';
            statusElement.textContent = 'Connected';
        } else {
            statusElement.className = 'badge bg-danger';
            statusElement.textContent = 'Disconnected';
        }
    }
    
    updateDashboard(data) {
        // Update summary cards
        document.getElementById('total-events').textContent = data.total_events || 0;
        document.getElementById('active-agents').textContent = data.active_agents || 0;
        document.getElementById('breakpoints-count').textContent = data.breakpoints || 0;
        
        // Update error count from events
        const errorCount = data.events_by_type?.error || 0;
        document.getElementById('errors-count').textContent = errorCount;
        
        // Show error notification if there are errors
        if (errorCount > 0) {
            const errorElement = document.getElementById('errors-count');
            errorElement.parentElement.style.color = '#dc3545';
            errorElement.parentElement.style.fontWeight = 'bold';
        }
        
        // Update performance chart if data available
        if (data.performance_summary) {
            this.updatePerformanceChart(data.performance_summary);
        }
        
        // Show recent errors in console
        if (data.recent_events) {
            const errorEvents = data.recent_events.filter(e => e.event_type === 'error');
            if (errorEvents.length > 0) {
                console.warn('Recent errors detected:', errorEvents);
                this.showNotification(`${errorEvents.length} recent error(s) detected`, 'warning');
            }
        }
    }
    
    addTraceEvent(event) {
        this.events.unshift(event); // Add to beginning
        
        // Limit events in memory
        if (this.events.length > 1000) {
            this.events = this.events.slice(0, 1000);
        }
        
        // Update events display if on events tab
        const activeTab = document.querySelector('#mainTabs .nav-link.active');
        if (activeTab && activeTab.id === 'events-tab') {
            this.renderEvents();
        }
        
        // Update summary
        this.socket.emit('request_update');
    }
    
    async refreshAgents() {
        try {
            const response = await fetch('/api/agents');
            const agents = await response.json();
            this.agents = agents;
            this.renderAgents();
        } catch (error) {
            console.error('Failed to refresh agents:', error);
        }
    }
    
    async refreshEvents() {
        try {
            const filter = document.getElementById('event-filter').value;
            let url = '/api/events?per_page=100';
            if (filter) {
                url += `&type=${filter}`;
            }
            
            const response = await fetch(url);
            const data = await response.json();
            this.events = data.events;
            this.renderEvents();
        } catch (error) {
            console.error('Failed to refresh events:', error);
        }
    }
    
    async refreshBreakpoints() {
        try {
            const response = await fetch('/api/breakpoints');
            const breakpoints = await response.json();
            this.breakpoints = breakpoints;
            this.renderBreakpoints();
        } catch (error) {
            console.error('Failed to refresh breakpoints:', error);
        }
    }
    
    
    renderAgents() {
        const container = document.getElementById('agents-container');
        container.innerHTML = '';
        
        Object.entries(this.agents).forEach(([agentId, state]) => {
            const agentCard = this.createAgentCard(agentId, state);
            container.appendChild(agentCard);
        });
    }
    
    createAgentCard(agentId, state) {
        const col = document.createElement('div');
        col.className = 'col-md-4 mb-3';
        
        const statusClass = state.is_paused ? 'status-paused' : 
                           state.errors_encountered > 0 ? 'status-error' : 'status-running';
        
        const statusText = state.is_paused ? 'Paused' : 
                          state.errors_encountered > 0 ? 'Error' : 'Running';
        
        // Get recent errors for this agent
        const recentErrors = this.events.filter(e => 
            e.agent_id === agentId && e.event_type === 'error'
        ).slice(0, 3); // Show last 3 errors
        
        // Get recent LLM calls for this agent
        const recentLLMCalls = this.events.filter(e => 
            e.agent_id === agentId && e.event_type === 'llm_call_end'
        ).slice(0, 2); // Show last 2 LLM calls
        
        col.innerHTML = `
            <div class="card agent-card h-100">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">
                        <span class="status-indicator ${statusClass}"></span>
                        ${agentId}
                    </h6>
                    <span class="badge bg-secondary">${statusText}</span>
                </div>
                <div class="card-body">
                    <div class="row text-center mb-3">
                        <div class="col-6">
                            <strong>${state.tasks_completed}</strong>
                            <br><small class="text-muted">Tasks</small>
                        </div>
                        <div class="col-6">
                            <strong>${state.errors_encountered}</strong>
                            <br><small class="text-muted">Errors</small>
                        </div>
                    </div>
                    
                    <!-- Recent Errors Section -->
                    ${recentErrors.length > 0 ? `
                    <div class="mb-3">
                        <h6 class="text-danger"><i class="fas fa-exclamation-triangle"></i> Recent Errors</h6>
                        <div class="error-list" style="max-height: 100px; overflow-y: auto;">
                            ${recentErrors.map(error => `
                                <div class="alert alert-danger alert-sm py-1 px-2 mb-1">
                                    <small>
                                        <strong>${error.data.error_type || 'Error'}:</strong><br>
                                        ${error.data.error || 'Unknown error'}<br>
                                        <em>${new Date(error.timestamp).toLocaleTimeString()}</em>
                                    </small>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    ` : ''}
                    
                    <!-- Recent LLM Calls Section -->
                    ${recentLLMCalls.length > 0 ? `
                    <div class="mb-3">
                        <h6 class="text-info"><i class="fas fa-brain"></i> Recent LLM Calls</h6>
                        <div class="llm-list" style="max-height: 120px; overflow-y: auto;">
                            ${recentLLMCalls.map(call => `
                                <div class="alert alert-info alert-sm py-1 px-2 mb-1">
                                    <small>
                                        <strong>Prompt:</strong> ${call.data.prompt ? call.data.prompt.substring(0, 50) + '...' : 'N/A'}<br>
                                        <strong>Response:</strong> ${call.data.response ? call.data.response.substring(0, 50) + '...' : 'N/A'}<br>
                                        <strong>Duration:</strong> ${call.duration ? call.duration.toFixed(2) + 's' : 'N/A'}<br>
                                        <em>${new Date(call.timestamp).toLocaleTimeString()}</em>
                                    </small>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    ` : ''}
                    
                    <div class="mt-2">
                        <small class="text-muted">Memory: ${state.memory_size} items</small><br>
                        <small class="text-muted">Created: ${new Date(state.created_at).toLocaleString()}</small>
                    </div>
                </div>
                <div class="card-footer">
                    <div class="btn-group w-100" role="group">
                        <button class="btn btn-sm btn-outline-warning" onclick="app.controlAgent('${agentId}', 'pause')" ${state.is_paused ? 'disabled' : ''}>
                            <i class="fas fa-pause"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-success" onclick="app.controlAgent('${agentId}', 'resume')" ${!state.is_paused ? 'disabled' : ''}>
                            <i class="fas fa-play"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-primary" onclick="app.controlAgent('${agentId}', 'step')">
                            <i class="fas fa-step-forward"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-info" onclick="app.showAgentDetails('${agentId}')">
                            <i class="fas fa-info"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        return col;
    }
    
    renderEvents() {
        const container = document.getElementById('events-container');
        container.innerHTML = '';
        
        this.events.forEach(event => {
            const eventItem = this.createEventItem(event);
            container.appendChild(eventItem);
        });
    }
    
    createEventItem(event) {
        const div = document.createElement('div');
        div.className = `event-item ${this.getEventClass(event.event_type)}`;
        div.style.cursor = 'pointer';
        div.onclick = () => this.showEventDetails(event);
        
        const timestamp = new Date(event.timestamp).toLocaleTimeString();
        const duration = event.duration ? ` (${event.duration.toFixed(2)}s)` : '';
        
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <strong>${event.event_type}</strong> - ${event.agent_id}
                    <br>
                    <small class="text-muted">${this.getEventDescription(event)}</small>
                </div>
                <div class="text-end">
                    <small class="text-muted">${timestamp}${duration}</small>
                </div>
            </div>
        `;
        
        return div;
    }
    
    getEventClass(eventType) {
        const classMap = {
            'error': 'error',
            'tool_call_start': 'tool_call',
            'tool_call_end': 'tool_call',
            'llm_call_start': 'llm_call',
            'llm_call_end': 'llm_call',
            'reasoning_start': 'reasoning',
            'reasoning_end': 'reasoning'
        };
        return classMap[eventType] || '';
    }
    
    getEventDescription(event) {
        const data = event.data;
        switch (event.event_type) {
            case 'tool_call_start':
                return `Tool: ${data.tool_name}`;
            case 'tool_call_end':
                return `Tool: ${data.tool_name} - ${data.result ? 'Success' : 'Failed'}`;
            case 'llm_call_start':
                return `Prompt: ${data.prompt?.substring(0, 50)}...`;
            case 'llm_call_end':
                return `Response: ${data.response?.substring(0, 50)}...`;
            case 'memory_write':
                return `Key: ${data.key}`;
            case 'error':
                return `Error: ${data.error}`;
            default:
                return event.step_id;
        }
    }
    
    renderBreakpoints() {
        const container = document.getElementById('breakpoints-container');
        container.innerHTML = '';
        
        if (this.breakpoints.length === 0) {
            container.innerHTML = '<p class="text-muted">No breakpoints set</p>';
            return;
        }
        
        this.breakpoints.forEach(breakpoint => {
            const breakpointItem = this.createBreakpointItem(breakpoint);
            container.appendChild(breakpointItem);
        });
    }
    
    createBreakpointItem(breakpoint) {
        const div = document.createElement('div');
        div.className = 'breakpoint-item d-flex justify-content-between align-items-center';
        
        const typeText = breakpoint.breakpoint_type.replace('_', ' ').toUpperCase();
        const toolText = breakpoint.tool_name ? ` (${breakpoint.tool_name})` : '';
        const agentText = breakpoint.agent_id ? ` [${breakpoint.agent_id}]` : '';
        
        div.innerHTML = `
            <div>
                <strong>${typeText}${toolText}${agentText}</strong>
                <br>
                <small class="text-muted">
                    Hits: ${breakpoint.hit_count} | 
                    ${breakpoint.enabled ? 'Enabled' : 'Disabled'} |
                    ${breakpoint.temporary ? 'Temporary' : 'Permanent'}
                </small>
            </div>
            <div class="btn-group" role="group">
                <button class="btn btn-sm btn-outline-${breakpoint.enabled ? 'warning' : 'success'}" 
                        onclick="app.toggleBreakpoint('${breakpoint.id}')">
                    <i class="fas fa-${breakpoint.enabled ? 'pause' : 'play'}"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="app.deleteBreakpoint('${breakpoint.id}')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        return div;
    }
    
    
    setupPerformanceChart() {
        try {
            const canvas = document.getElementById('performance-chart');
            if (!canvas) {
                console.error('Performance chart canvas not found');
                return;
            }
            
            const ctx = canvas.getContext('2d');
            this.performanceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Tool Execution Time',
                        data: [],
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        tension: 0.1
                    }, {
                        label: 'LLM Response Time',
                        data: [],
                        borderColor: '#ffc107',
                        backgroundColor: 'rgba(255, 193, 7, 0.1)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Time (seconds)'
                            }
                        }
                    }
                }
            });
            console.log('Performance chart initialized successfully');
        } catch (error) {
            console.error('Error setting up performance chart:', error);
        }
    }
    
    updatePerformanceChart(performanceData) {
        // This would update the chart with new performance data
        // Implementation depends on the structure of performanceData
        console.log('Performance data:', performanceData);
    }
    
    // Event handlers
    async controlAgent(agentId, action) {
        try {
            console.log(`Attempting to ${action} agent ${agentId}`);
            
            const response = await fetch(`/api/agent/${agentId}/control`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ action })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                console.log(`Successfully ${action}ed agent ${agentId}:`, result);
                this.refreshAgents();
                this.showNotification(`Agent ${agentId} ${action}ed successfully`, 'success');
            } else {
                console.error(`Failed to ${action} agent:`, result);
                this.showError(`Failed to ${action} agent: ${result.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error(`Failed to ${action} agent:`, error);
            this.showError(`Failed to ${action} agent: ${error.message}`);
        }
    }
    
    showAgentDetails(agentId) {
        const state = this.agents[agentId];
        if (!state) return;
        
        // Get all errors for this agent
        const allErrors = this.events.filter(e => 
            e.agent_id === agentId && e.event_type === 'error'
        );
        
        // Get all LLM calls for this agent
        const allLLMCalls = this.events.filter(e => 
            e.agent_id === agentId && e.event_type === 'llm_call_end'
        );
        
        // Create detailed modal content
        const modalContent = `
            <div class="row">
                <div class="col-md-6">
                    <h6><i class="fas fa-info-circle"></i> Agent State</h6>
                    <div class="json-viewer">${JSON.stringify(state, null, 2)}</div>
                </div>
                <div class="col-md-6">
                    <h6><i class="fas fa-exclamation-triangle text-danger"></i> All Errors (${allErrors.length})</h6>
                    <div style="max-height: 300px; overflow-y: auto;">
                        ${allErrors.length > 0 ? allErrors.map(error => `
                            <div class="alert alert-danger mb-2">
                                <strong>${error.data.error_type || 'Error'}</strong><br>
                                <small>${error.data.error || 'Unknown error'}</small><br>
                                <em>${new Date(error.timestamp).toLocaleString()}</em>
                                ${error.data.tool_name ? `<br><strong>Tool:</strong> ${error.data.tool_name}` : ''}
                            </div>
                        `).join('') : '<p class="text-muted">No errors</p>'}
                    </div>
                </div>
            </div>
            
            <div class="row mt-3">
                <div class="col-12">
                    <h6><i class="fas fa-brain text-info"></i> All LLM Calls (${allLLMCalls.length})</h6>
                    <div style="max-height: 400px; overflow-y: auto;">
                        ${allLLMCalls.length > 0 ? allLLMCalls.map(call => `
                            <div class="alert alert-info mb-2">
                                <div class="row">
                                    <div class="col-md-6">
                                        <strong>Prompt:</strong><br>
                                        <div class="bg-light p-2 rounded" style="max-height: 100px; overflow-y: auto;">
                                            ${call.data.prompt || 'N/A'}
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <strong>Response:</strong><br>
                                        <div class="bg-light p-2 rounded" style="max-height: 100px; overflow-y: auto;">
                                            ${call.data.response || 'N/A'}
                                        </div>
                                    </div>
                                </div>
                                <div class="mt-2">
                                    <small>
                                        <strong>Duration:</strong> ${call.duration ? call.duration.toFixed(2) + 's' : 'N/A'} | 
                                        <strong>Time:</strong> ${new Date(call.timestamp).toLocaleString()}
                                    </small>
                                </div>
                            </div>
                        `).join('') : '<p class="text-muted">No LLM calls</p>'}
                    </div>
                </div>
            </div>
        `;
        
        document.getElementById('event-detail-content').innerHTML = modalContent;
        new bootstrap.Modal(document.getElementById('eventDetailModal')).show();
    }
    
    showEventDetails(event) {
        const modalContent = `
            <h6>Event: ${event.event_type}</h6>
            <p><strong>Agent:</strong> ${event.agent_id}</p>
            <p><strong>Step:</strong> ${event.step_id}</p>
            <p><strong>Timestamp:</strong> ${new Date(event.timestamp).toLocaleString()}</p>
            ${event.duration ? `<p><strong>Duration:</strong> ${event.duration.toFixed(2)}s</p>` : ''}
            <h6>Data:</h6>
            <div class="json-viewer">${JSON.stringify(event.data, null, 2)}</div>
        `;
        
        document.getElementById('event-detail-content').innerHTML = modalContent;
        new bootstrap.Modal(document.getElementById('eventDetailModal')).show();
    }
    
    handleBreakpointHit(data) {
        // Show notification and highlight the event
        this.showNotification(`Breakpoint hit in agent ${data.agent_id}`, 'warning');
        
        // Update agent state
        this.updateAgentState(data.agent_id, data.agent_state);
        
        // Switch to agents tab to show paused agent
        document.getElementById('agents-tab').click();
    }
    
    handleAgentAttached(data) {
        this.showNotification(`Agent ${data.agent_id} attached (${data.framework})`, 'success');
        this.refreshAgents();
    }
    
    updateAgentState(agentId, state) {
        this.agents[agentId] = state;
        this.renderAgents();
    }
    
    addBreakpointToList(breakpoint) {
        this.breakpoints.push(breakpoint);
        this.renderBreakpoints();
    }
    
    removeBreakpointFromList(breakpointId) {
        this.breakpoints = this.breakpoints.filter(bp => bp.id !== breakpointId);
        this.renderBreakpoints();
    }
    
    
    showNotification(message, type = 'info') {
        // Create a toast notification
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
    }
    
    showError(message) {
        this.showNotification(message, 'danger');
    }
}

// Global functions for HTML onclick handlers
function showAddBreakpointModal() {
    new bootstrap.Modal(document.getElementById('addBreakpointModal')).show();
}

function addBreakpoint() {
    const form = document.getElementById('breakpoint-form');
    const formData = new FormData(form);
    
    const data = {
        breakpoint_type: document.getElementById('breakpoint-type').value,
        tool_name: document.getElementById('tool-name').value || null,
        agent_id: document.getElementById('agent-id').value || null,
        temporary: document.getElementById('temporary-breakpoint').checked
    };
    
    fetch('/api/breakpoints', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            bootstrap.Modal.getInstance(document.getElementById('addBreakpointModal')).hide();
            form.reset();
            app.refreshBreakpoints();
            app.showNotification('Breakpoint added successfully', 'success');
        } else {
            app.showError('Failed to add breakpoint');
        }
    })
    .catch(error => {
        console.error('Error adding breakpoint:', error);
        app.showError('Failed to add breakpoint');
    });
}


function clearAllBreakpoints() {
    if (confirm('Are you sure you want to clear all breakpoints?')) {
        app.breakpoints.forEach(bp => {
            fetch('/api/breakpoints', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ breakpoint_id: bp.id })
            });
        });
        app.refreshBreakpoints();
    }
}


function exportTrace() {
    fetch('/api/export?format=json')
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                app.showNotification(`Trace exported to ${result.filename}`, 'success');
            } else {
                app.showError('Failed to export trace');
            }
        })
        .catch(error => {
            console.error('Error exporting trace:', error);
            app.showError('Failed to export trace');
        });
}

function refreshAllData() {
    app.refreshAgents();
    app.refreshEvents();
    app.refreshBreakpoints();
    app.showNotification('All data refreshed', 'success');
}

function cleanupDebugger() {
    if (confirm('Are you sure you want to clean all debugger memory? This will clear all agents, events, and breakpoints.')) {
        fetch('/api/cleanup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                app.showNotification('Debugger memory cleaned successfully', 'success');
                // Refresh all data to show empty state
                app.refreshAgents();
                app.refreshEvents();
                app.refreshBreakpoints();
            } else {
                app.showError('Failed to clean debugger memory');
            }
        })
        .catch(error => {
            console.error('Error cleaning debugger:', error);
            app.showError('Failed to clean debugger memory');
        });
    }
}

function refreshAgents() {
    app.refreshAgents();
}

function refreshEvents() {
    app.refreshEvents();
}

// Initialize the application
const app = new AgentDebuggerApp();
