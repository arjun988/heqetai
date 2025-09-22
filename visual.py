"""
AgentDebugger Visualization
===========================

This module provides utilities to visualize agent traces using Pydantic
schemas for validation and matplotlib/networkx for rendering.

Features:
- Timeline view of events by timestamp
- Group nodes by agent_id (color-coded)
- Hover tooltips with full prompt/response text
"""

import json
from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplcursors


# ------------------------------
# Pydantic Models
# ------------------------------

class TraceEventModel(BaseModel):
    id: str
    timestamp: datetime
    event_type: str
    agent_id: str
    step_id: str
    data: Dict
    parent_event_id: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)


class TraceSummaryModel(BaseModel):
    total_events: int
    events_by_type: Dict[str, int]
    execution_time: float
    agents: List[str]


class TraceFileModel(BaseModel):
    summary: TraceSummaryModel
    events: List[TraceEventModel]


# ------------------------------
# Visualization Logic
# ------------------------------

def visualize_trace_timeline(filename: str, output: Optional[str] = None):
    """
    Load a JSON trace file and generate a timeline visualization.

    Args:
        filename (str): Path to trace JSON file
        output (str, optional): Path to save PNG image. If None, show interactive plot.
    """
    with open(filename, "r") as f:
        data = json.load(f)

    # Validate schema
    trace = TraceFileModel(**data)

    # Prepare figure
    plt.figure(figsize=(14, 6))

    # Assign a color per agent_id
    agent_ids = list(set([e.agent_id for e in trace.events]))
    colors = plt.cm.get_cmap("tab10", len(agent_ids))
    agent_color_map = {agent: colors(i) for i, agent in enumerate(agent_ids)}

    # Collect event points
    times = [e.timestamp for e in trace.events]
    y_positions = [agent_ids.index(e.agent_id) for e in trace.events]
    labels = []
    scatter_colors = []

    for event in trace.events:
        scatter_colors.append(agent_color_map[event.agent_id])
        tooltip_text = (
            f"Agent: {event.agent_id}\n"
            f"Event: {event.event_type}\n"
            f"Step: {event.step_id}\n"
            f"Time: {event.timestamp}\n"
        )

        # Show prompt/response if available
        if "prompt" in event.data:
            tooltip_text += f"Prompt: {event.data['prompt']}\n"
        if "response" in event.data:
            tooltip_text += f"Response: {event.data['response']}\n"
        if "result" in event.data:
            tooltip_text += f"Result: {event.data['result']}\n"

        labels.append(tooltip_text)

    # Scatter plot timeline
    scatter = plt.scatter(
        times, y_positions,
        c=scatter_colors,
        s=120,
        alpha=0.8,
        edgecolors="k"
    )

    # Customize axes
    plt.yticks(range(len(agent_ids)), agent_ids)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    plt.xlabel("Timestamp")
    plt.ylabel("Agents")
    plt.title(f"Agent Trace Timeline ({', '.join(trace.summary.agents)})")

    # Hover tooltips
    cursor = mplcursors.cursor(scatter, hover=True)
    @cursor.connect("add")
    def on_hover(sel):
        sel.annotation.set_text(labels[sel.index])
        sel.annotation.get_bbox_patch().set(fc="white", alpha=0.9)

    plt.tight_layout()

    if output:
        plt.savefig(output, bbox_inches="tight")
        print(f"✅ Timeline visualization saved to {output}")
    else:
        plt.show()


# ------------------------------
# Demo Run
# ------------------------------

if __name__ == "__main__":
    # Example usage with your demo files
    visualize_trace_timeline("demo_tools_trace.json", output="tools_timeline.png")
    visualize_trace_timeline("demo_review_trace.json", output="review_timeline.png")
