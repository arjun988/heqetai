"""
Performance monitoring utilities for AgentDebugger.
"""

import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque


class PerformanceMonitor:
    """Enhanced monitor and analyzer for agent performance metrics"""

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history

        # Core performance metrics
        self.metrics: Dict[str, deque] = {
            "tool_execution_times": deque(maxlen=max_history),
            "llm_response_times": deque(maxlen=max_history),
            "memory_access_times": deque(maxlen=max_history),
            "reasoning_times": deque(maxlen=max_history),
            "total_response_times": deque(maxlen=max_history),
            "context_retrieval_times": deque(maxlen=max_history),
            "error_rates": deque(maxlen=max_history),
            "throughput": deque(maxlen=max_history),
        }

        # Agent-specific metrics
        self.agent_metrics: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: {
                "task_completion_times": deque(maxlen=max_history),
                "error_count": deque(maxlen=max_history),
                "memory_usage": deque(maxlen=max_history),
                "tool_usage_count": deque(maxlen=max_history),
                "llm_call_count": deque(maxlen=max_history),
                "efficiency_score": deque(maxlen=max_history),
            }
        )

        # System metrics
        self.system_metrics: Dict[str, deque] = {
            "cpu_usage": deque(maxlen=max_history),
            "memory_usage": deque(maxlen=max_history),
            "disk_io": deque(maxlen=max_history),
            "network_io": deque(maxlen=max_history),
            "active_connections": deque(maxlen=max_history),
        }

        # Memory tracking
        self.memory_metrics: Dict[str, deque] = {
            "context_size": deque(maxlen=max_history),
            "agent_memory_size": deque(maxlen=max_history),
            "total_memory_usage": deque(maxlen=max_history),
            "memory_growth_rate": deque(maxlen=max_history),
        }

        # Note: Sample data generation removed - using real performance data only

        # Timing tracking
        self.start_times: Dict[str, datetime] = {}
        self.session_start = datetime.now()

        # Performance alerts
        self.alerts: List[Dict[str, Any]] = []
        self.alert_thresholds = {
            "high_cpu_usage": 80.0,
            "high_memory_usage": 85.0,
            "slow_response_time": 5.0,
            "high_error_rate": 0.1,
        }

    def start_timing(self, event_type: str, event_id: str, agent_id: str = None):
        """Start timing for a specific event"""
        self.start_times[event_id] = {
            "start_time": datetime.now(),
            "event_type": event_type,
            "agent_id": agent_id,
        }

    def end_timing(self, event_id: str) -> Optional[float]:
        """End timing and return duration"""
        if event_id in self.start_times:
            timing_info = self.start_times[event_id]
            duration = (datetime.now() - timing_info["start_time"]).total_seconds()

            # Record the metric
            self.record_metric(timing_info["event_type"], duration)

            # Record agent-specific metric if available
            if timing_info["agent_id"]:
                self.record_agent_metric(
                    timing_info["agent_id"], timing_info["event_type"], duration
                )

            del self.start_times[event_id]
            return duration
        return None

    def record_metric(self, metric_type: str, value: float):
        """Record a performance metric"""
        if metric_type in self.metrics:
            self.metrics[metric_type].append(value)

            # Check for performance alerts
            self._check_performance_alerts(metric_type, value)

    def record_agent_metric(self, agent_id: str, metric_type: str, value: float):
        """Record agent-specific metric"""
        if metric_type in self.agent_metrics[agent_id]:
            self.agent_metrics[agent_id][metric_type].append(value)

    def record_system_metric(self, metric_type: str, value: float):
        """Record system-level metric"""
        if metric_type in self.system_metrics:
            self.system_metrics[metric_type].append(value)

    def record_memory_metric(self, metric_type: str, value: float):
        """Record memory-related metric"""
        if metric_type in self.memory_metrics:
            self.memory_metrics[metric_type].append(value)

    def update_system_metrics(self):
        """Update system metrics from psutil"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.record_system_metric("cpu_usage", cpu_percent)

            # Memory usage
            memory = psutil.virtual_memory()
            self.record_system_metric("memory_usage", memory.percent)

            # Disk I/O
            disk_io = psutil.disk_io_counters()
            if disk_io:
                self.record_system_metric(
                    "disk_io", disk_io.read_bytes + disk_io.write_bytes
                )

            # Network I/O
            network_io = psutil.net_io_counters()
            if network_io:
                self.record_system_metric(
                    "network_io", network_io.bytes_sent + network_io.bytes_recv
                )

            # Active connections
            connections = len(psutil.net_connections())
            self.record_system_metric("active_connections", connections)

        except Exception as e:
            print(f"Error updating system metrics: {e}")

    def calculate_efficiency_score(self, agent_id: str) -> float:
        """Calculate agent efficiency score based on multiple factors"""
        if agent_id not in self.agent_metrics:
            return 0.0

        agent_data = self.agent_metrics[agent_id]

        # Factors: task completion rate, error rate, response time
        task_completion_rate = len(agent_data["task_completion_times"]) / max(
            1, len(agent_data["error_count"])
        )
        error_rate = sum(agent_data["error_count"]) / max(
            1, len(agent_data["error_count"])
        )
        avg_response_time = sum(agent_data["task_completion_times"]) / max(
            1, len(agent_data["task_completion_times"])
        )

        # Efficiency score (0-100)
        efficiency = (
            (task_completion_rate * 40)
            + ((1 - error_rate) * 30)
            + (max(0, 10 - avg_response_time) * 3)
        )
        return min(100, max(0, efficiency))

    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        stats = {
            "core_metrics": self._get_metric_stats(self.metrics),
            "agent_metrics": {},
            "system_metrics": self._get_metric_stats(self.system_metrics),
            "memory_metrics": self._get_metric_stats(self.memory_metrics),
            "session_info": {
                "session_duration": (
                    datetime.now() - self.session_start
                ).total_seconds(),
                "total_events": sum(len(metrics) for metrics in self.metrics.values()),
                "active_agents": len(self.agent_metrics),
            },
            "alerts": self.alerts[-10:],  # Last 10 alerts
            "performance_trends": self._calculate_trends(),
        }

        # Add agent-specific stats
        for agent_id, agent_data in self.agent_metrics.items():
            stats["agent_metrics"][agent_id] = {
                "metrics": self._get_metric_stats(agent_data),
                "efficiency_score": self.calculate_efficiency_score(agent_id),
                "total_tasks": len(agent_data["task_completion_times"]),
                "total_errors": sum(agent_data["error_count"]),
                "avg_memory_usage": sum(agent_data["memory_usage"])
                / max(1, len(agent_data["memory_usage"])),
            }

        return stats

    def _get_metric_stats(
        self, metrics_dict: Dict[str, deque]
    ) -> Dict[str, Dict[str, float]]:
        """Get statistics for a metrics dictionary"""
        stats = {}
        for metric_type, values in metrics_dict.items():
            if values:
                values_list = list(values)
                stats[metric_type] = {
                    "count": len(values_list),
                    "mean": sum(values_list) / len(values_list),
                    "max": max(values_list),
                    "min": min(values_list),
                    "latest": values_list[-1] if values_list else 0,
                    "median": (
                        sorted(values_list)[len(values_list) // 2] if values_list else 0
                    ),
                }
            else:
                stats[metric_type] = {
                    "count": 0,
                    "mean": 0,
                    "max": 0,
                    "min": 0,
                    "latest": 0,
                    "median": 0,
                }
        return stats

    def _calculate_trends(self) -> Dict[str, str]:
        """Calculate performance trends"""
        trends = {}

        # Calculate trends for core metrics
        for metric_name, values in self.metrics.items():
            if len(values) >= 10:
                recent_avg = sum(list(values)[-5:]) / 5
                older_avg = sum(list(values)[-10:-5]) / 5

                if recent_avg > older_avg * 1.1:
                    trends[metric_name] = "increasing"
                elif recent_avg < older_avg * 0.9:
                    trends[metric_name] = "decreasing"
                else:
                    trends[metric_name] = "stable"

        return trends

    def _check_performance_alerts(self, metric_type: str, value: float):
        """Check for performance alerts and add them if thresholds are exceeded"""
        alert_triggered = False
        alert_message = ""

        if (
            metric_type == "cpu_usage"
            and value > self.alert_thresholds["high_cpu_usage"]
        ):
            alert_triggered = True
            alert_message = f"High CPU usage: {value:.1f}%"
        elif (
            metric_type == "memory_usage"
            and value > self.alert_thresholds["high_memory_usage"]
        ):
            alert_triggered = True
            alert_message = f"High memory usage: {value:.1f}%"
        elif (
            metric_type in ["tool_execution_times", "llm_response_times"]
            and value > self.alert_thresholds["slow_response_time"]
        ):
            alert_triggered = True
            alert_message = f"Slow {metric_type}: {value:.2f}s"
        elif (
            metric_type == "error_rates"
            and value > self.alert_thresholds["high_error_rate"]
        ):
            alert_triggered = True
            alert_message = f"High error rate: {value:.2f}"

        if alert_triggered:
            self.alerts.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "type": "performance_alert",
                    "metric": metric_type,
                    "value": value,
                    "message": alert_message,
                    "severity": (
                        "warning"
                        if value < self.alert_thresholds.get(metric_type, 0) * 1.5
                        else "critical"
                    ),
                }
            )

    def get_chart_data(
        self, metric_type: str, time_range_minutes: int = 60
    ) -> Dict[str, Any]:
        """Get data formatted for charts"""
        cutoff_time = datetime.now() - timedelta(minutes=time_range_minutes)

        if metric_type in self.metrics:
            values = list(self.metrics[metric_type])
            timestamps = [
                self.session_start + timedelta(seconds=i * 10)
                for i in range(len(values))
            ]
        elif metric_type in self.system_metrics:
            values = list(self.system_metrics[metric_type])
            timestamps = [
                self.session_start + timedelta(seconds=i * 10)
                for i in range(len(values))
            ]
        elif metric_type in self.memory_metrics:
            values = list(self.memory_metrics[metric_type])
            timestamps = [
                self.session_start + timedelta(seconds=i * 10)
                for i in range(len(values))
            ]
        else:
            return {"labels": [], "datasets": []}

        result = {
            "labels": [ts.strftime("%H:%M:%S") for ts in timestamps],
            "datasets": [
                {
                    "label": metric_type.replace("_", " ").title(),
                    "data": values,
                    "borderColor": self._get_metric_color(metric_type),
                    "backgroundColor": self._get_metric_color(metric_type, alpha=0.1),
                    "tension": 0.1,
                }
            ],
        }

        return result

    def _get_metric_color(self, metric_type: str, alpha: float = 1.0) -> str:
        """Get color for metric type"""
        colors = {
            "tool_execution_times": f"rgba(40, 167, 69, {alpha})",
            "llm_response_times": f"rgba(255, 193, 7, {alpha})",
            "memory_access_times": f"rgba(23, 162, 184, {alpha})",
            "reasoning_times": f"rgba(111, 66, 193, {alpha})",
            "cpu_usage": f"rgba(220, 53, 69, {alpha})",
            "memory_usage": f"rgba(255, 87, 34, {alpha})",
            "error_rates": f"rgba(220, 53, 69, {alpha})",
            "throughput": f"rgba(40, 167, 69, {alpha})",
        }
        return colors.get(metric_type, f"rgba(108, 117, 125, {alpha})")

    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get basic performance statistics (backward compatibility)"""
        return self._get_metric_stats(self.metrics)

    def cleanup_old_data(self, max_age_hours: int = 24):
        """Clean up old performance data"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        # Clean up old alerts
        self.alerts = [
            alert
            for alert in self.alerts
            if datetime.fromisoformat(alert["timestamp"]) > cutoff_time
        ]

        # Note: deque automatically handles maxlen, so no manual cleanup needed
