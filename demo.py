import os
import sys
import pathlib

# Ensure project root is importable when running directly
ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_google_genai import ChatGoogleGenerativeAI
except Exception as e:
    print("Missing dependencies. Install: pip install langchain-core langchain-google-genai")
    raise

from main import AgentDebugger, Breakpoint, BreakpointType
from integration import LangChainDebugger, MultiAgentOrchestrator


MEDICAL_CONTEXT = (
    "Hypertension (high blood pressure) increases risk of stroke and heart disease. "
    "Lifestyle interventions include reduced sodium intake, regular aerobic exercise, and limiting alcohol. "
    "First-line pharmacologic treatments often include thiazide diuretics, ACE inhibitors, ARBs, or calcium channel blockers. "
    "Diabetes management emphasizes A1c control through diet, exercise, and medications like metformin as first-line, unless contraindicated. "
    "Statins reduce cardiovascular risk in eligible patients based on ASCVD risk. "
    "If information is not present in this context, the correct response is: I don't know based on the provided medical context."
)


def build_medical_agent():
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a medical assistant. Only answer using the provided medical context. "
            "If the answer is not explicitly in the context, say: I don't know based on the provided medical context.\n\n"
            "Context:\n{medical_context}",
        ),
        ("human", "Question: {question}"),
    ])
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    return prompt | llm | StrOutputParser()


def build_reviewer_agent():
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a clinical reviewer. Given the clinician-facing answer, provide:\n"
            "1) A patient-friendly summary (<= 2 sentences).\n"
            "2) A confidence tag: High/Medium/Low." ,
        ),
        ("human", "Clinician answer: {answer}"),
    ])
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    return prompt | llm | StrOutputParser()


class MedicalWorkflowAgent:
    """Agent exposing tool, memory, and LLM methods to exercise debugger features."""
    def __init__(self):
        self.tools = ["web_search", "summarizer"]
        self.memory = {}
        self._llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)

    def execute_tool(self, tool_name: str, query: str) -> str:
        if tool_name == "web_search":
            # Simple search over MEDICAL_CONTEXT; also allow forcing an error path
            if "force_error" in query.lower():
                raise RuntimeError("Simulated web_search failure for testing")
            hits = []
            for sentence in MEDICAL_CONTEXT.split(". "):
                if any(word.lower() in sentence.lower() for word in query.split() if len(word) > 3):
                    hits.append(sentence.strip())
            return " | ".join(hits[:3]) or "No direct hits in medical context"
        elif tool_name == "summarizer":
            return f"Summary: {query[:120]}" if query else "Summary: (empty)"
        return f"Tool {tool_name} executed with: {query}"

    def call_llm(self, prompt: str) -> str:
        # Use Gemini to generate a short response
        template = ChatPromptTemplate.from_messages([
            ("system", "You are assisting a clinician. Be concise."),
            ("human", "{p}")
        ])
        chain = template | self._llm | StrOutputParser()
        return chain.invoke({"p": prompt})

    def update_memory(self, key: str, value):
        self.memory[key] = value

    def run(self, question: str) -> str:
        reasoning = self.call_llm(f"Given the medical context, plan to answer: {question}")
        search_results = self.execute_tool("web_search", question)
        self.update_memory("search_results", search_results)
        combined = f"Plan: {reasoning}\nFindings: {search_results}"
        summary = self.execute_tool("summarizer", combined)
        self.update_memory("summary", summary)
        final = self.call_llm(
            f"Using context-only facts, produce clinician answer to: {question}.\nFacts: {search_results}\n{summary}"
        )
        return final


