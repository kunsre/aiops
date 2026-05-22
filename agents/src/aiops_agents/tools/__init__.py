"""Agent tool functions for interacting with external systems."""

from aiops_agents.tools.git_ops import create_pull_request, get_file_content, patch_file
from aiops_agents.tools.logql import query_logql
from aiops_agents.tools.promql import query_promql, query_promql_range
from aiops_agents.tools.source_code import get_recent_commits, list_directory, read_source_file, search_code

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

# Evaluator: 코드 리뷰만 (클러스터 접근 없음)
# - PR의 변경 내용을 읽고 검증
# - 머지/배포 권한 없음 → 검증 통과 시 "승인 대기" 알림
EVALUATOR_TOOLS = [
    get_file_content,
    read_source_file,
    list_directory,
    search_code,
]
