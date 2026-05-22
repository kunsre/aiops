from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from aiops_agents.config import get_llm
from aiops_agents.state import AgentState, EvaluationResult, PipelineStatus
from aiops_agents.tools import EVALUATOR_TOOLS

SYSTEM_PROMPT = Path(__file__).parent.parent.joinpath("prompts", "evaluator.md").read_text()


def evaluator_node(state: AgentState) -> dict:
    """Validate changes via GitOps deployment + read-only diagnostics."""
    llm = get_llm("evaluator").bind_tools(EVALUATOR_TOOLS)

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

    if state.proposed_changes:
        parts.append("\nProposed changes:")
        for change in state.proposed_changes:
            parts.append(f"  - {change.repository}: {change.file_path}")
            if change.pull_request_url:
                parts.append(f"    PR: {change.pull_request_url}")

    parts.append(
        "\nYour workflow:\n"
        "1. Merge the PR (approve_and_merge_pr)\n"
        "2. Trigger ArgoCD sync (sync_argocd_app)\n"
        "3. Poll ArgoCD status until Synced+Healthy or Failed (get_argocd_app_status)\n"
        "4. Run health check against the service endpoint\n"
        "5. Run load test to verify stability\n\n"
        "On FAILURE - collect diagnostics (read-only):\n"
        "- kubectl logs (pod stderr, previous container)\n"
        "- kubectl describe (pod events, scheduling issues)\n"
        "- kubectl get events (namespace-level events)\n"
        "- kubectl top (resource pressure)\n\n"
        "Report ALL error details. You cannot apply manifests or exec into pods.\n"
        "All deployments happen through ArgoCD only."
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
