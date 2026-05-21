from langgraph.graph import END, StateGraph

from aiops_agents.nodes.evaluator import evaluator_node
from aiops_agents.nodes.generator import generator_node
from aiops_agents.nodes.monitor import monitor_node
from aiops_agents.nodes.planner import planner_node
from aiops_agents.state import AgentState, TriggerSource


def should_retry(state: AgentState) -> str:
    if state.evaluation_results and state.evaluation_results.is_passed:
        return "approve"
    if state.retry_count >= 3:
        return "fail"
    return "retry"


def route_entry(state: AgentState) -> str:
    if state.trigger_source == TriggerSource.PLANNER_REQUEST:
        return "planner"
    return "monitor"


def build_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("monitor", monitor_node)
    builder.add_node("planner", planner_node)
    builder.add_node("generator", generator_node)
    builder.add_node("evaluator", evaluator_node)

    builder.set_conditional_entry_point(route_entry, {"monitor": "monitor", "planner": "planner"})

    builder.add_edge("monitor", "generator")
    builder.add_edge("planner", "generator")
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