def run_pipeline(question: str, console_mode: bool = False, force_error: bool = False, enable_multi: bool = True, enable_mock: bool = False):
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("Set GOOGLE_API_KEY environment variable before running.")

    mode = "console" if console_mode else "headless"

    # Debugger for tool/memory/LLM instrumentation (custom workflow agent)
    tool_debugger = AgentDebugger(mode=mode)
    # Global listener example: count events
    event_counts = {"count": 0}
    def _count_listener(ev):
        event_counts["count"] += 1
    tool_debugger.add_global_listener(_count_listener)
    workflow_agent = MedicalWorkflowAgent()
    debugged_workflow = tool_debugger.attach(workflow_agent, agent_id="medical_workflow")

    # Add interactive breakpoints to exercise console commands
    tool_debugger.add_breakpoint(Breakpoint(
        breakpoint_type=BreakpointType.BEFORE_TOOL
    ))
    tool_debugger.add_breakpoint(Breakpoint(
        breakpoint_type=BreakpointType.BEFORE_TOOL,
        tool_name="web_search"
    ))
    tool_debugger.add_breakpoint(Breakpoint(
        breakpoint_type=BreakpointType.CONDITIONAL,
        condition=lambda event: "error" in str(event.data).lower()
    ))
    tool_debugger.add_breakpoint(Breakpoint(breakpoint_type=BreakpointType.BEFORE_MEMORY_WRITE))
    tool_debugger.add_breakpoint(Breakpoint(breakpoint_type=BreakpointType.AFTER_TOOL))
    tool_debugger.add_breakpoint(Breakpoint(breakpoint_type=BreakpointType.BEFORE_LLM))
    tool_debugger.add_breakpoint(Breakpoint(breakpoint_type=BreakpointType.AFTER_LLM))

    # Optional mocking
    if enable_mock:
        tool_debugger.mock_registry.mock_tool("web_search", "Mocked search results from tool")
        tool_debugger.mock_registry.mock_llm("plan to answer", "Mocked LLM plan response")

    # Reviewer uses LangChain LCEL; instrument with LangChainDebugger to capture reasoning events
    review_debugger = LangChainDebugger(mode=mode)
    review_debugger.add_global_listener(_count_listener)
    reviewer_chain = build_reviewer_agent()
    debugged_reviewer = review_debugger.attach(reviewer_chain, agent_id="reviewer_agent")
    review_debugger.add_breakpoint(Breakpoint(breakpoint_type=BreakpointType.AFTER_REASONING))
    review_debugger.add_breakpoint(Breakpoint(breakpoint_type=BreakpointType.BEFORE_REASONING))

    q = question
    if force_error:
        q = f"{question} force_error"  # triggers simulated web_search failure

    medical_answer = debugged_workflow.run(q)
    reviewed_output = debugged_reviewer.invoke({"answer": medical_answer})

    # Optional: Multi-agent orchestration demo using the same LangChain debugger
    orchestration_result = None
    if enable_multi:
        # Two lightweight LCEL agents
        def build_agent(system_msg: str):
            p = ChatPromptTemplate.from_messages([
                ("system", system_msg),
                ("human", "{input}")
            ])
            m = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
            return p | m | StrOutputParser()

        chain_a = build_agent("You are Agent A. Propose ideas briefly.")
        chain_b = build_agent("You are Agent B. Critique concisely.")

        agent_a = review_debugger.attach(chain_a, agent_id="agent_A")
        agent_b = review_debugger.attach(chain_b, agent_id="agent_B")

        orchestrator = MultiAgentOrchestrator(review_debugger)
        orchestrator.register("agent_A", agent_a)
        orchestrator.register("agent_B", agent_b)

        # Break on inter-agent messages
        review_debugger.add_breakpoint(Breakpoint(
            breakpoint_type=BreakpointType.CONDITIONAL,
            condition=lambda e: getattr(e, 'event_type', None) and e.event_type.value == "inter_agent_message"
        ))

        msg1 = orchestrator.send("agent_A", "agent_B", "Propose a project name for a medical note app.")
        msg2 = orchestrator.send("agent_B", "agent_A", f"Briefly critique: {msg1}")
        orchestration_result = {"a_to_b": msg1, "b_to_a": msg2}

    return medical_answer, reviewed_output, tool_debugger, review_debugger, event_counts, orchestration_result


def main():
    question = None
    console = False
    force_error = False
    enable_multi = True
    enable_mock = False
    args = sys.argv[1:]
    if "--console" in args:
        console = True
        args = [a for a in args if a != "--console"]
    if "--force-error" in args:
        force_error = True
        args = [a for a in args if a != "--force-error"]
    if "--no-multi" in args:
        enable_multi = False
        args = [a for a in args if a != "--no-multi"]
    if "--mock" in args:
        enable_mock = True
        args = [a for a in args if a != "--mock"]
    if args:
        question = " ".join(args)
    else:
        try:
            question = input("Enter a medical question: ").strip()
        except EOFError:
            question = "What are first-line treatments for hypertension?"

    medical_answer, reviewed_output, dbg_tools, dbg_review, evt_counts, orch = run_pipeline(
        question, console_mode=console, force_error=force_error, enable_multi=enable_multi, enable_mock=enable_mock
    )

    print("\nMedical Agent Answer:\n" + medical_answer)
    print("\nReviewer Agent Output:\n" + reviewed_output)

    print("\nTool/Memory/LLM Debugger Summary:")
    print(dbg_tools.get_trace_summary())
    print("\nReviewer Reasoning Debugger Summary:")
    print(dbg_review.get_trace_summary())
    print(f"\nGlobal event count observed by listener: {evt_counts['count']}")

    if orch is not None:
        print("\nOrchestration exchange:")
        print(f"A->B: {orch['a_to_b']}")
        print(f"B->A: {orch['b_to_a']}")
    try:
        dbg_tools.export_trace("demo_tools_trace.json")
        dbg_review.export_trace("demo_review_trace.json")
    except Exception:
        pass


if __name__ == "__main__":
    main()


