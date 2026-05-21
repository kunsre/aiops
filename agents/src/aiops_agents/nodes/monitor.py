from aiops_agents.state import AgentState, PipelineStatus


def monitor_node(state: AgentState) -> dict:
    """Analyze alerts, query metrics/logs, produce RCA report."""
    return {"status": PipelineStatus.ANALYZING}
