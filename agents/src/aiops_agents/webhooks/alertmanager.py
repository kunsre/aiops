import logging
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

from aiops_agents.guardrails import check_cooldown, record_trigger
from aiops_agents.runner import run_pipeline
from aiops_agents.state import AgentState, TriggerSource
from aiops_agents.webhooks.jandi import send_jandi_alert

logger = logging.getLogger(__name__)

app = FastAPI(title="AIOps Alert Receiver")


class Alert(BaseModel):
    status: str
    labels: dict
    annotations: dict
    startsAt: str
    endsAt: str


class AlertmanagerPayload(BaseModel):
    version: str
    status: str
    alerts: list[Alert]


def _run(alert_details: str, services: list[str]):
    try:
        run_pipeline(alert_content=alert_details, target_services=services)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)


@app.post("/webhook/alertmanager")
async def receive_alert(payload: AlertmanagerPayload, background_tasks: BackgroundTasks):
    """Receive Alertmanager webhook and trigger the agent pipeline."""
    firing_alerts = [a for a in payload.alerts if a.status == "firing"]
    if not firing_alerts:
        return {"status": "ignored", "reason": "no firing alerts"}

    services = list({a.labels.get("service", a.labels.get("container", "unknown")) for a in firing_alerts})
    alert_details = "\n".join(
        f"- [{a.labels.get('alertname')}] {a.annotations.get('summary', '')}" for a in firing_alerts
    )

    # 쿨다운 체크
    for svc in services:
        cooldown_msg = check_cooldown(svc)
        if cooldown_msg:
            return {"status": "cooldown", "message": cooldown_msg}
        record_trigger(svc)

    # Jandi 알림 발송
    for a in firing_alerts:
        send_jandi_alert(
            alertname=a.labels.get("alertname", "Unknown"),
            service=a.labels.get("service", a.labels.get("container", "unknown")),
            summary=a.annotations.get("summary", "No summary"),
            status=a.status,
        )

    background_tasks.add_task(_run, alert_details, services)

    return {"status": "pipeline_triggered", "services": services}


@app.get("/healthz")
async def health():
    return {"status": "ok"}
