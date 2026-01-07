"""
Performance tests for the AgentDebugger performance monitoring.
"""

import time
from unittest.mock import Mock, patch

import pytest

from agent_debugger import EventType, PerformanceMonitor, TraceEvent


class TestPerformanceMonitor:
    """Test the PerformanceMonitor class."""

    @pytest.fixture
    def performance_monitor(self):
        """Create a performance monitor instance."""
        return PerformanceMonitor()

    def test_performance_monitor_initialization(self):
        """Test performance monitor initialization."""
        monitor = PerformanceMonitor()

        assert monitor.event_count == 0
        assert len(monitor.execution_times) == 0
        assert len(monitor.memory_usage) == 0
        assert monitor.start_time is not None

    def test_record_event_performance(self, performance_monitor):
        """Test recording event performance."""
        event = TraceEvent(
            event_type=EventType.TOOL_CALL,
            agent_id="test_agent",
            data={"tool": "web_search"},
        )

        performance_monitor.record_event(event)

        assert performance_monitor.event_count == 1
        assert len(performance_monitor.execution_times) == 1

    def test_start_operation(self, performance_monitor):
        """Test starting an operation timing."""
        operation_id = performance_monitor.start_operation("test_operation")

        assert operation_id in performance_monitor.active_operations
        assert "start_time" in performance_monitor.active_operations[operation_id]

    def test_end_operation(self, performance_monitor):
        """Test ending an operation timing."""
        operation_id = performance_monitor.start_operation("test_operation")

        # Small delay to simulate operation time
        time.sleep(0.01)

        performance_monitor.end_operation(operation_id)

        assert operation_id not in performance_monitor.active_operations
        assert len(performance_monitor.execution_times) == 1

    def test_end_operation_not_started(self, performance_monitor):
        """Test ending an operation that wasn't started."""
        # Should not raise an error
        performance_monitor.end_operation("nonexistent")

    def test_record_memory_usage(self, performance_monitor):
        """Test recording memory usage."""
        performance_monitor.record_memory_usage(50.5)

        assert len(performance_monitor.memory_usage) == 1
        assert performance_monitor.memory_usage[-1] == 50.5

    def test_get_average_execution_time(self, performance_monitor):
        """Test getting average execution time."""
        # Record some execution times
        performance_monitor.execution_times = [0.1, 0.2, 0.3]

        avg_time = performance_monitor.get_average_execution_time()
        assert avg_time == 0.2

    def test_get_average_execution_time_no_data(self, performance_monitor):
        """Test getting average execution time with no data."""
        avg_time = performance_monitor.get_average_execution_time()
        assert avg_time == 0.0

    def test_get_peak_memory_usage(self, performance_monitor):
        """Test getting peak memory usage."""
        performance_monitor.memory_usage = [10.0, 50.0, 30.0, 60.0, 20.0]

        peak = performance_monitor.get_peak_memory_usage()
        assert peak == 60.0

    def test_get_peak_memory_usage_no_data(self, performance_monitor):
        """Test getting peak memory usage with no data."""
        peak = performance_monitor.get_peak_memory_usage()
        assert peak == 0.0

    def test_get_events_per_second(self, performance_monitor):
        """Test getting events per second rate."""
        # Simulate 10 events over 2 seconds
        performance_monitor.event_count = 10
        with patch.object(performance_monitor, "get_elapsed_time", return_value=2.0):
            eps = performance_monitor.get_events_per_second()
            assert eps == 5.0

    def test_get_elapsed_time(self, performance_monitor):
        """Test getting elapsed time since monitoring started."""
        elapsed = performance_monitor.get_elapsed_time()
        assert elapsed >= 0.0

    def test_reset_monitor(self, performance_monitor):
        """Test resetting the performance monitor."""
        # Add some data
        performance_monitor.record_event(TraceEvent(EventType.TOOL_CALL, "agent", {}))
        performance_monitor.record_memory_usage(50.0)

        performance_monitor.reset()

        assert performance_monitor.event_count == 0
        assert len(performance_monitor.execution_times) == 0
        assert len(performance_monitor.memory_usage) == 0

    def test_get_performance_report(self, performance_monitor):
        """Test getting a comprehensive performance report."""
        # Add some test data
        performance_monitor.record_event(TraceEvent(EventType.TOOL_CALL, "agent1", {}))
        performance_monitor.record_event(
            TraceEvent(EventType.MEMORY_WRITE, "agent1", {})
        )
        performance_monitor.record_memory_usage(45.0)
        performance_monitor.record_memory_usage(50.0)

        report = performance_monitor.get_performance_report()

        assert "total_events" in report
        assert "average_execution_time" in report
        assert "peak_memory_usage" in report
        assert "events_per_second" in report
        assert "elapsed_time" in report
        assert "event_breakdown" in report

        assert report["total_events"] == 2
        assert report["peak_memory_usage"] == 50.0

    def test_performance_monitor_string_representation(self, performance_monitor):
        """Test string representation of performance monitor."""
        str_repr = str(performance_monitor)
        assert "PerformanceMonitor" in str_repr
        assert "events" in str_repr

    @pytest.mark.slow
    def test_performance_under_load(self, performance_monitor):
        """Test performance monitor under load."""
        # Generate many events quickly
        start_time = time.time()
        for i in range(1000):
            event = TraceEvent(
                event_type=EventType.TOOL_CALL,
                agent_id=f"agent_{i % 10}",
                data={"iteration": i},
            )
            performance_monitor.record_event(event)

        end_time = time.time()
        duration = end_time - start_time

        # Should handle 1000 events in reasonable time (< 1 second)
        assert duration < 1.0
        assert performance_monitor.event_count == 1000

    def test_memory_usage_tracking(self, performance_monitor):
        """Test memory usage tracking over time."""
        # Simulate increasing memory usage
        memory_values = [10.0, 20.0, 35.0, 50.0, 45.0, 60.0, 55.0]

        for mem in memory_values:
            performance_monitor.record_memory_usage(mem)

        assert len(performance_monitor.memory_usage) == len(memory_values)
        assert performance_monitor.get_peak_memory_usage() == 60.0

        # Test memory trend calculation
        recent_avg = sum(memory_values[-3:]) / 3
        assert recent_avg == (45.0 + 60.0 + 55.0) / 3

    def test_operation_timing_precision(self, performance_monitor):
        """Test precision of operation timing."""
        operation_id = performance_monitor.start_operation("precise_test")

        # Very short operation
        time.sleep(0.001)  # 1ms

        performance_monitor.end_operation(operation_id)

        # Should record the timing
        assert len(performance_monitor.execution_times) == 1
        execution_time = performance_monitor.execution_times[0]

        # Should be very close to 0.001 seconds (within reasonable precision)
        assert 0.0005 <= execution_time <= 0.002

    def test_concurrent_operations(self, performance_monitor):
        """Test handling multiple concurrent operations."""
        # Start multiple operations
        op1 = performance_monitor.start_operation("op1")
        op2 = performance_monitor.start_operation("op2")
        op3 = performance_monitor.start_operation("op3")

        assert len(performance_monitor.active_operations) == 3

        # End them in different order
        performance_monitor.end_operation(op2)
        performance_monitor.end_operation(op1)
        performance_monitor.end_operation(op3)

        assert len(performance_monitor.active_operations) == 0
        assert len(performance_monitor.execution_times) == 3

    def test_performance_monitor_cleanup(self, performance_monitor):
        """Test cleanup of old performance data."""
        # Add lots of data
        for i in range(100):
            performance_monitor.record_event(
                TraceEvent(EventType.TOOL_CALL, "agent", {})
            )
            performance_monitor.record_memory_usage(float(i))

        # Cleanup old data (keep only last 50)
        performance_monitor.cleanup(max_events=50, max_memory_entries=50)

        assert performance_monitor.event_count <= 50
        assert len(performance_monitor.memory_usage) <= 50

    def test_performance_monitor_export(self, performance_monitor, tmp_path):
        """Test exporting performance data."""
        # Add some data
        performance_monitor.record_event(TraceEvent(EventType.TOOL_CALL, "agent", {}))
        performance_monitor.record_memory_usage(50.0)

        export_path = tmp_path / "performance.json"
        performance_monitor.export_data(str(export_path))

        assert export_path.exists()

        import json

        with open(export_path) as f:
            data = json.load(f)

        assert "event_count" in data
        assert "execution_times" in data
        assert "memory_usage" in data
        assert "start_time" in data
