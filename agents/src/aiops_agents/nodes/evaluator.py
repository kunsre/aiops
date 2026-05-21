from aiops_agents.state import AgentState, PipelineStatus


def evaluator_node(state: AgentState) -> dict:
    """Run sandbox tests, evaluate results, approve or request retry."""
    return {"status": PipelineStatus.TESTING}
