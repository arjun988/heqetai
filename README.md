# 🐛 AgentDebugger Framework

**DevTools for AI Agents** - A revolutionary Python framework for debugging AI agents at runtime with step-by-step visibility and interactive controls.

## 🚀 Quick Start

### Installation

```bash
pip install agentdebugger  # (when published)
# Or clone and install locally:
git clone https://github.com/yourusername/agentdebugger
cd agentdebugger
pip install -e .
```

### Basic Usage

```python
from agentdebugger import AgentDebugger
from your_agent_framework import YourAgent

# Create your agent
agent = YourAgent(name="Assistant", goal="Help users")

# Attach debugger
debugger = AgentDebugger(mode="console")
debugged_agent = debugger.attach(agent)

# Run with debugging enabled
result = debugged_agent.run("Your task here")
```

## 🎯 Core Features

### 1. **Step-by-Step Tracing**
- Monitor every reasoning step, tool call, and memory operation
- View complete LLM prompts and responses
- Track execution flow with parent-child event relationships

### 2. **Interactive Breakpoints**
```python
from agentdebugger import Breakpoint, BreakpointType

# Break before any tool execution
debugger.add_breakpoint(Breakpoint(
    breakpoint_type=BreakpointType.BEFORE_TOOL
))

# Break on specific tool
debugger.add_breakpoint(Breakpoint(
    breakpoint_type=BreakpointType.BEFORE_TOOL,
    tool_name="web_search"
))

# Conditional breakpoint
debugger.add_breakpoint(Breakpoint(
    breakpoint_type=BreakpointType.CONDITIONAL,
    condition=lambda event: "error" in str(event.data).lower()
))
```

### 3. **Interactive Console Commands**
When execution pauses at a breakpoint:

| Command | Description |
|---------|-------------|
| `n`, `next` | Continue to next step |
| `s`, `step` | Step into sub-agent execution |
| `c`, `continue` | Continue without stopping |
| `m`, `memory` | Show current memory state |
| `e`, `edit` | Edit next operation before execution |
| `o`, `override` | Override tool output manually |
| `b`, `breakpoint` | Set new breakpoint |
| `l`, `list` | List all breakpoints |
| `trace` | Show execution trace |
| `state` | Show complete agent state |
| `h`, `help` | Show help message |
| `q`, `quit` | Exit debugger |

### 4. **Mocking & Testing**
```python
# Mock tool outputs for testing
debugger.mock_registry.mock_tool("web_search", "Mocked search results")
debugger.mock_registry.mock_llm("summarize", "Mocked summary response")

# Test assertions
from agentdebugger.testing import AgentTester

tester = AgentTester(debugger)
tester.expect_tool_call("web_search").with_input_containing("AI startups")
tester.expect_memory_write("search_results")
tester.run_and_verify(agent, "Find AI startups")
```

### 5. **Replay & Analysis**
```python
# Export execution trace
debugger.export_trace("my_agent_session.json")

# Replay previous session
debugger.replay_from_file("my_agent_session.json")

# Compare multiple runs
from agentdebugger.analysis import TraceComparator
comparator = TraceComparator()
diff = comparator.compare_traces("run1.json", "run2.json")
```

## 🔧 Framework Integrations

### LangChain Integration
```python
from langchain.agents import AgentExecutor
from agentdebugger.integrations import LangChainDebugger

agent_executor = AgentExecutor(...)
debugger = LangChainDebugger()
debugged_executor = debugger.attach(agent_executor)
```

### CrewAI Integration
```python
from crewai import Agent, Task, Crew
from agentdebugger.integrations import CrewAIDebugger

crew = Crew(agents=[...], tasks=[...])
debugger = CrewAIDebugger()
debugged_crew = debugger.attach(crew)
```

### AutoGPT Integration
```python
from autogpt import AutoGPT
from agentdebugger.integrations import AutoGPTDebugger

autogpt = AutoGPT(...)
debugger = AutoGPTDebugger()
debugged_autogpt = debugger.attach(autogpt)
```

## 📊 Advanced Features

### Web Dashboard (Optional)
```python
debugger = AgentDebugger(mode="web", port=8080)
# Opens web interface at http://localhost:8080
```

Features include:
- Real-time execution timeline
- Interactive memory state visualization
- Tool execution graph
- Performance metrics dashboard

### Custom Event Types
```python
from agentdebugger import TraceEvent, EventType

# Define custom events
class CustomEventType(Enum):
    CUSTOM_REASONING = "custom_reasoning"
    VALIDATION_CHECK = "validation_check"

# Emit custom events
debugger.trace_events.append(TraceEvent(
    event_type=CustomEventType.CUSTOM_REASONING,
    agent_id="my_agent",
    data={"reasoning": "Custom logic here"}
))
```

### Performance Analysis
```python
from agentdebugger.analysis import PerformanceAnalyzer

analyzer = PerformanceAnalyzer(debugger.trace_events)

# Analyze execution patterns
report = analyzer.generate_report()
print(f"Total execution time: {report['total_time']}s")
print(f"Tool call overhead: {report['tool_overhead']}%")
print(f"Memory operations: {report['memory_ops']}")

# Detect infinite loops
loops = analyzer.detect_loops()
if loops:
    print(f"⚠️ Potential infinite loop detected: {loops}")
```

## 🧪 Testing Framework

