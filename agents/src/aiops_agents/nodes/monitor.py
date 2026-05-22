from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from aiops_agents.config import get_llm
from aiops_agents.state import AgentState, PipelineStatus, RCAReport
from aiops_agents.tools import MONITORING_TOOLS

SYSTEM_PROMPT = Path(__file__).parent.parent.joinpath("prompts", "monitor.md").read_text()


def monitor_node(state: AgentState) -> dict:
    """Analyze alerts through the observability stack only (PromQL/LogQL)."""
    llm = get_llm("monitor").bind_tools(MONITORING_TOOLS)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=_build_analysis_prompt(state)),
    ]

    tool_map = {t.name: t for t in MONITORING_TOOLS}

    for _ in range(15):
        response = llm.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for tc in response.tool_calls:
            tool_fn = tool_map[tc["name"]]
            result = tool_fn.invoke(tc["args"])
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    rca = _parse_rca(response.content, state)

    return {
        "status": PipelineStatus.ANALYZING,
        "rca_report": rca,
        "messages": state.messages + [{"role": "monitor", "content": response.content}],
    }


def _build_analysis_prompt(state: AgentState) -> str:
    alert_info = "\n".join(
        msg.get("content", "") for msg in state.messages if msg.get("role") == "alert"
    )
    return (
        f"An alert has been received for services: {state.target_services}\n\n"
        f"Alert details:\n{alert_info}\n\n"
        "Investigate using the monitoring stack:\n"
        "- PromQL: resource metrics (CPU, memory, restarts, network)\n"
        "- PromQL range: time-series trends to identify when the problem started\n"
        "- LogQL: application error logs, stack traces, panic messages\n\n"
        "Produce an RCA report with: root_cause_service, failure_mode, evidence_logs, recommended_action."
    )


def _parse_rca(content: str, state: AgentState) -> RCAReport:
    return RCAReport(
        root_cause_service=state.target_services[0] if state.target_services else "unknown",
        failure_mode="Determined by LLM analysis",
        evidence_logs=[content[:2000]],
        recommended_action="See LLM analysis above",
    )
