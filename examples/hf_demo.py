import sys
import pathlib

# Ensure project root is importable when running directly
ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse

try:
    from transformers import pipeline, set_seed
except Exception as e:
    print("Missing dependency: transformers. Install with: pip install transformers")
    raise

from agent_debugger import Breakpoint, BreakpointType
from agent_debugger.integrations import HuggingFaceDebugger


def build_pipeline(task: str, model: str, device: str | None = None):
    kwargs = {}
    if device:
        # transformers uses device index integers; keep string for user, rely on auto if not provided
        try:
            kwargs["device"] = int(device)
        except Exception:
            pass
    return pipeline(task, model=model, **kwargs)


def run_demo(
    prompt: str,
    task: str = "text-generation",
    model: str = "gpt2",
    console: bool = False,
    max_new_tokens: int = 24,
    device: str | None = None,
    seed: int | None = 42,
):
    if seed is not None:
        try:
            set_seed(seed)
        except Exception:
            pass

    dbg = HuggingFaceDebugger(mode="console" if console else "headless")

    # Break before/after LLM calls for interactive stepping
    dbg.add_breakpoint(Breakpoint(breakpoint_type=BreakpointType.BEFORE_LLM))
    dbg.add_breakpoint(Breakpoint(breakpoint_type=BreakpointType.AFTER_LLM))

    pipe = build_pipeline(task=task, model=model, device=device)
    pipe_dbg = dbg.attach(pipe, agent_id=f"hf_{task}")

    if task == "text-generation":
        outputs = pipe_dbg(prompt, max_new_tokens=max_new_tokens, do_sample=False)
        return outputs
    elif task in ("text2text-generation", "summarization"):
        outputs = pipe_dbg(prompt, max_new_tokens=max_new_tokens)
        return outputs
    elif task == "sentiment-analysis":
        outputs = pipe_dbg(prompt)
        return outputs
    else:
        outputs = pipe_dbg(prompt)
        return outputs


def main():
    parser = argparse.ArgumentParser(
        description="Hugging Face integration demo with interactive console"
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="Hello from AgentDebugger!",
        help="Input prompt/text",
    )
    parser.add_argument(
        "--task",
        default="text-generation",
        help="Pipeline task, e.g., text-generation, summarization, sentiment-analysis",
    )
    parser.add_argument("--model", default="gpt2", help="Model name or path")
    parser.add_argument(
        "--console", action="store_true", help="Enable interactive console breakpoints"
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=24,
        help="Max new tokens for generation tasks",
    )
    parser.add_argument(
        "--device", default=None, help="Device index (e.g., 0 for CUDA:0), optional"
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility"
    )

    args = parser.parse_args()

    outputs = run_demo(
        prompt=args.prompt,
        task=args.task,
        model=args.model,
        console=args.console,
        max_new_tokens=args.max_new_tokens,
        device=args.device,
        seed=args.seed,
    )

    print("\nOutputs:\n", outputs)


if __name__ == "__main__":
    main()
