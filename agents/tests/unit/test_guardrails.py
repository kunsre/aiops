import time
from aiops_agents.guardrails import check_cooldown, check_memory_limit, parse_memory, record_trigger


def test_parse_memory():
    assert parse_memory("256Mi") == 256 * 1024 * 1024
    assert parse_memory("1Gi") == 1024 * 1024 * 1024
    assert parse_memory("4Gi") == 4 * 1024 * 1024 * 1024


def test_check_memory_limit_ok():
    assert check_memory_limit("data-worker", "512Mi") is None
    assert check_memory_limit("data-worker", "2Gi") is None


def test_check_memory_limit_exceeded():
    result = check_memory_limit("data-worker", "8Gi")
    assert result is not None
    assert "MAX LIMIT EXCEEDED" in result
    assert "Escalate" in result


def test_cooldown_not_triggered():
    assert check_cooldown("new-service") is None


def test_cooldown_triggered():
    record_trigger("test-service")
    result = check_cooldown("test-service")
    assert result is not None
    assert "COOLDOWN" in result
