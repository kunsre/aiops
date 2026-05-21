from langgraph.graph import END, StateGraph

from aiops_agents.nodes import evaluator_node, generator_node, monitor_node
from aiops_agents.state import AgentState


def should_retry(state: AgentState) -> str:
    if state.evaluation_results and state.evaluation_results.is_passed:
        return "approve"
    if state.retry_count >= 3:
        return "fail"
    return "retry"


def build_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("monitor", monitor_node)
    builder.add_node("generator", generator_node)
    builder.add_node("evaluator", evaluator_node)

    builder.set_entry_point("monitor")
    builder.add_edge("monitor", "generator")
    builder.add_edge("generator", "evaluator")
    builder.add_conditional_edges(
        "evaluator",
        should_retry,
        {
            "retry": "generator",
            "approve": END,
            "fail": END,
        },
    )

    return builder.compile()


graph = build_graph()
