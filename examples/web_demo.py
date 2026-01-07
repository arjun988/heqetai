"""
AgentDebugger Web Portal Demo
=============================

Demonstrates how to use the AgentDebugger framework with the web portal interface.
This creates a sample agent and shows how to attach the web debugger.
"""

import time
import threading
from datetime import datetime
from typing import Any, Dict
import random

# Import the web portal and existing debugger
from agent_debugger.web import WebPortalDebugger, attach_agent_to_web, socketio, app
from agent_debugger import EventType, TraceEvent
from agent_debugger.context import ContextType, ContextPriority


class DemoAgent:
    """A simple demo agent that simulates various operations"""

    def __init__(self, name: str):
        self.name = name
        self.memory = {}
        self.tools = ["web_search", "calculator", "file_read", "database_query"]

    def execute_tool(self, tool_name: str, input_data: str) -> str:
        """Simulate tool execution"""
        print(f"🔧 {self.name} executing tool: {tool_name} with input: {input_data}")

        # Simulate processing time
        time.sleep(random.uniform(0.5, 2.0))

        # Simulate different outcomes
        if random.random() < 0.1:  # 10% chance of error
            raise Exception(f"Simulated error in {tool_name}")

        # Generate mock responses
        responses = {
            "web_search": f"Found 5 results for '{input_data}'",
            "calculator": f"Result: {random.randint(1, 1000)}",
            "file_read": f"File content: {input_data}_content",
            "database_query": f"Query returned {random.randint(1, 50)} rows",
        }

        return responses.get(tool_name, f"Tool {tool_name} executed successfully")

    def call_llm(self, prompt: str) -> str:
        """Simulate LLM call"""
        print(f"🧠 {self.name} calling LLM with prompt: {prompt[:50]}...")

        # Simulate processing time
        time.sleep(random.uniform(1.0, 3.0))

        responses = [
            "I understand the task and will proceed step by step.",
            "Let me analyze this problem and break it down.",
            "Based on the information provided, I recommend...",
            "I need to gather more information using the available tools.",
            "The solution involves multiple steps that I'll execute sequentially.",
        ]

        return random.choice(responses)

    def update_memory(self, key: str, value: Any):
        """Update agent memory"""
        print(f"📚 {self.name} updating memory: {key} = {value}")
        self.memory[key] = value

    def execute_task(self, task_description: str) -> str:
        """Execute a complete task"""
        print(f"🎯 {self.name} starting task: {task_description}")

        # Simulate reasoning
        reasoning = self.call_llm(
            f"How should I approach this task: {task_description}"
        )

        # Update memory with task
        self.update_memory("current_task", task_description)
        self.update_memory("reasoning", reasoning)

        # Execute tools
        tools_to_use = random.sample(self.tools, random.randint(1, 3))
        results = []

        for tool in tools_to_use:
            try:
                result = self.execute_tool(tool, f"input_for_{tool}")
                results.append(f"{tool}: {result}")
                self.update_memory(f"{tool}_result", result)
            except Exception as e:
                print(f"❌ Error in {tool}: {e}")
                results.append(f"{tool}: ERROR - {e}")

        # Final LLM call to summarize
        final_response = self.call_llm(f"Summarize the results: {'; '.join(results)}")

        # Update memory with final result
        self.update_memory("task_result", final_response)

        print(f"✅ {self.name} completed task: {task_description}")
        return final_response


