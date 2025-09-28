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
        this.contexts = [];
        this.performanceCharts = {};
        this.performanceData = {};
        this.autoRefreshInterval = null;
        this.refreshInterval = 10000; // 10 seconds
        this.currentTimeRange = 60; // 1 hour
        this.currentMetricType = 'core';
        
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
            this.refreshContexts();
        });
        
        // Context management events
        this.socket.on('context_added', (data) => {
            this.showNotification(`Context added: ${data.key}`, 'success');
            this.refreshContexts();
        });
        
        this.socket.on('context_updated', (data) => {
            this.showNotification(`Context updated: ${data.context_id}`, 'info');
            this.refreshContexts();
        });
        
        this.socket.on('context_deleted', (data) => {
            this.showNotification(`Context deleted: ${data.context_id}`, 'warning');
            this.refreshContexts();
        });
        
        this.socket.on('contexts_imported', (data) => {
            this.showNotification(`${data.count} contexts imported`, 'success');
            this.refreshContexts();
        });
        
        this.socket.on('contexts_cleared', (data) => {
            this.showNotification(`${data.count} contexts cleared`, 'warning');
            this.refreshContexts();
        });
        
        // Performance monitoring events
        this.socket.on('performance_update', (data) => {
            this.handlePerformanceUpdate(data);
        });
        
        this.socket.on('performance_alert', (data) => {
            this.handlePerformanceAlert(data);
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
            
            // Load contexts
            await this.refreshContexts();
            
            // Load performance data
            await this.refreshPerformanceData();
            
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
            this.updatePerformanceSummary(data.performance_summary);
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
    
    async refreshContexts() {
        try {
            const response = await fetch('/api/contexts');
            const contexts = await response.json();
            this.contexts = contexts;
            this.renderContexts();
            this.updateContextSummary();
        } catch (error) {
            console.error('Failed to refresh contexts:', error);
        }
    }
    
    async updateContextSummary() {
        try {
            const response = await fetch('/api/contexts/summary');
            const summary = await response.json();
            this.renderContextSummary(summary);
        } catch (error) {
            console.error('Failed to load context summary:', error);
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
        // Initialize all performance charts
        this.initializePerformanceCharts();
        this.startAutoRefresh();
        
        // Load initial performance data
        this.refreshPerformanceData();
    }
    
    initializePerformanceCharts() {
        const chartConfigs = {
            'tool-execution-chart': {
                type: 'line',
                title: 'Tool Execution Times',
                yAxisLabel: 'Time (seconds)',
                color: '#28a745'
            },
            'llm-response-chart': {
                type: 'line',
                title: 'LLM Response Times',
                yAxisLabel: 'Time (seconds)',
                color: '#ffc107'
            },
            'memory-access-chart': {
                type: 'line',
                title: 'Memory Access Times',
                yAxisLabel: 'Time (seconds)',
                color: '#17a2b8'
            },
            'reasoning-time-chart': {
                type: 'line',
                title: 'Reasoning Times',
                yAxisLabel: 'Time (seconds)',
                color: '#6f42c1'
            },
            'cpu-usage-chart': {
                type: 'line',
                title: 'CPU Usage',
                yAxisLabel: 'Percentage (%)',
                color: '#dc3545'
            },
            'memory-usage-chart': {
                type: 'line',
                title: 'Memory Usage',
                yAxisLabel: 'Percentage (%)',
                color: '#fd7e14'
            },
            'disk-io-chart': {
                type: 'line',
                title: 'Disk I/O',
                yAxisLabel: 'Bytes',
                color: '#20c997'
            },
            'network-io-chart': {
                type: 'line',
                title: 'Network I/O',
                yAxisLabel: 'Bytes',
                color: '#6f42c1'
            },
            'context-size-chart': {
                type: 'line',
                title: 'Context Size',
                yAxisLabel: 'Items',
                color: '#17a2b8'
            },
            'agent-memory-chart': {
                type: 'line',
                title: 'Agent Memory Usage',
                yAxisLabel: 'Items',
                color: '#28a745'
            },
            'total-memory-chart': {
                type: 'line',
                title: 'Total Memory Usage',
                yAxisLabel: 'MB',
                color: '#dc3545'
            },
            'agent-efficiency-chart': {
                type: 'bar',
                title: 'Agent Efficiency Scores',
                yAxisLabel: 'Score (0-100)',
                color: '#28a745'
            },
            'agent-error-rate-chart': {
                type: 'bar',
                title: 'Agent Error Rates',
                yAxisLabel: 'Error Rate',
                color: '#dc3545'
            }
        };
        
        Object.entries(chartConfigs).forEach(([chartId, config]) => {
            const canvas = document.getElementById(chartId);
            if (canvas) {
                this.performanceCharts[chartId] = this.createChart(canvas, config);
            }
        });
    }
    
    createChart(canvas, config) {
        const ctx = canvas.getContext('2d');
        return new Chart(ctx, {
            type: config.type,
            data: {
                labels: [],
                datasets: [{
                    label: config.title,
                    data: [],
                    borderColor: config.color,
                    backgroundColor: config.color + '20',
                    tension: 0.1,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: config.title
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: config.yAxisLabel
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    }
                },
                animation: {
                    duration: 750
                }
            }
        });
    }
    
    async refreshPerformanceData() {
        try {
            const response = await fetch('/api/performance');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            this.performanceData = data;
            this.updateAllCharts();
            this.updatePerformanceSummary();
            this.updatePerformanceAlerts();
        } catch (error) {
            console.error('Failed to refresh performance data:', error);
            // Set empty performance data to show appropriate message
            this.performanceData = null;
            this.updatePerformanceSummary();
        }
    }
    
    updateAllCharts() {
        if (!this.performanceData || !this.performanceData.chart_data) {
            // Clear all charts if no data available
            this.clearAllCharts();
            return;
        }
        
        // Update core performance charts
        this.updateChart('tool-execution-chart', 'tool_execution_times');
        this.updateChart('llm-response-chart', 'llm_response_times');
        this.updateChart('memory-access-chart', 'memory_access_times');
        this.updateChart('reasoning-time-chart', 'reasoning_times');
        
        // Update system metrics charts
        this.updateChart('cpu-usage-chart', 'cpu_usage');
        this.updateChart('memory-usage-chart', 'memory_usage');
        this.updateChart('disk-io-chart', 'disk_io');
        this.updateChart('network-io-chart', 'network_io');
        
        // Update memory metrics charts
        this.updateChart('context-size-chart', 'context_size');
        this.updateChart('agent-memory-chart', 'agent_memory_size');
        this.updateChart('total-memory-chart', 'total_memory_usage');
        
        // Update agent performance charts
        this.updateAgentPerformanceCharts();
    }
    
    clearAllCharts() {
        // Clear all charts by setting empty data
        const chartIds = [
            'tool-execution-chart', 'llm-response-chart', 'memory-access-chart', 'reasoning-time-chart',
            'cpu-usage-chart', 'memory-usage-chart', 'disk-io-chart', 'network-io-chart',
            'context-size-chart', 'agent-memory-chart', 'total-memory-chart',
            'agent-efficiency-chart', 'agent-error-rate-chart'
        ];
        
        chartIds.forEach(chartId => {
            const chart = this.performanceCharts[chartId];
            if (chart) {
                chart.data.labels = [];
                chart.data.datasets[0].data = [];
                chart.update('none');
            }
        });
    }
    
    updateChart(chartId, metricType) {
        const chart = this.performanceCharts[chartId];
        if (!chart) {
            return;
        }
        
        const chartData = this.performanceData.chart_data?.[metricType];
        
        if (!chartData || !chartData.labels || chartData.labels.length === 0) {
            // Initialize with empty data if no data available
            chart.data.labels = [];
            chart.data.datasets[0].data = [];
            chart.update('none');
            return;
        }
        
        chart.data.labels = chartData.labels;
        chart.data.datasets[0].data = chartData.datasets[0].data;
        chart.update('none'); // No animation for real-time updates
    }
    
    updateAgentPerformanceCharts() {
        // Update agent efficiency chart
        const efficiencyChart = this.performanceCharts['agent-efficiency-chart'];
        if (efficiencyChart && this.performanceData.agent_metrics) {
            const agents = Object.keys(this.performanceData.agent_metrics);
            const efficiencyScores = agents.map(agent => 
                this.performanceData.agent_metrics[agent].efficiency_score || 0
            );
            
            efficiencyChart.data.labels = agents;
            efficiencyChart.data.datasets[0].data = efficiencyScores;
            efficiencyChart.update('none');
        }
        
        // Update agent error rate chart
        const errorRateChart = this.performanceCharts['agent-error-rate-chart'];
        if (errorRateChart && this.performanceData.agent_metrics) {
            const agents = Object.keys(this.performanceData.agent_metrics);
            const errorRates = agents.map(agent => {
                const agentData = this.performanceData.agent_metrics[agent];
                return agentData.total_errors / Math.max(1, agentData.total_tasks);
            });
            
            errorRateChart.data.labels = agents;
            errorRateChart.data.datasets[0].data = errorRates;
            errorRateChart.update('none');
        }
    }
    
    updatePerformanceSummary() {
        const container = document.getElementById('performance-summary');
        if (!container) return;
        
        // Handle case when performance data is not available
        if (!this.performanceData) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle"></i>
                    Performance data is not available. Make sure performance monitoring is enabled.
                </div>
            `;
            return;
        }
        
        const sessionInfo = this.performanceData.session_info || {};
        const coreMetrics = this.performanceData.core_metrics || {};
        const systemMetrics = this.performanceData.system_metrics || {};
        
        container.innerHTML = `
            <div class="row">
                <div class="col-md-3">
                    <div class="card bg-primary text-white">
                        <div class="card-body text-center">
                            <h5>${sessionInfo.total_events || 0}</h5>
                            <small>Total Events</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-success text-white">
                        <div class="card-body text-center">
                            <h5>${sessionInfo.active_agents || 0}</h5>
                            <small>Active Agents</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-info text-white">
                        <div class="card-body text-center">
                            <h5>${Math.round((sessionInfo.session_duration || 0) / 60)}m</h5>
                            <small>Session Duration</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-warning text-white">
                        <div class="card-body text-center">
                            <h5>${this.performanceData.alerts?.length || 0}</h5>
                            <small>Active Alerts</small>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mt-3">
                <div class="col-md-6">
                    <h6>Core Performance</h6>
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <tr>
                                <td>Tool Execution (avg):</td>
                                <td>${coreMetrics.tool_execution_times?.mean?.toFixed(2) || '0.00'}s</td>
                            </tr>
                            <tr>
                                <td>LLM Response (avg):</td>
                                <td>${coreMetrics.llm_response_times?.mean?.toFixed(2) || '0.00'}s</td>
                            </tr>
                            <tr>
                                <td>Memory Access (avg):</td>
                                <td>${coreMetrics.memory_access_times?.mean?.toFixed(2) || '0.00'}s</td>
                            </tr>
                        </table>
                    </div>
                </div>
                <div class="col-md-6">
                    <h6>System Metrics</h6>
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <tr>
                                <td>CPU Usage:</td>
                                <td>${systemMetrics.cpu_usage?.latest?.toFixed(1) || '0.0'}%</td>
                            </tr>
                            <tr>
                                <td>Memory Usage:</td>
                                <td>${systemMetrics.memory_usage?.latest?.toFixed(1) || '0.0'}%</td>
                            </tr>
                            <tr>
                                <td>Active Connections:</td>
                                <td>${systemMetrics.active_connections?.latest || 0}</td>
                            </tr>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }
    
    updatePerformanceAlerts() {
        const container = document.getElementById('performance-alerts-container');
        const alertsCard = document.getElementById('performance-alerts-card');
        
        if (!container || !this.performanceData.alerts) return;
        
        const alerts = this.performanceData.alerts;
        
        if (alerts.length === 0) {
            alertsCard.style.display = 'none';
            return;
        }
        
        alertsCard.style.display = 'block';
        container.innerHTML = alerts.map(alert => `
            <div class="alert alert-${alert.severity === 'critical' ? 'danger' : 'warning'} alert-dismissible fade show">
                <strong>${alert.metric}:</strong> ${alert.message}
                <br><small class="text-muted">${new Date(alert.timestamp).toLocaleString()}</small>
            </div>
        `).join('');
    }
    
    startAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        
        this.autoRefreshInterval = setInterval(() => {
            if (this.connected) {
                this.refreshPerformanceData();
            }
        }, this.refreshInterval);
    }
    
    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }
    
    toggleAutoRefresh() {
        const icon = document.getElementById('auto-refresh-icon');
        if (this.autoRefreshInterval) {
            this.stopAutoRefresh();
            icon.className = 'fas fa-play';
        } else {
            this.startAutoRefresh();
            icon.className = 'fas fa-pause';
        }
    }
    
    updateTimeRange() {
        this.currentTimeRange = parseInt(document.getElementById('time-range-select').value);
        this.refreshPerformanceData();
    }
    
    updateMetricType() {
        this.currentMetricType = document.getElementById('metric-type-select').value;
        this.showMetricType(this.currentMetricType);
    }
    
    showMetricType(metricType) {
        // Hide all metric cards
        document.getElementById('core-performance-card').style.display = 'none';
        document.getElementById('system-metrics-card').style.display = 'none';
        document.getElementById('memory-metrics-card').style.display = 'none';
        document.getElementById('agent-performance-card').style.display = 'none';
        
        // Show selected metric card
        switch (metricType) {
            case 'core':
                document.getElementById('core-performance-card').style.display = 'block';
                break;
            case 'system':
                document.getElementById('system-metrics-card').style.display = 'block';
                break;
            case 'memory':
                document.getElementById('memory-metrics-card').style.display = 'block';
                break;
            case 'agents':
                document.getElementById('agent-performance-card').style.display = 'block';
                break;
        }
    }
    
    updateRefreshInterval() {
        this.refreshInterval = parseInt(document.getElementById('refresh-interval').value);
        if (this.autoRefreshInterval) {
            this.startAutoRefresh();
        }
    }
    
    exportPerformanceData() {
        if (!this.performanceData) {
            this.showError('No performance data to export');
            return;
        }
        
        const dataStr = JSON.stringify(this.performanceData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `performance_data_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showNotification('Performance data exported successfully', 'success');
    }
    
    handlePerformanceUpdate(data) {
        // Update performance data with new metrics
        if (data.metrics) {
            this.performanceData = { ...this.performanceData, ...data };
            this.updateAllCharts();
            this.updatePerformanceSummary();
        }
    }
    
    handlePerformanceAlert(alert) {
        // Show performance alert notification
        const severity = alert.severity === 'critical' ? 'danger' : 'warning';
        this.showNotification(`Performance Alert: ${alert.message}`, severity);
        
        // Update alerts display
        this.updatePerformanceAlerts();
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
    
    // Context Management Methods
    
    renderContexts() {
        const container = document.getElementById('contexts-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (this.contexts.length === 0) {
            container.innerHTML = '<p class="text-muted">No contexts found</p>';
            return;
        }
        
        this.contexts.forEach(context => {
            const contextItem = this.createContextItem(context);
            container.appendChild(contextItem);
        });
    }
    
    createContextItem(context) {
        const div = document.createElement('div');
        div.className = 'card mb-3 context-item';
        div.style.cursor = 'pointer';
        div.onclick = () => this.showContextDetails(context);
        
        const priorityClass = this.getPriorityClass(context.priority);
        const typeIcon = this.getTypeIcon(context.type);
        
        div.innerHTML = `
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="card-title">
                            <i class="${typeIcon}"></i>
                            <span class="badge ${priorityClass}">${context.priority}</span>
                            ${context.key}
                        </h6>
                        <p class="card-text">
                            <strong>Type:</strong> ${context.type} | 
                            <strong>Agent:</strong> ${context.agent_id || 'N/A'} |
                            <strong>Created:</strong> ${new Date(context.created_at).toLocaleString()}
                        </p>
                        <div class="context-preview">
                            ${this.truncateText(context.value, 100)}
                        </div>
                        ${context.tags && context.tags.length > 0 ? `
                            <div class="mt-2">
                                ${context.tags.map(tag => `<span class="badge bg-secondary me-1">${tag}</span>`).join('')}
                            </div>
                        ` : ''}
                    </div>
                    <div class="btn-group-vertical" role="group">
                        <button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); app.editContext('${context.id}')">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="event.stopPropagation(); app.deleteContext('${context.id}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        return div;
    }
    
    getPriorityClass(priority) {
        const classMap = {
            'critical': 'bg-danger',
            'high': 'bg-warning',
            'medium': 'bg-info',
            'low': 'bg-secondary',
            'archive': 'bg-dark'
        };
        return classMap[priority] || 'bg-secondary';
    }
    
    getTypeIcon(type) {
        const iconMap = {
            'memory': 'fas fa-memory',
            'conversation': 'fas fa-comments',
            'knowledge': 'fas fa-brain',
            'task': 'fas fa-tasks',
            'environment': 'fas fa-globe',
            'user_preference': 'fas fa-user-cog',
            'system_state': 'fas fa-cogs'
        };
        return iconMap[type] || 'fas fa-info-circle';
    }
    
    truncateText(text, maxLength) {
        if (typeof text !== 'string') {
            text = JSON.stringify(text);
        }
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    }
    
    renderContextSummary(summary) {
        const container = document.getElementById('context-summary');
        if (!container) return;
        
        container.innerHTML = `
            <div class="row">
                <div class="col-md-3">
                    <strong>Total Items:</strong> ${summary.total_items || 0}
                </div>
                <div class="col-md-3">
                    <strong>By Type:</strong> ${Object.entries(summary.by_type || {}).map(([type, count]) => `${type}: ${count}`).join(', ')}
                </div>
                <div class="col-md-3">
                    <strong>By Priority:</strong> ${Object.entries(summary.by_priority || {}).map(([priority, count]) => `${priority}: ${count}`).join(', ')}
                </div>
                <div class="col-md-3">
                    <strong>Expired:</strong> ${summary.expired_count || 0}
                </div>
            </div>
        `;
    }
    
    showContextDetails(context) {
        const modalContent = `
            <div class="row">
                <div class="col-md-6">
                    <h6><i class="fas fa-info-circle"></i> Context Details</h6>
                    <div class="json-viewer">${JSON.stringify({
                        id: context.id,
                        type: context.type,
                        key: context.key,
                        priority: context.priority,
                        agent_id: context.agent_id,
                        step_id: context.step_id,
                        created_at: context.created_at,
                        updated_at: context.updated_at,
                        expires_at: context.expires_at,
                        tags: context.tags,
                        metadata: context.metadata
                    }, null, 2)}</div>
                </div>
                <div class="col-md-6">
                    <h6><i class="fas fa-file-alt"></i> Value</h6>
                    <div class="json-viewer" style="max-height: 400px; overflow-y: auto;">
                        ${typeof context.value === 'string' ? context.value : JSON.stringify(context.value, null, 2)}
                    </div>
                </div>
            </div>
        `;
        
        document.getElementById('event-detail-content').innerHTML = modalContent;
        new bootstrap.Modal(document.getElementById('eventDetailModal')).show();
    }
    
    async editContext(contextId) {
        const context = this.contexts.find(c => c.id === contextId);
        if (!context) return;
        
        // Populate edit form (could be a separate modal)
        document.getElementById('context-type').value = context.type;
        document.getElementById('context-priority').value = context.priority;
        document.getElementById('context-key').value = context.key;
        document.getElementById('context-value').value = typeof context.value === 'string' ? context.value : JSON.stringify(context.value);
        document.getElementById('context-tags').value = context.tags ? context.tags.join(', ') : '';
        document.getElementById('context-agent').value = context.agent_id || '';
        document.getElementById('context-metadata').value = context.metadata ? JSON.stringify(context.metadata) : '';
        
        // Show modal
        new bootstrap.Modal(document.getElementById('addContextModal')).show();
        
        // Store context ID for update
        document.getElementById('addContextModal').dataset.contextId = contextId;
    }
    
    async deleteContext(contextId) {
        if (!confirm('Are you sure you want to delete this context?')) return;
        
        try {
            const response = await fetch('/api/contexts', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ context_id: contextId })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showNotification('Context deleted successfully', 'success');
                this.refreshContexts();
            } else {
                this.showError(`Failed to delete context: ${result.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error deleting context:', error);
            this.showError('Failed to delete context');
        }
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

// Context Management Global Functions

function showAddContextModal() {
    // Clear form
    document.getElementById('context-form').reset();
    document.getElementById('addContextModal').dataset.contextId = '';
    
    // Populate agent dropdown
    populateAgentDropdown('context-agent');
    
    new bootstrap.Modal(document.getElementById('addContextModal')).show();
}

function showImportContextModal() {
    new bootstrap.Modal(document.getElementById('importContextModal')).show();
}

function showClearContextModal() {
    // Populate agent dropdown for clear modal
    populateAgentDropdown('clear-agent-filter');
    
    new bootstrap.Modal(document.getElementById('clearContextModal')).show();
}

function populateAgentDropdown(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;
    
    // Clear existing options except first
    select.innerHTML = '<option value="">All Agents</option>';
    
    // Add agents from app.agents
    Object.keys(app.agents).forEach(agentId => {
        const option = document.createElement('option');
        option.value = agentId;
        option.textContent = agentId;
        select.appendChild(option);
    });
}

function addContext() {
    const form = document.getElementById('context-form');
    const contextId = document.getElementById('addContextModal').dataset.contextId;
    
    const data = {
        type: document.getElementById('context-type').value,
        key: document.getElementById('context-key').value,
        value: document.getElementById('context-value').value,
        priority: document.getElementById('context-priority').value,
        tags: document.getElementById('context-tags').value.split(',').map(tag => tag.trim()).filter(tag => tag),
        agent_id: document.getElementById('context-agent').value || null,
        metadata: {}
    };
    
    // Parse metadata if provided
    const metadataText = document.getElementById('context-metadata').value.trim();
    if (metadataText) {
        try {
            data.metadata = JSON.parse(metadataText);
        } catch (e) {
            app.showError('Invalid JSON in metadata field');
            return;
        }
    }
    
    const url = contextId ? '/api/contexts' : '/api/contexts';
    const method = contextId ? 'PUT' : 'POST';
    
    if (contextId) {
        data.context_id = contextId;
    }
    
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            bootstrap.Modal.getInstance(document.getElementById('addContextModal')).hide();
            form.reset();
            app.refreshContexts();
            app.showNotification(contextId ? 'Context updated successfully' : 'Context added successfully', 'success');
        } else {
            app.showError(`Failed to ${contextId ? 'update' : 'add'} context: ${result.error || 'Unknown error'}`);
        }
    })
    .catch(error => {
        console.error(`Error ${contextId ? 'updating' : 'adding'} context:`, error);
        app.showError(`Failed to ${contextId ? 'update' : 'add'} context`);
    });
}

function importContexts() {
    const fileInput = document.getElementById('context-file');
    const format = document.getElementById('import-format').value;
    
    if (!fileInput.files[0]) {
        app.showError('Please select a file');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('format', format);
    
    fetch('/api/contexts/import', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            bootstrap.Modal.getInstance(document.getElementById('importContextModal')).hide();
            app.showNotification(`${result.imported_count} contexts imported successfully`, 'success');
            app.refreshContexts();
        } else {
            app.showError(`Failed to import contexts: ${result.error || 'Unknown error'}`);
        }
    })
    .catch(error => {
        console.error('Error importing contexts:', error);
        app.showError('Failed to import contexts');
    });
}

function clearContexts() {
    const typeFilter = document.getElementById('clear-type-filter').value;
    const agentFilter = document.getElementById('clear-agent-filter').value;
    const tagFilter = document.getElementById('clear-tag-filter').value.split(',').map(tag => tag.trim()).filter(tag => tag);
    
    const data = {};
    if (typeFilter) data.type = typeFilter;
    if (agentFilter) data.agent_id = agentFilter;
    if (tagFilter.length > 0) data.tags = tagFilter;
    
    fetch('/api/contexts/clear', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            bootstrap.Modal.getInstance(document.getElementById('clearContextModal')).hide();
            app.showNotification(`${result.cleared_count} contexts cleared successfully`, 'warning');
            app.refreshContexts();
        } else {
            app.showError(`Failed to clear contexts: ${result.error || 'Unknown error'}`);
        }
    })
    .catch(error => {
        console.error('Error clearing contexts:', error);
        app.showError('Failed to clear contexts');
    });
}

function exportContexts() {
    const format = prompt('Export format (json/csv):', 'json');
    if (!format) return;
    
    let url = `/api/contexts/export?format=${format}`;
    
    // Add current filters if any
    const typeFilter = document.getElementById('context-type-filter')?.value;
    const agentFilter = document.getElementById('context-agent-filter')?.value;
    const tagFilter = document.getElementById('context-tag-filter')?.value;
    
    if (typeFilter) url += `&type=${typeFilter}`;
    if (agentFilter) url += `&agent_id=${agentFilter}`;
    if (tagFilter) url += `&tags=${tagFilter}`;
    
    fetch(url)
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            // Download the data
            const blob = new Blob([result.data], { type: 'application/octet-stream' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `contexts_export_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            app.showNotification('Contexts exported successfully', 'success');
        } else {
            app.showError(`Failed to export contexts: ${result.error || 'Unknown error'}`);
        }
    })
    .catch(error => {
        console.error('Error exporting contexts:', error);
        app.showError('Failed to export contexts');
    });
}

function filterContexts() {
    const query = document.getElementById('context-search').value;
    const typeFilter = document.getElementById('context-type-filter').value;
    const priorityFilter = document.getElementById('context-priority-filter').value;
    const agentFilter = document.getElementById('context-agent-filter').value;
    const tagFilter = document.getElementById('context-tag-filter').value;
    
    let url = '/api/contexts?';
    const params = new URLSearchParams();
    
    if (query) params.append('query', query);
    if (typeFilter) params.append('type', typeFilter);
    if (priorityFilter) params.append('priority', priorityFilter);
    if (agentFilter) params.append('agent_id', agentFilter);
    if (tagFilter) {
        tagFilter.split(',').forEach(tag => params.append('tags', tag.trim()));
    }
    
    url += params.toString();
    
    fetch(url)
    .then(response => response.json())
    .then(contexts => {
        app.contexts = contexts;
        app.renderContexts();
    })
    .catch(error => {
        console.error('Error filtering contexts:', error);
        app.showError('Failed to filter contexts');
    });
}

// Initialize the application
const app = new AgentDebuggerApp();
