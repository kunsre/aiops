from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from aiops_agents.config import get_llm
from aiops_agents.state import AgentState, PipelineStatus, ProposedChange
from aiops_agents.tools import GENERATOR_TOOLS

SYSTEM_PROMPT = Path(__file__).parent.parent.joinpath("prompts", "generator.md").read_text()


def generator_node(state: AgentState) -> dict:
    """Generate fixes using source code analysis, patching, and PR creation."""
    llm = get_llm().bind_tools(GENERATOR_TOOLS)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=_build_generation_prompt(state)),
    ]

    tool_map = {t.name: t for t in GENERATOR_TOOLS}
    proposed_changes: list[ProposedChange] = list(state.proposed_changes)

    for _ in range(20):
        response = llm.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for tc in response.tool_calls:
            tool_fn = tool_map[tc["name"]]
            result = tool_fn.invoke(tc["args"])
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

            if tc["name"] == "create_pull_request" and "github.com" in str(result):
                proposed_changes.append(
                    ProposedChange(
                        repository=state.target_services[0],
                        file_path=tc["args"].get("title", "unknown"),
                        diff="see PR",
                        pull_request_url=str(result),
                    )
                )

    return {
        "status": PipelineStatus.IMPLEMENTING,
        "proposed_changes": proposed_changes,
        "messages": state.messages + [{"role": "generator", "content": response.content}],
    }


def _build_generation_prompt(state: AgentState) -> str:
    parts = [f"Target services: {state.target_services}"]

    if state.rca_report:
        parts.append(f"\nRCA Report:")
        parts.append(f"  Root cause: {state.rca_report.root_cause_service}")
        parts.append(f"  Failure mode: {state.rca_report.failure_mode}")
        parts.append(f"  Evidence: {state.rca_report.evidence_logs}")
        parts.append(f"  Recommended action: {state.rca_report.recommended_action}")

    if state.evaluation_results and not state.evaluation_results.is_passed:
        parts.append(f"\n⚠️  RETRY #{state.retry_count} - Previous attempt failed:")
        parts.append(f"  Failed resource: {state.evaluation_results.failed_resource}")
        parts.append(f"  Failure phase: {state.evaluation_results.failure_phase}")
        parts.append(f"  Error logs:\n" + "\n".join(f"    {log}" for log in state.evaluation_results.error_logs))
        if state.evaluation_results.suggested_fix_hint:
            parts.append(f"  Suggested fix: {state.evaluation_results.suggested_fix_hint}")

    parts.append(
        "\nYou have access to: source code reader, directory listing, code search, git history, "
        "file patching, kubectl dry-run validation, and PR creation. "
        "Use them to understand the problem, implement a fix, validate it, and open a PR."
    )
    return "\n".join(parts)