def simulate_agent_activity(agent, agent_id: str, debugger: WebPortalDebugger):
    """Simulate continuous agent activity for demonstration with performance monitoring"""
    tasks = [
        "Analyze market trends for Q4",
        "Research competitor strategies",
        "Generate monthly report",
        "Process customer feedback",
        "Optimize workflow efficiency",
        "Review security protocols",
        "Update documentation",
        "Plan team meeting agenda",
    ]

    # Wait for debugger to be ready
    max_wait = 10  # seconds
    wait_time = 0
    while (
        not debugger
        or not hasattr(debugger, "performance_monitor")
        or not debugger.performance_monitor
    ) and wait_time < max_wait:
        time.sleep(1)
        wait_time += 1
        print(f"⏳ Waiting for debugger to be ready... ({wait_time}s)")

    if wait_time >= max_wait:
        print(
            f"⚠️ Debugger not ready after {max_wait}s, continuing without performance monitoring"
        )

    task_count = 0
    while task_count < 20:  # Run 20 tasks for demo
        try:
            task = random.choice(tasks)
            print(f"\n🔄 Starting task {task_count + 1}: {task}")

            # Record performance metrics
            start_time = time.time()

            # Execute the task
            result = agent.execute_task(task)

            # Record completion metrics
            completion_time = time.time() - start_time

            # Update performance monitor with metrics
            if (
                debugger
                and hasattr(debugger, "performance_monitor")
                and debugger.performance_monitor
            ):
                debugger.performance_monitor.record_metric(
                    "total_response_times", completion_time
                )
                debugger.performance_monitor.record_agent_metric(
                    agent_id, "task_completion_times", completion_time
                )
                debugger.performance_monitor.record_agent_metric(
                    agent_id, "tool_usage_count", len(agent.tools)
                )
                debugger.performance_monitor.record_agent_metric(
                    agent_id, "memory_usage", len(agent.memory)
                )

                # Simulate some performance variations
                if random.random() < 0.1:  # 10% chance of slow performance
                    debugger.performance_monitor.record_metric(
                        "tool_execution_times", random.uniform(3, 8)
                    )
                else:
                    debugger.performance_monitor.record_metric(
                        "tool_execution_times", random.uniform(0.5, 2.0)
                    )

                if random.random() < 0.05:  # 5% chance of error
                    debugger.performance_monitor.record_metric("error_rates", 0.1)
                    debugger.performance_monitor.record_agent_metric(
                        agent_id, "error_count", 1
                    )
                else:
                    debugger.performance_monitor.record_metric("error_rates", 0.0)
                    debugger.performance_monitor.record_agent_metric(
                        agent_id, "error_count", 0
                    )

            print(
                f"📊 Task {task_count + 1} completed in {completion_time:.2f}s: {result[:100]}..."
            )
            task_count += 1

            # Wait between tasks
            time.sleep(random.uniform(1, 3))

        except Exception as e:
            print(f"❌ Task {task_count + 1} failed: {e}")
            task_count += 1

            # Record error metrics
            if (
                debugger
                and hasattr(debugger, "performance_monitor")
                and debugger.performance_monitor
            ):
                debugger.performance_monitor.record_metric("error_rates", 0.2)
                debugger.performance_monitor.record_agent_metric(
                    agent_id, "error_count", 1
                )


def create_multi_agent_demo():
    """Create multiple agents for demonstration"""
    # Create multiple demo agents
    agents = {
        "research_agent": DemoAgent("Research Agent"),
        "analysis_agent": DemoAgent("Analysis Agent"),
        "report_agent": DemoAgent("Report Agent"),
    }

    # Attach each agent to the web debugger
    debugged_agents = {}
    for agent_id, agent in agents.items():
        print(f"🔧 Attaching {agent_id} to web debugger...")
        debugged_agent = attach_agent_to_web(agent, agent_id, "generic")
        debugged_agents[agent_id] = debugged_agent

    return debugged_agents


def setup_demo_breakpoints(debugger: WebPortalDebugger):
    """Set up some demonstration breakpoints"""
    from agent_debugger import Breakpoint, BreakpointType

    # Break before any tool execution
    debugger.add_breakpoint(
        Breakpoint(
            breakpoint_type=BreakpointType.BEFORE_TOOL,
            metadata={"description": "Demo breakpoint - before tools"},
        )
    )

    # Break on errors
    debugger.add_breakpoint(
        Breakpoint(
            breakpoint_type=BreakpointType.ON_ERROR,
            metadata={"description": "Demo breakpoint - on errors"},
        )
    )

    # Break before LLM calls
    debugger.add_breakpoint(
        Breakpoint(
            breakpoint_type=BreakpointType.BEFORE_LLM,
            metadata={"description": "Demo breakpoint - before LLM"},
        )
    )


def setup_demo_mocks(debugger: WebPortalDebugger):
    """Set up some demonstration mocks"""
    # Mock a tool to always return specific output
    debugger.mock_registry.mock_tool(
        "web_search", "Mock search result: AgentDebugger is awesome!"
    )

    # Mock LLM responses for certain patterns
    debugger.mock_registry.mock_llm(
        "market trends", "Mock LLM response: Market trends are looking positive for Q4."
    )


