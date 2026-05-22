from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from aiops_agents.config import get_llm
from aiops_agents.state import AgentState, EvaluationResult, PipelineStatus
from aiops_agents.tools import EVALUATOR_TOOLS

SYSTEM_PROMPT = Path(__file__).parent.parent.joinpath("prompts", "evaluator.md").read_text()


def evaluator_node(state: AgentState) -> dict:
    """Deploy, test, and validate changes with comprehensive diagnostics on failure."""
    llm = get_llm().bind_tools(EVALUATOR_TOOLS)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=_build_eval_prompt(state)),
    ]

    tool_map = {t.name: t for t in EVALUATOR_TOOLS}

    for _ in range(20):
        response = llm.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for tc in response.tool_calls:
            tool_fn = tool_map[tc["name"]]
            result = tool_fn.invoke(tc["args"])
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

    if state.proposed_changes:
        parts.append("\nProposed changes:")
        for change in state.proposed_changes:
            parts.append(f"  - {change.repository}: {change.file_path}")
            if change.pull_request_url:
                parts.append(f"    PR: {change.pull_request_url}")

    parts.append(
        "\nYou have full access to: kubectl (apply, logs, describe, events, exec, top, scale, restart), "
        "health checks, load testing, ArgoCD sync, and PR merge.\n\n"
        "Deploy to sandbox, run comprehensive tests. On FAILURE:\n"
        "- Capture pod stderr (kubectl logs --previous)\n"
        "- Capture pod events (kubectl describe)\n"
        "- Run kubectl exec for in-container diagnostics if needed\n"
        "- Check node-level resources (kubectl top)\n"
        "- Report ALL error details without truncation"
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
        failure_phase="HEALTH_CHECK",
        suggested_fix_hint=None,
    )
