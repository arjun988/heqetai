"""
Performance monitoring utilities for AgentDebugger.
"""

from datetime import datetime
from typing import Dict, List, Optional


class PerformanceMonitor:
    """Monitor and analyze agent performance metrics"""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {
            'tool_execution_times': [],
            'llm_response_times': [],
            'memory_access_times': [],
            'reasoning_times': []
        }
        self.start_times: Dict[str, datetime] = {}

    def start_timing(self, event_type: str, event_id: str):
        """Start timing for a specific event"""
        self.start_times[event_id] = datetime.now()

    def end_timing(self, event_id: str) -> Optional[float]:
        """End timing and return duration"""
        if event_id in self.start_times:
            duration = (datetime.now() - self.start_times[event_id]).total_seconds()
            del self.start_times[event_id]
            return duration
        return None

    def record_metric(self, metric_type: str, value: float):
        """Record a performance metric"""
        if metric_type in self.metrics:
            self.metrics[metric_type].append(value)

    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics"""
        stats = {}
        for metric_type, values in self.metrics.items():
            if values:
                stats[metric_type] = {
                    'count': len(values),
                    'mean': sum(values) / len(values),
                    'max': max(values),
                    'min': min(values),
                    'latest': values[-1] if values else 0
                }
            else:
                stats[metric_type] = {'count': 0, 'mean': 0, 'max': 0, 'min': 0, 'latest': 0}
        return stats