def setup_demo_contexts(debugger: WebPortalDebugger):
    """Set up demonstration contexts for the web portal"""
    print("🧠 Setting up demo contexts...")

    # Add some manual contexts to demonstrate context management
    debugger.add_context(
        type=ContextType.USER_PREFERENCE,
        key="demo_theme",
        value="dark_mode",
        priority=ContextPriority.HIGH,
        tags=["demo", "ui", "preference"],
        metadata={"source": "demo_setup", "version": "1.0"},
    )

    debugger.add_context(
        type=ContextType.KNOWLEDGE,
        key="domain_expertise",
        value="Business intelligence and data analysis",
        priority=ContextPriority.CRITICAL,
        tags=["knowledge", "domain", "expertise"],
        agent_id="research_agent",
    )

    debugger.add_context(
        type=ContextType.TASK,
        key="current_objective",
        value="Demonstrate AgentDebugger capabilities",
        priority=ContextPriority.HIGH,
        tags=["demo", "objective", "current"],
        metadata={"deadline": "2024-12-31", "priority": "demo"},
    )

    debugger.add_context(
        type=ContextType.ENVIRONMENT,
        key="demo_environment",
        value="Development environment with web portal",
        priority=ContextPriority.MEDIUM,
        tags=["environment", "demo", "development"],
        metadata={"platform": "web", "mode": "demo"},
    )

    debugger.add_context(
        type=ContextType.SYSTEM_STATE,
        key="demo_status",
        value="Active demonstration mode",
        priority=ContextPriority.MEDIUM,
        tags=["system", "demo", "status"],
        metadata={"active": True, "mode": "demonstration"},
    )

    print("✅ Demo contexts added successfully")


def add_dynamic_contexts(debugger: WebPortalDebugger):
    """Add dynamic contexts during demo execution"""
    import time
    import random

    context_templates = [
        {
            "type": ContextType.CONVERSATION,
            "key": "user_query",
            "value": "How can I optimize my workflow?",
            "priority": ContextPriority.MEDIUM,
            "tags": ["conversation", "user", "query"],
        },
        {
            "type": ContextType.KNOWLEDGE,
            "key": "learned_pattern",
            "value": "Users prefer step-by-step instructions",
            "priority": ContextPriority.HIGH,
            "tags": ["learning", "pattern", "user_behavior"],
        },
        {
            "type": ContextType.MEMORY,
            "key": "session_data",
            "value": "Current session: 15 minutes active",
            "priority": ContextPriority.LOW,
            "tags": ["session", "temporary", "runtime"],
        },
        {
            "type": ContextType.SYSTEM_STATE,
            "key": "performance_metric",
            "value": "CPU usage: 45%, Memory: 2.1GB",
            "priority": ContextPriority.MEDIUM,
            "tags": ["performance", "system", "monitoring"],
        },
    ]

    while True:
        try:
            time.sleep(random.uniform(10, 20))  # Add context every 10-20 seconds

            # Pick a random context template
            template = random.choice(context_templates)

            # Add some randomness to the context
            context_key = f"{template['key']}_{int(time.time())}"
            context_value = (
                template["value"]
                + f" (updated at {datetime.now().strftime('%H:%M:%S')})"
            )

            debugger.add_context(
                type=template["type"],
                key=context_key,
                value=context_value,
                priority=template["priority"],
                tags=template["tags"],
                agent_id=random.choice(
                    ["research_agent", "analysis_agent", "report_agent"]
                ),
                metadata={"dynamic": True, "timestamp": datetime.now().isoformat()},
            )

            print(f"🧠 Added dynamic context: {context_key}")

        except Exception as e:
            print(f"❌ Error adding dynamic context: {e}")
            time.sleep(5)


def simulate_performance_monitoring(debugger: WebPortalDebugger):
    """Simulate continuous performance monitoring"""
    # Wait for debugger to be ready
    max_wait = 10  # seconds
    wait_time = 0
    while (
        not debugger
        or not hasattr(debugger, "performance_monitor")
        or not debugger.performance_monitor
    ) and wait_time < max_wait:
        time.sleep(1)
        wait_time += 1
        print(f"⏳ Performance monitor waiting for debugger... ({wait_time}s)")

    if wait_time >= max_wait:
        print(
            f"⚠️ Performance monitor: Debugger not ready after {max_wait}s, continuing without performance monitoring"
        )

    while True:
        try:
            time.sleep(5)  # Update every 5 seconds

            if (
                debugger
                and hasattr(debugger, "performance_monitor")
                and debugger.performance_monitor
            ):
                # Update system metrics
                debugger.performance_monitor.update_system_metrics()

                # Simulate some performance variations
                debugger.performance_monitor.record_metric(
                    "llm_response_times", random.uniform(1.0, 4.0)
                )
                debugger.performance_monitor.record_metric(
                    "memory_access_times", random.uniform(0.1, 0.5)
                )
                debugger.performance_monitor.record_metric(
                    "reasoning_times", random.uniform(0.5, 2.0)
                )
                debugger.performance_monitor.record_metric(
                    "throughput", random.uniform(10, 50)
                )

                # Update memory metrics
                debugger.performance_monitor.record_memory_metric(
                    "context_size", random.randint(50, 200)
                )
                debugger.performance_monitor.record_memory_metric(
                    "agent_memory_size", random.randint(10, 100)
                )
                debugger.performance_monitor.record_memory_metric(
                    "total_memory_usage", random.uniform(100, 500)
                )

                print(f"📊 Performance metrics updated")

        except Exception as e:
            print(f"❌ Error updating performance metrics: {e}")
            time.sleep(5)