### Unit Tests for Agents
```python
import unittest
from agentdebugger.testing import AgentTestCase

class TestMyAgent(AgentTestCase):
    def setUp(self):
        self.agent = MyAgent()
        self.debugger = self.create_debugger()
    
    def test_web_search_flow(self):
        # Set up expectations
        self.expect_tool_call("web_search")
        self.expect_memory_write("search_results")
        
        # Run agent
        result = self.run_agent("Search for AI news")
        
        # Verify expectations
        self.verify_expectations()
        self.assertIn("AI", result)
    
    def test_error_handling(self):
        # Mock tool to raise error
        self.mock_tool_error("web_search", "Connection failed")
        
        # Verify agent handles error gracefully
        with self.assertRaises(AgentExecutionError):
            self.run_agent("Search for news")
```

### Integration Tests
```python
from agentdebugger.testing import IntegrationTest

class TestAgentWorkflow(IntegrationTest):
    def test_multi_agent_collaboration(self):
        researcher = ResearchAgent()
        writer = WriterAgent()
        
        # Debug both agents
        debugger = self.create_debugger()
        debugger.attach(researcher, "researcher")
        debugger.attach(writer, "writer")
        
        # Set breakpoint for inter-agent communication
        debugger.add_breakpoint(Breakpoint(
            breakpoint_type=BreakpointType.CONDITIONAL,
            condition=lambda e: e.agent_id == "writer" and 
                               "researcher_output" in str(e.data)
        ))
        
        # Run workflow
        result = self.run_workflow(researcher, writer, "Write about AI")
        self.verify_collaboration_patterns()
```

## 🎨 Visualization Options

### Console Output Formatting
```python
debugger = AgentDebugger(
    mode="console",
    console_theme="dark",  # dark, light, colorful
    show_timestamps=True,
    max_trace_display=20
)
```

### Export Formats
```python
# JSON (default)
debugger.export_trace("trace.json")

# CSV for analysis
debugger.export_trace("trace.csv", format="csv")

# HTML report
debugger.export_trace("report.html", format="html")

# Mermaid diagram
debugger.export_trace("flow.mmd", format="mermaid")
```

## ⚡ Performance Considerations

### Minimal Overhead Mode
```python
debugger = AgentDebugger(
    mode="minimal",  # Reduces instrumentation overhead
    buffer_size=1000,  # Limit trace buffer size
    sample_rate=0.1  # Only trace 10% of events
)
```

### Memory Management
```python
# Clear old traces
debugger.clear_traces(keep_last=100)

# Set automatic cleanup
debugger.auto_cleanup(max_events=10000, max_age_hours=24)
```

## 🚨 Error Handling & Recovery

### Automatic Error Detection
```python
from agentdebugger.analysis import ErrorDetector

detector = ErrorDetector(debugger)

# Detect common issues
issues = detector.scan_for_issues()
for issue in issues:
    print(f"⚠️ {issue.severity}: {issue.description}")
    print(f"   Suggestion: {issue.suggestion}")
```

### Recovery Strategies
```python
# Auto-retry on tool failures
debugger.add_recovery_strategy("tool_failure", 
    lambda: debugger.mock_registry.mock_tool("failed_tool", "fallback_output")
)

# Timeout handling
debugger.set_timeout(30)  # 30 second timeout per operation
```

## 🔒 Security & Privacy

### Sensitive Data Filtering
```python
debugger = AgentDebugger(
    filter_sensitive=True,  # Filter out API keys, tokens, etc.
    redact_patterns=[r'\b\w+@\w+\.\w+\b'],  # Email addresses
    max_data_length=200  # Truncate long data fields
)
```

### Audit Logging
```python
debugger.enable_audit_log("agent_audit.log")
# Logs all breakpoint hits, edits, and overrides
```

## 📚 API Reference

### Core Classes

#### `AgentDebugger`
Main debugger interface for attaching to agents and controlling execution.

**Constructor:**
```python
AgentDebugger(
    mode: str = "console",  # console, web, minimal, headless
    enable_replay: bool = True,
    max_trace_events: int = 10000,
    auto_export: bool = False,
    export_path: str = "./traces/"
)
```

**Methods:**
- `attach(agent, agent_id=None)` - Attach debugger to an agent
- `add_breakpoint(breakpoint)` - Add execution breakpoint
- `get_trace_summary()` - Get execution statistics
- `export_trace(filename, format="json")` - Export trace data

#### `Breakpoint`
Defines conditions for pausing agent execution.

```python
Breakpoint(
    breakpoint_type: BreakpointType,
    condition: Callable[[TraceEvent], bool] = None,
    tool_name: str = None,
    enabled: bool = True
)
```

#### `TraceEvent`
Represents a single event in agent execution.

```python
TraceEvent(
    event_type: EventType,
    agent_id: str,
    data: Dict[str, Any],
    timestamp: datetime = now(),
    parent_event_id: str = None
)
```

### Utility Functions
```python
# Quick debugging
debug_agent(agent, mode="console")

# Decorator for automatic breakpoints  
@breakpoint_on_tool("web_search")
def my_agent_method(self):
    pass

# Context manager for temporary debugging
with temporary_debug(agent) as debugger:
    agent.run("task")
```



### Adding New Integrations
```python
from agentdebugger.integrations.base import BaseIntegration

class MyFrameworkIntegration(BaseIntegration):
    def instrument_agent(self, agent):
        # Implement framework-specific instrumentation
        pass
    
    def extract_events(self, execution_data):
        # Convert framework events to TraceEvents
        pass
```

## 📋 Roadmap

- [ ] **v1.1**: Web dashboard with real-time visualization
- [ ] **v1.2**: Integration with popular agent frameworks
- [ ] **v1.3**: Advanced analytics and pattern detection
- [ ] **v1.4**: Distributed agent debugging across multiple processes
- [ ] **v1.5**: AI-powered debugging suggestions
- [ ] **v2.0**: Visual agent flow builder with integrated debugging

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.



*"Finally, a microscope for AI agent behavior!"* 🔬✨