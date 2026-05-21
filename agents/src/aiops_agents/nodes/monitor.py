from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from aiops_agents.config import get_llm
from aiops_agents.state import AgentState, PipelineStatus, RCAReport
from aiops_agents.tools.logql import query_logql
from aiops_agents.tools.promql import query_promql, query_promql_range

SYSTEM_PROMPT = Path(__file__).parent.parent.joinpath("prompts", "monitor.md").read_text()

MONITOR_TOOLS = [query_promql, query_promql_range, query_logql]


def monitor_node(state: AgentState) -> dict:
    """Analyze alerts, query metrics/logs, produce RCA report."""
    llm = get_llm().bind_tools(MONITOR_TOOLS)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=_build_analysis_prompt(state)),
    ]

    # Agent loop: let LLM call tools until it produces a final answer
    for _ in range(10):
        response = llm.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for tc in response.tool_calls:
            tool_fn = _get_tool(tc["name"])
            result = tool_fn.invoke(tc["args"])
            from langchain_core.messages import ToolMessage
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    # Parse RCA from final response
    rca = _parse_rca(response.content, state)

    return {
        "status": PipelineStatus.ANALYZING,
        "rca_report": rca,
        "messages": [{"role": "monitor", "content": response.content}],
    }


def _build_analysis_prompt(state: AgentState) -> str:
    alert_info = "\n".join(
        msg.get("content", "") for msg in state.messages if msg.get("role") == "alert"
    )
    return (
        f"An alert has been received for services: {state.target_services}\n\n"
        f"Alert details:\n{alert_info}\n\n"
        "Please investigate using PromQL and LogQL queries, then produce an RCA report."
    )


def _get_tool(name: str):
    tool_map = {t.name: t for t in MONITOR_TOOLS}
    return tool_map[name]


def _parse_rca(content: str, state: AgentState) -> RCAReport:
    # Simple extraction - in production, use structured output
    return RCAReport(
        root_cause_service=state.target_services[0] if state.target_services else "unknown",
        failure_mode="Determined by LLM analysis",
        evidence_logs=[content[:500]],
        recommended_action="See LLM analysis above",
    )
