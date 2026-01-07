"""
Agent state tracking structures.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class AgentState:
    """Tracks the current state of an agent during execution"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.memory: Dict[str, Any] = {}
        self.execution_stack: List[str] = []
        self.current_step: Optional[str] = None
        self.tool_outputs: Dict[str, Any] = {}
        self.reasoning_log: List[str] = []
        self.is_paused: bool = False
        self.last_llm_call: Optional[Dict[str, Any]] = None
        self.created_at: datetime = datetime.now()
        self.tasks_completed: int = 0
        self.errors_encountered: int = 0
        self.performance_stats: Dict[str, float] = {
            "total_tool_time": 0.0,
            "total_llm_time": 0.0,
            "avg_response_time": 0.0,
        }
