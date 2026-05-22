"""Agent tool functions for interacting with external systems."""

from aiops_agents.tools.git_ops import create_pull_request, get_file_content, patch_file
from aiops_agents.tools.gitops import approve_and_merge_pr, get_argocd_app_status, sync_argocd_app
from aiops_agents.tools.k8s_ops import (
    kubectl_describe,
    kubectl_get,
    kubectl_get_events,
    kubectl_get_pod_logs,
    kubectl_top,
)
from aiops_agents.tools.logql import query_logql
from aiops_agents.tools.promql import query_promql, query_promql_range
from aiops_agents.tools.source_code import get_recent_commits, list_directory, read_source_file, search_code
from aiops_agents.tools.test_runner import run_health_check, run_load_test, trigger_test_pipeline

# Monitor: 관측 평면만 (모니터링 스택 경유)
MONITORING_TOOLS = [
    query_promql,
    query_promql_range,
    query_logql,
]

# Generator: 코드 읽기 + 수정 + PR
GENERATOR_TOOLS = [
    read_source_file,
    list_directory,
    search_code,
    get_recent_commits,
    get_file_content,
    patch_file,
    create_pull_request,
]

# Evaluator: Read-Only 진단 + GitOps 배포 + 검증
# - 읽기만: logs, describe, get, events, top
# - 배포: PR merge → ArgoCD sync (직접 apply 없음)
# - 검증: health check, load test
EVALUATOR_TOOLS = [
    kubectl_get_pod_logs,
    kubectl_describe,
    kubectl_get,
    kubectl_get_events,
    kubectl_top,
    trigger_test_pipeline,
    run_health_check,
    run_load_test,
    approve_and_merge_pr,
    sync_argocd_app,
    get_argocd_app_status,
]
