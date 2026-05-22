"""Jandi notification forwarder for Alertmanager alerts and pipeline status."""

import os

import httpx

JANDI_WEBHOOK_URL = os.getenv(
    "JANDI_WEBHOOK_URL",
    "https://wh.jandi.com/connect-api/webhook/279/04a5f22f40ee2a4d035265ecbc639fcc",
)


def _send(body: str, color: str, info: list[dict]) -> bool:
    payload = {
        "body": body,
        "connectColor": color,
        "connectInfo": info,
    }
    headers = {
        "Accept": "application/vnd.tosslab.jandi-v2+json",
        "Content-Type": "application/json",
    }
    try:
        resp = httpx.post(JANDI_WEBHOOK_URL, json=payload, headers=headers, timeout=5.0)
        return resp.status_code == 200
    except Exception:
        return False


def send_jandi_alert(alertname: str, service: str, summary: str, status: str = "firing"):
    """Send alert notification to Jandi."""
    color = "#FF0000" if status == "firing" else "#00C853"
    icon = "🚨" if status == "firing" else "✅"
    return _send(
        body=f"{icon} [{alertname}] {service}",
        color=color,
        info=[
            {"title": "Service", "description": service},
            {"title": "Summary", "description": summary},
            {"title": "Status", "description": status.upper()},
        ],
    )


def send_jandi_monitor(service: str, failure_mode: str, action: str):
    """Monitor RCA 결과 알림."""
    return _send(
        body=f"🔍 [Monitor] RCA 완료 - {service}",
        color="#FFA000",
        info=[
            {"title": "Root Cause", "description": service},
            {"title": "Failure Mode", "description": failure_mode},
            {"title": "Recommended Action", "description": action},
        ],
    )


def send_jandi_generator(service: str, pr_url: str, diff_summary: str):
    """Generator PR 생성 알림."""
    return _send(
        body=f"🔧 [Generator] PR 생성 - {service}",
        color="#2196F3",
        info=[
            {"title": "Service", "description": service},
            {"title": "PR", "description": pr_url},
            {"title": "Change", "description": diff_summary},
        ],
    )


def send_jandi_evaluator(service: str, passed: bool, detail: str):
    """Evaluator 검증 결과 알림."""
    if passed:
        return _send(
            body=f"✅ [Evaluator] 검증 통과 - {service}",
            color="#00C853",
            info=[
                {"title": "Service", "description": service},
                {"title": "Result", "description": "PASS - 배포 완료"},
                {"title": "Detail", "description": detail},
            ],
        )
    else:
        return _send(
            body=f"❌ [Evaluator] 검증 실패 - {service}",
            color="#FF0000",
            info=[
                {"title": "Service", "description": service},
                {"title": "Result", "description": "FAIL - 재시도 예정"},
                {"title": "Detail", "description": detail[:300]},
            ],
        )


def send_jandi_review_request(
    service: str, pr_url: str, rca_summary: str, fix_summary: str, evaluator_verdict: str
):
    """PR 리뷰 요청 알림 (Human-in-the-loop)."""
    return _send(
        body=f"👀 [리뷰 요청] {service} 자가복구 PR 생성됨",
        color="#9C27B0",
        info=[
            {"title": "Service", "description": service},
            {"title": "RCA", "description": rca_summary[:300]},
            {"title": "Fix", "description": fix_summary[:300]},
            {"title": "검증 결과", "description": evaluator_verdict[:200]},
            {"title": "PR", "description": pr_url},
        ],
    )


def send_jandi_pipeline_complete(service: str, status: str):
    """파이프라인 최종 결과 알림."""
    if status == "COMPLETED":
        return _send(
            body=f"✅ [AIOps] 검증 완료 - 리뷰 승인 대기 중",
            color="#9C27B0",
            info=[
                {"title": "Service", "description": service},
                {"title": "Status", "description": "에이전트 검증 통과 → 운영자 머지 승인 대기"},
            ],
        )
    elif status == "RETRYING":
        return _send(
            body=f"🔄 [AIOps] 재시도 중 - {service}",
            color="#FFA000",
            info=[
                {"title": "Service", "description": service},
                {"title": "Status", "description": "Evaluator 검증 실패 → Generator 재수정 중"},
            ],
        )
    else:
        return _send(
            body=f"💀 [AIOps] 자가복구 실패 - {service}",
            color="#FF0000",
            info=[
                {"title": "Service", "description": service},
                {"title": "Status", "description": f"복구 실패 ({status}) - 운영자 수동 개입 필요"},
            ],
        )
