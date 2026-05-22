"""Agent tool functions for interacting with external systems."""

from aiops_agents.tools.git_ops import create_pull_request, get_file_content, patch_file
from aiops_agents.tools.gitops import approve_and_merge_pr, get_argocd_app_status, sync_argocd_app
from aiops_agents.tools.k8s_ops import (
    kubectl_apply,
    kubectl_describe,
    kubectl_exec,
    kubectl_get,
    kubectl_get_configmap,
    kubectl_get_events,
    kubectl_get_pod_logs,
    kubectl_rollout_restart,
    kubectl_scale,
    kubectl_top,
)
from aiops_agents.tools.logql import query_logql
from aiops_agents.tools.promql import query_promql, query_promql_range
from aiops_agents.tools.source_code import get_recent_commits, list_directory, read_source_file, search_code
from aiops_agents.tools.test_runner import run_health_check, run_load_test, trigger_test_pipeline

# Monitor: 관측 평면만 (모니터링 스택을 통해서만 분석)
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
    kubectl_apply,  # dry-run 검증용
]

# Evaluator: 배포 + 검증 + 제어
EVALUATOR_TOOLS = [
    kubectl_apply,
    kubectl_get_pod_logs,
    kubectl_describe,
    kubectl_get,
    kubectl_get_events,
    kubectl_exec,
    kubectl_top,
    kubectl_get_configmap,
    kubectl_rollout_restart,
    kubectl_scale,
    trigger_test_pipeline,
    run_health_check,
    run_load_test,
    approve_and_merge_pr,
    sync_argocd_app,
    get_argocd_app_status,
]
