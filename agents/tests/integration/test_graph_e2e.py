"""Integration test: verify LangGraph compiles and state transitions are correct."""
from unittest.mock import patch

from aiops_agents.graph import build_graph, should_retry
from aiops_agents.state import AgentState, EvaluationResult, PipelineStatus, TriggerSource


def test_should_retry_approve():
    state = AgentState(
        trigger_source=TriggerSource.ALERTMANAGER,
        target_services=["data-worker"],
        evaluation_results=EvaluationResult(is_passed=True, error_logs=[]),
    )
    assert should_retry(state) == "approve"


def test_should_retry_fail_max_retries():
    state = AgentState(
        trigger_source=TriggerSource.ALERTMANAGER,
        target_services=["data-worker"],
        retry_count=3,
        evaluation_results=EvaluationResult(is_passed=False, error_logs=["error"]),
    )
    assert should_retry(state) == "fail"


def test_should_retry_retry():
    state = AgentState(
        trigger_source=TriggerSource.ALERTMANAGER,
        target_services=["data-worker"],
        retry_count=1,
        evaluation_results=EvaluationResult(is_passed=False, error_logs=["error"]),
    )
    assert should_retry(state) == "retry"


def test_graph_compiles():
    """Verify the graph compiles without errors."""
    g = build_graph()
    assert g is not None
