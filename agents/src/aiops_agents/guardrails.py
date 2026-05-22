"""Pipeline guardrails: max limits, cooldown, token cap, safety checks."""

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

# LLM 호출 제한: 파이프라인 1회 실행 시 최대 호출 수
MAX_LLM_CALLS_PER_PIPELINE = 30

# Retry 간 대기 시간 (초)
RETRY_DELAY_SECONDS = 10

# 최근 파이프라인 실행 기록 {service: timestamp}
_last_triggered: dict[str, float] = {}


class TokenBudgetExceeded(Exception):
    """LLM 호출 횟수 초과."""
    pass


class LLMCallCounter:
    """파이프라인 내 LLM 호출 횟수 추적."""

    def __init__(self, max_calls: int = MAX_LLM_CALLS_PER_PIPELINE):
        self.max_calls = max_calls
        self.count = 0

    def increment(self):
        self.count += 1
        if self.count > self.max_calls:
            raise TokenBudgetExceeded(
                f"LLM 호출 {self.max_calls}회 초과. 파이프라인 강제 종료."
            )

    def remaining(self) -> int:
        return max(0, self.max_calls - self.count)


def check_cooldown(service: str) -> Optional[str]:
    """Check if service is in cooldown period."""
    last = _last_triggered.get(service, 0)
    elapsed = time.time() - last
    if elapsed < COOLDOWN_SECONDS:
        remaining = int(COOLDOWN_SECONDS - elapsed)
        return f"COOLDOWN: {service} was triggered {int(elapsed)}s ago. Wait {remaining}s more."
    return None


def record_trigger(service: str):
    """Record that a pipeline was triggered for this service."""
    _last_triggered[service] = time.time()


def reset_cooldown(service: str):
    """Reset cooldown for testing."""
    _last_triggered.pop(service, None)


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
    """Check if proposed memory limit exceeds maximum allowed."""
    max_limit_str = MAX_MEMORY_LIMITS.get(service, "4Gi")
    max_bytes = parse_memory(max_limit_str)
    proposed_bytes = parse_memory(proposed_limit)

    if proposed_bytes > max_bytes:
        return (
            f"MAX LIMIT EXCEEDED: {service} proposed {proposed_limit} exceeds max {max_limit_str}. "
            f"Escalate to human operator - likely a memory leak that needs code fix."
        )
    return None
