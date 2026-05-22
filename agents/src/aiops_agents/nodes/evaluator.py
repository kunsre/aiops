from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from aiops_agents.config import get_llm
from aiops_agents.state import AgentState, EvaluationResult, PipelineStatus
from aiops_agents.tools import EVALUATOR_TOOLS

SYSTEM_PROMPT = Path(__file__).parent.parent.joinpath("prompts", "evaluator.md").read_text()


def evaluator_node(state: AgentState) -> dict:
    """Review proposed code changes for correctness."""
    llm = get_llm("evaluator").bind_tools(EVALUATOR_TOOLS)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=_build_eval_prompt(state)),
    ]

    tool_map = {t.name: t for t in EVALUATOR_TOOLS}

    for _ in range(10):
        response = llm.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for tc in response.tool_calls:
            tool_fn = tool_map[tc["name"]]
            try:
                result = tool_fn.invoke(tc["args"])
            except Exception as e:
                result = f"TOOL ERROR: {type(e).__name__}: {e}"
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    eval_result = _parse_evaluation(response.content, state)

    new_status = PipelineStatus.COMPLETED if eval_result.is_passed else PipelineStatus.RETRYING
    new_retry = state.retry_count if eval_result.is_passed else state.retry_count + 1

    return {
        "status": new_status,
        "evaluation_results": eval_result,
        "retry_count": new_retry,
        "messages": state.messages + [{"role": "evaluator", "content": response.content}],
    }


def _build_eval_prompt(state: AgentState) -> str:
    parts = [f"Target services: {state.target_services}"]
    parts.append(f"Current retry count: {state.retry_count}/3")

    if state.rca_report:
        parts.append(f"\nRCA Summary:")
        parts.append(f"  Root cause: {state.rca_report.root_cause_service}")
        parts.append(f"  Failure mode: {state.rca_report.failure_mode}")
        parts.append(f"  Recommended: {state.rca_report.recommended_action}")

    if state.proposed_changes:
        parts.append("\nProposed changes to review:")
        for change in state.proposed_changes:
            parts.append(f"  - File: {change.file_path}")
            parts.append(f"    Diff: {change.diff}")
            if change.pull_request_url:
                parts.append(f"    PR: {change.pull_request_url}")

    parts.append(
        "\nReview the proposed change by reading the current file from the repo. "
        "Determine if this fix correctly addresses the root cause. "
        "Report PASS if it looks correct, FAIL if it won't work."
    )
    return "\n".join(parts)


def _parse_evaluation(content: str, state: AgentState) -> EvaluationResult:
    content_lower = content.lower()
    is_passed = "pass" in content_lower and "fail" not in content_lower

    if is_passed:
        return EvaluationResult(is_passed=True, error_logs=[])

    return EvaluationResult(
        is_passed=False,
        error_logs=[content[:4000]],
        failed_resource=state.target_services[0] if state.target_services else None,
        failure_phase="CODE_REVIEW",
        suggested_fix_hint=None,
    )
