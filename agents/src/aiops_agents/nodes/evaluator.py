from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from aiops_agents.config import get_llm
from aiops_agents.state import AgentState, EvaluationResult, PipelineStatus
from aiops_agents.tools.gitops import approve_and_merge_pr, get_argocd_app_status, sync_argocd_app
from aiops_agents.tools.k8s_ops import kubectl_apply, kubectl_describe_pod, kubectl_get_pod_logs
from aiops_agents.tools.test_runner import run_health_check, run_load_test, trigger_test_pipeline

SYSTEM_PROMPT = Path(__file__).parent.parent.joinpath("prompts", "evaluator.md").read_text()

EVALUATOR_TOOLS = [
    kubectl_apply,
    kubectl_get_pod_logs,
    kubectl_describe_pod,
    trigger_test_pipeline,
    run_health_check,
    run_load_test,
    approve_and_merge_pr,
    sync_argocd_app,
    get_argocd_app_status,
]


def evaluator_node(state: AgentState) -> dict:
    """Run sandbox tests, evaluate results, approve or request retry."""
    llm = get_llm().bind_tools(EVALUATOR_TOOLS)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=_build_eval_prompt(state)),
    ]

    # Agent loop
    for _ in range(15):
        response = llm.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for tc in response.tool_calls:
            tool_fn = _get_tool(tc["name"])
            result = tool_fn.invoke(tc["args"])
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    # Parse evaluation result from LLM response
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
        "\nPlease deploy to sandbox, run tests, and report whether the fix works. "
        "If it fails, collect ALL error details (pod logs, describe events, etc)."
    )
    return "\n".join(parts)


def _get_tool(name: str):
    tool_map = {t.name: t for t in EVALUATOR_TOOLS}
    return tool_map[name]


def _parse_evaluation(content: str, state: AgentState) -> EvaluationResult:
    # Simple heuristic - in production, use structured output
    content_lower = content.lower()
    is_passed = "pass" in content_lower and "fail" not in content_lower

    if is_passed:
        return EvaluationResult(is_passed=True, error_logs=[])

    return EvaluationResult(
        is_passed=False,
        error_logs=[content[:2000]],
        failed_resource=state.target_services[0] if state.target_services else None,
        failure_phase="HEALTH_CHECK",
        suggested_fix_hint=None,
    )
