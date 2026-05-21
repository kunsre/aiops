from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PipelineStatus(str, Enum):
    INIT = "INIT"
    ANALYZING = "ANALYZING"
    IMPLEMENTING = "IMPLEMENTING"
    TESTING = "TESTING"
    RETRYING = "RETRYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TriggerSource(str, Enum):
    ALERTMANAGER = "ALERTMANAGER"
    PLANNER_REQUEST = "PLANNER_REQUEST"


class RCAReport(BaseModel):
    root_cause_service: str
    failure_mode: str
    evidence_logs: list[str] = Field(default_factory=list)
    recommended_action: Optional[str] = None


class ProposedChange(BaseModel):
    repository: str
    file_path: str
    diff: str
    pull_request_url: Optional[str] = None


class EvaluationResult(BaseModel):
    is_passed: bool
    error_logs: list[str] = Field(default_factory=list)
    failed_resource: Optional[str] = None
    failure_phase: Optional[str] = None
    suggested_fix_hint: Optional[str] = None


class AgentState(BaseModel):
    pipeline_id: UUID = Field(default_factory=uuid4)
    trigger_source: TriggerSource
    target_services: list[str]
    status: PipelineStatus = PipelineStatus.INIT
    rca_report: Optional[RCAReport] = None
    proposed_changes: list[ProposedChange] = Field(default_factory=list)
    evaluation_results: Optional[EvaluationResult] = None
    retry_count: int = Field(default=0, le=3)
    messages: list[dict] = Field(default_factory=list)
