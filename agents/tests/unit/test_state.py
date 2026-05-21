import pytest
from pydantic import ValidationError

from aiops_agents.state import (
    AgentState,
    EvaluationResult,
    PipelineStatus,
    ProposedChange,
    RCAReport,
    TriggerSource,
)


def test_agent_state_defaults():
    state = AgentState(
        trigger_source=TriggerSource.ALERTMANAGER,
        target_services=["data-worker"],
    )
    assert state.status == PipelineStatus.INIT
    assert state.retry_count == 0
    assert state.rca_report is None
    assert state.proposed_changes == []
    assert state.evaluation_results is None


def test_agent_state_full():
    state = AgentState(
        trigger_source=TriggerSource.ALERTMANAGER,
        target_services=["data-worker"],
        status=PipelineStatus.TESTING,
        rca_report=RCAReport(
            root_cause_service="data-worker",
            failure_mode="OOMKilled",
            evidence_logs=["memory usage exceeded 256Mi"],
            recommended_action="increase memory limit to 512Mi",
        ),
        proposed_changes=[
            ProposedChange(
                repository="org/data-worker",
                file_path="k8s/deployment.yaml",
                diff="- memory: 256Mi\n+ memory: 512Mi",
            )
        ],
        evaluation_results=EvaluationResult(
            is_passed=False,
            error_logs=["pod/data-worker-abc123 OOMKilled after 30s"],
            failed_resource="deployment/data-worker",
            failure_phase="HEALTH_CHECK",
            suggested_fix_hint="memory limit still too low, try 1Gi",
        ),
        retry_count=1,
    )
    assert state.status == PipelineStatus.TESTING
    assert state.rca_report.failure_mode == "OOMKilled"
    assert not state.evaluation_results.is_passed
    assert state.evaluation_results.failure_phase == "HEALTH_CHECK"


def test_retry_count_max_3():
    with pytest.raises(ValidationError):
        AgentState(
            trigger_source=TriggerSource.ALERTMANAGER,
            target_services=["data-worker"],
            retry_count=4,
        )


def test_trigger_source_planner():
    state = AgentState(
        trigger_source=TriggerSource.PLANNER_REQUEST,
        target_services=["api-gateway", "data-worker"],
    )
    assert state.trigger_source == TriggerSource.PLANNER_REQUEST
    assert len(state.target_services) == 2