def run_web_demo():
    """Run the complete web portal demonstration"""
    print("🌐 Starting AgentDebugger Web Portal Demo")
    print("=" * 50)

    # Clean up any existing debugger state
    try:
        from agent_debugger.web import debugger_instance

        if debugger_instance:
            debugger_instance.cleanup_memory()
            print("✅ Previous debugger state cleaned up")
    except Exception as e:
        print(f"⚠️ Could not clean up previous state: {e}")

    # Create debugged agents
    debugged_agents = create_multi_agent_demo()

    # Get the debugger instance
    from agent_debugger.web import debugger_instance

    if debugger_instance:
        print("🔧 Setting up demo breakpoints...")
        setup_demo_breakpoints(debugger_instance)

        print("🎭 Setting up demo mocks...")
        setup_demo_mocks(debugger_instance)

        print("🧠 Setting up demo contexts...")
        setup_demo_contexts(debugger_instance)

    print("\n📊 Web portal is running at: http://localhost:5000")
    print("🔧 You can:")
    print("  - View real-time agent states")
    print("  - Monitor trace events")
    print("  - Set/remove breakpoints")
    print("  - Add/manage mocks")
    print("  - Export traces")
    print("  - Control agent execution")
    print("  - Manage contexts (NEW!)")
    print("  - Search and filter contexts")
    print("  - Export/import contexts")
    print("  - View context analytics")

    # Start agent activity in separate threads
    threads = []

    # Wait a moment for debugger to be fully initialized
    time.sleep(2)

    for agent_id, agent in debugged_agents.items():
        # Get the debugger instance from the web portal
        from agent_debugger.web import debugger_instance as web_debugger

        thread = threading.Thread(
            target=simulate_agent_activity,
            args=(agent, agent_id, web_debugger),
            daemon=True,
        )
        thread.start()
        threads.append(thread)
        print(f"🤖 Started {agent_id} simulation thread")

    # Start dynamic context generation thread
    from agent_debugger.web import debugger_instance as web_debugger

    if web_debugger:
        context_thread = threading.Thread(
            target=add_dynamic_contexts, args=(web_debugger,), daemon=True
        )
        context_thread.start()
        threads.append(context_thread)
        print("🧠 Started dynamic context generation thread")

        # Start performance monitoring thread
        performance_thread = threading.Thread(
            target=simulate_performance_monitoring, args=(web_debugger,), daemon=True
        )
        performance_thread.start()
        threads.append(performance_thread)
        print("📊 Started performance monitoring thread")

    print(f"\n🎉 Demo is running with {len(debugged_agents)} agents!")
    print("💡 Open http://localhost:5000 in your browser to see the web portal")
    print("🧠 Navigate to the 'Context' tab to see context management features")
    print(
        "📊 Navigate to the 'Performance' tab to see enhanced performance monitoring with:"
    )
    print("   - Real-time charts for core performance metrics")
    print("   - System metrics (CPU, memory, disk, network)")
    print("   - Memory usage tracking")
    print("   - Agent performance analysis")
    print("   - Performance alerts and thresholds")
    print("   - Dynamic chart updates via WebSocket")
    print("⏹️  Press Ctrl+C to stop the demo")

    return threads


if __name__ == "__main__":
    # Start the demo in a separate thread
    demo_thread = threading.Thread(target=run_web_demo, daemon=True)
    demo_thread.start()

    # Wait a moment for demo setup
    time.sleep(2)

    try:
        # Run the Flask app with SocketIO
        print("🚀 Starting Flask server...")
        socketio.run(app, debug=False, host="0.0.0.0", port=5000)
    except KeyboardInterrupt:
        print("\n👋 Demo stopped by user")
    except Exception as e:
        print(f"\n❌ Error running demo: {e}")
