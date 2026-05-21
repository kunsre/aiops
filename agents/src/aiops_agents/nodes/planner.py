from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from aiops_agents.config import get_llm
from aiops_agents.state import AgentState, PipelineStatus

SYSTEM_PROMPT = Path(__file__).parent.parent.joinpath("prompts", "planner.md").read_text()


def planner_node(state: AgentState) -> dict:
    """Gather requirements, analyze dependencies, define acceptance criteria."""
    llm = get_llm()

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=_build_planning_prompt(state)),
    ]

    response = llm.invoke(messages)

    return {
        "status": PipelineStatus.IMPLEMENTING,
        "messages": state.messages + [{"role": "planner", "content": response.content}],
    }


def _build_planning_prompt(state: AgentState) -> str:
    request_info = "\n".join(
        msg.get("content", "") for msg in state.messages if msg.get("role") == "request"
    )
    return (
        f"Target services: {state.target_services}\n\n"
        f"Request:\n{request_info}\n\n"
        "Please analyze the request, determine cross-service impact, and produce "
        "an implementation spec with acceptance criteria."
    )
