"""Pipeline guardrails: max limits, cooldown, safety checks."""

import time
from typing import Optional

# 서비스별 memory limit 상한선
MAX_MEMORY_LIMITS = {
    "data-worker": "4Gi",
    "api-gateway": "2Gi",
    "core-business": "4Gi",
    "bff-service": "2Gi",
}

# 쿨다운: 같은 서비스에 대해 최소 N초 간격으로만 파이프라인 실행
COOLDOWN_SECONDS = 300  # 5분

# 최근 파이프라인 실행 기록 {service: timestamp}
_last_triggered: dict[str, float] = {}


def check_cooldown(service: str) -> Optional[str]:
    """Check if service is in cooldown period.

    Returns None if OK, error message if in cooldown.
    """
    last = _last_triggered.get(service, 0)
    elapsed = time.time() - last
    if elapsed < COOLDOWN_SECONDS:
        remaining = int(COOLDOWN_SECONDS - elapsed)
        return f"COOLDOWN: {service} was triggered {int(elapsed)}s ago. Wait {remaining}s more."
    return None


def record_trigger(service: str):
    """Record that a pipeline was triggered for this service."""
    _last_triggered[service] = time.time()


def parse_memory(mem_str: str) -> int:
    """Parse K8s memory string to bytes."""
    mem_str = mem_str.strip()
    if mem_str.endswith("Gi"):
        return int(float(mem_str[:-2]) * 1024 * 1024 * 1024)
    if mem_str.endswith("Mi"):
        return int(float(mem_str[:-2]) * 1024 * 1024)
    if mem_str.endswith("Ki"):
        return int(float(mem_str[:-2]) * 1024)
    return int(mem_str)


def check_memory_limit(service: str, proposed_limit: str) -> Optional[str]:
    """Check if proposed memory limit exceeds maximum allowed.

    Returns None if OK, error message if exceeded.
    """
    max_limit_str = MAX_MEMORY_LIMITS.get(service, "4Gi")
    max_bytes = parse_memory(max_limit_str)
    proposed_bytes = parse_memory(proposed_limit)

    if proposed_bytes > max_bytes:
        return (
            f"MAX LIMIT EXCEEDED: {service} proposed {proposed_limit} exceeds max {max_limit_str}. "
            f"Escalate to human operator - likely a memory leak that needs code fix."
        )
    return None
