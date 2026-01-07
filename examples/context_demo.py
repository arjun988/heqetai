#!/usr/bin/env python3
"""
Context Management Demo for AgentDebugger
Demonstrates the new context engineering and management capabilities.
"""

import time
from datetime import datetime, timedelta

from agent_debugger import AgentDebugger
from agent_debugger.context import ContextPriority, ContextType


class DemoAgent:
    """Simple demo agent for testing context management"""

    def __init__(self, name: str):
        self.name = name
        self.memory = {}
        self.tasks_completed = 0

    def execute_task(self, task_description: str):
        """Simulate task execution"""
        print(f"🤖 {self.name} executing: {task_description}")
        time.sleep(0.5)  # Simulate work

        # Store task in memory
        self.memory[f"task_{self.tasks_completed}"] = task_description
        self.tasks_completed += 1

        return f"Task completed: {task_description}"

    def call_llm(self, prompt: str):
        """Simulate LLM call"""
        print(f"🧠 {self.name} LLM call: {prompt[:50]}...")
        time.sleep(0.3)  # Simulate LLM processing

        response = f"LLM response for: {prompt[:30]}..."
        return response

    def execute_tool(self, tool_name: str, *args, **kwargs):
        """Simulate tool execution"""
        print(f"🔧 {self.name} using tool: {tool_name}")
        time.sleep(0.2)  # Simulate tool execution

        result = f"Tool {tool_name} result with args: {args}"
        return result

    def update_memory(self, key: str, value: str):
        """Update agent memory"""
        self.memory[key] = value
        print(f"💾 {self.name} updated memory: {key} = {value[:30]}...")


def run_context_demo():
    """Run the context management demo"""
    print("🧠 AgentDebugger Context Management Demo")
    print("=" * 50)

    # Create debugger with context management enabled
    debugger = AgentDebugger(
        mode="console",
        enable_context_management=True,
        enable_performance_monitoring=True,
    )

    # Create demo agents
    agent1 = DemoAgent("ResearchBot")
    agent2 = DemoAgent("AnalysisBot")

    # Attach agents to debugger
    debugger.attach(agent1, "research_agent")
    debugger.attach(agent2, "analysis_agent")

    print("\n📝 Adding manual contexts...")

    # Add some manual contexts
    debugger.add_context(
        type=ContextType.USER_PREFERENCE,
        key="user_theme",
        value="dark_mode",
        priority=ContextPriority.HIGH,
        tags=["ui", "preference"],
        metadata={"source": "user_settings", "version": "1.0"},
    )

    debugger.add_context(
        type=ContextType.KNOWLEDGE,
        key="domain_knowledge",
        value="Machine learning and AI research",
        priority=ContextPriority.CRITICAL,
        tags=["knowledge", "domain"],
        agent_id="research_agent",
    )

    debugger.add_context(
        type=ContextType.TASK,
        key="current_project",
        value="Build intelligent research assistant",
        priority=ContextPriority.HIGH,
        tags=["project", "current"],
        metadata={"deadline": "2024-12-31", "priority": "high"},
    )

    print("✅ Manual contexts added")

    print("\n🤖 Running agent tasks to generate auto-captured contexts...")

    # Execute some tasks to generate auto-captured contexts
    agent1.execute_task("Research latest AI trends")
    agent1.call_llm("What are the current trends in artificial intelligence?")
    agent1.execute_tool("web_search", "AI trends 2024")
    agent1.update_memory("research_findings", "AI is advancing rapidly in 2024")

    agent2.execute_task("Analyze research data")
    agent2.call_llm("Analyze the following data: [research data]")
    agent2.execute_tool("data_analysis", "research_data.csv")
    agent2.update_memory("analysis_results", "Data shows positive trends")

    print("\n📊 Context Summary:")
    summary = debugger.get_context_summary()
    print(f"  Total contexts: {summary['total_items']}")
    print(f"  By type: {summary['by_type']}")
    print(f"  By priority: {summary['by_priority']}")
    print(f"  By agent: {summary['by_agent']}")

    print("\n🔍 Searching contexts...")

    # Search for contexts
    search_results = debugger.search_contexts("AI", type_filter=ContextType.KNOWLEDGE)
    print(f"Found {len(search_results)} knowledge contexts containing 'AI':")
    for ctx in search_results:
        print(f"  - {ctx.key}: {str(ctx.value)[:50]}...")

    print("\n📤 Exporting contexts...")

    # Export contexts
    exported_data = debugger.export_contexts(format="json")
    print(f"Exported {len(exported_data)} characters of context data")

    print("\n🎯 Context Management Features Demonstrated:")
    print("  ✅ Automatic context capture from agent activities")
    print("  ✅ Manual context creation with types and priorities")
    print("  ✅ Context search and filtering")
    print("  ✅ Context export/import capabilities")
    print("  ✅ Context summary and statistics")
    print("  ✅ Agent-specific context tracking")
    print("  ✅ Tag-based context organization")

    print("\n🌐 Web Portal Features:")
    print("  ✅ Interactive context management UI")
    print("  ✅ Real-time context updates via WebSocket")
    print("  ✅ Context filtering and search interface")
    print("  ✅ Context import/export through web interface")
    print("  ✅ Context visualization and management")

    print("\n💻 Console Commands Available:")
    print("  ctx, context - Context management menu")
    print("  add_ctx - Add new context item")
    print("  search_ctx <query> - Search contexts")
    print("  list_ctx - List all contexts")
    print("  clear_ctx - Clear contexts with filters")
    print("  export_ctx - Export contexts to file")
    print("  import_ctx - Import contexts from file")

    print("\n🚀 To try the web portal:")
    print("  python -m agent_debugger.web.portal")
    print("  Then visit: http://localhost:5000")
    print("  Navigate to the 'Context' tab to see the context management interface")

    print("\n✨ Context Management Demo Complete!")


if __name__ == "__main__":
    run_context_demo()
