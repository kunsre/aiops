from aiops_agents.state import AgentState, PipelineStatus


def planner_node(state: AgentState) -> dict:
    """Gather requirements, analyze dependencies, define acceptance criteria."""
    return {"status": PipelineStatus.IMPLEMENTING}
