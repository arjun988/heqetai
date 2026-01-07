"""
Hugging Face Transformers integration for AgentDebugger.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..debugger import AgentDebugger
from ..events import EventType, TraceEvent
from ..state import AgentState
from .base import BaseIntegration


class HuggingFaceIntegration(BaseIntegration):
    """Integration for Hugging Face transformers Pipelines and Models"""

    def instrument_agent(self, agent: Any, agent_id: str) -> Any:
        self.instrumented_agents[agent_id] = agent

        # Pipelines expose __call__; special method lookup bypasses instance attributes,
        # so wrap with a proxy that defines __call__ on its own class.
        proxy = None
        if hasattr(agent, "__call__"):
            underlying = agent

            class _PipelineProxy:
                def __init__(self, underlying_ref):
                    self._underlying = underlying_ref

                def __call__(self, *args, **kwargs):
                    event = TraceEvent(
                        event_type=EventType.LLM_CALL_START,
                        agent_id=agent_id,
                        step_id=f"hf_call_{int(datetime.now().timestamp())}",
                        data={
                            "args_preview": str(args)[:200],
                            "kwargs_keys": list(kwargs.keys()),
                            "component": type(self._underlying).__name__,
                            "framework": "Transformers",
                        },
                    )
                    self_ref = self  # capture for readability
                    self_ref_debugger = self_ref_debugger_outer
                    self_ref_debugger._emit_event(event)
                    if self_ref_debugger._should_break(event):
                        self_ref_debugger._trigger_breakpoint(event, agent_id)

                    try:
                        start_time = datetime.now()
                        result = self._underlying.__call__(*args, **kwargs)
                        duration = (datetime.now() - start_time).total_seconds()
                        end_event = TraceEvent(
                            event_type=EventType.LLM_CALL_END,
                            agent_id=agent_id,
                            step_id=event.step_id,
                            data={
                                "result_preview": str(result)[:300],
                                "duration": duration,
                            },
                            parent_event_id=event.id,
                            duration=duration,
                        )
                        self_ref_debugger._emit_event(end_event)
                        if self_ref_debugger._should_break(end_event):
                            self_ref_debugger._trigger_breakpoint(end_event, agent_id)
                        return result
                    except Exception as e:
                        error_event = TraceEvent(
                            event_type=EventType.ERROR,
                            agent_id=agent_id,
                            step_id=event.step_id,
                            data={"error": str(e), "error_type": type(e).__name__},
                            parent_event_id=event.id,
                        )
                        self_ref_debugger._emit_event(error_event)
                        if self_ref_debugger._should_break(error_event):
                            self_ref_debugger._trigger_breakpoint(error_event, agent_id)
                        raise

                def __getattr__(self, name):
                    return getattr(self._underlying, name)

            # Provide debugger to proxy without closing over self in class body
            self_ref_debugger_outer = self.debugger
            proxy = _PipelineProxy(underlying)
            self.instrumented_agents[agent_id] = proxy
            agent = proxy

        if hasattr(agent, "generate"):
            original_generate = agent.generate

            def debugged_generate(*args, **kwargs):
                event = TraceEvent(
                    event_type=EventType.LLM_CALL_START,
                    agent_id=agent_id,
                    step_id=f"hf_generate_{int(datetime.now().timestamp())}",
                    data={
                        "kwargs_keys": list(kwargs.keys()),
                        "framework": "Transformers",
                    },
                )
                self.debugger._emit_event(event)
                if self.debugger._should_break(event):
                    self.debugger._trigger_breakpoint(event, agent_id)
                start_time = datetime.now()
                outputs = original_generate(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                end_event = TraceEvent(
                    event_type=EventType.LLM_CALL_END,
                    agent_id=agent_id,
                    step_id=event.step_id,
                    data={"duration": duration},
                    parent_event_id=event.id,
                    duration=duration,
                )
                self.debugger._emit_event(end_event)
                if self.debugger._should_break(end_event):
                    self.debugger._trigger_breakpoint(end_event, agent_id)
                return outputs

            agent.generate = debugged_generate
            self.original_methods["generate"] = original_generate

        # Emit framework detection event
        self._emit_framework_event(
            "huggingface_instrumented",
            agent_id,
            {
                "component_type": type(agent).__name__,
                "methods_instrumented": list(self.original_methods.keys()),
            },
        )

        return agent if proxy is None else proxy

    def extract_events(self, execution_data: Any) -> List[TraceEvent]:
        return []


class HuggingFaceDebugger(AgentDebugger):
    """Debugger wrapper for Hugging Face transformers components"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.integration = HuggingFaceIntegration(self)
        self.framework = "Transformers"

    def attach(self, component, agent_id: Optional[str] = None):
        if agent_id is None:
            agent_id = f"hf_{len(self._attached_agents)}"
        self._attached_agents[agent_id] = component
        self.agent_states[agent_id] = AgentState(agent_id)
        debugged_component = self.integration.instrument_agent(component, agent_id)
        print(f"🤗 Hugging Face debugger attached to '{agent_id}'")
        print(
            f"   Methods instrumented: {list(self.integration.original_methods.keys())}"
        )
        return debugged_component

    def get_integration_stats(self) -> Dict[str, Any]:
        return self.integration.get_integration_stats()
