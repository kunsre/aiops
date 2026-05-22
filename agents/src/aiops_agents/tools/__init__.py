"""Agent tool functions for interacting with external systems."""

from aiops_agents.tools.aws_ops import (
    aws_cli,
    aws_cloudwatch_get_metric,
    aws_describe_alarms,
    aws_describe_ec2_instances,
)
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

# All tools available to agents
MONITORING_TOOLS = [
    query_promql,
    query_promql_range,
    query_logql,
    kubectl_get_pod_logs,
    kubectl_describe,
    kubectl_get,
    kubectl_get_events,
    kubectl_top,
    kubectl_exec,
    kubectl_get_configmap,
    aws_cloudwatch_get_metric,
    aws_describe_alarms,
    aws_describe_ec2_instances,
    aws_cli,
]

GENERATOR_TOOLS = [
    get_file_content,
    read_source_file,
    list_directory,
    search_code,
    get_recent_commits,
    patch_file,
    create_pull_request,
    kubectl_apply,
]

EVALUATOR_TOOLS = [
    kubectl_apply,
    kubectl_get_pod_logs,
    kubectl_describe,
    kubectl_get,
    kubectl_get_events,
    kubectl_exec,
    kubectl_top,
    trigger_test_pipeline,
    run_health_check,
    run_load_test,
    approve_and_merge_pr,
    sync_argocd_app,
    get_argocd_app_status,
    kubectl_rollout_restart,
    kubectl_scale,
]
