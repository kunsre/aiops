import logging
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

from aiops_agents.graph import graph
from aiops_agents.state import AgentState, TriggerSource

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


def _run_pipeline(state: AgentState):
    try:
        result = graph.invoke(state.model_dump())
        logger.info(f"Pipeline {state.pipeline_id} completed with status: {result.get('status')}")
    except Exception as e:
        logger.error(f"Pipeline {state.pipeline_id} failed: {e}")


@app.post("/webhook/alertmanager")
async def receive_alert(payload: AlertmanagerPayload, background_tasks: BackgroundTasks):
    """Receive Alertmanager webhook and trigger the agent pipeline."""
    firing_alerts = [a for a in payload.alerts if a.status == "firing"]
    if not firing_alerts:
        return {"status": "ignored", "reason": "no firing alerts"}

    # Extract affected services from alert labels
    services = list({a.labels.get("service", "unknown") for a in firing_alerts})
    alert_details = "\n".join(
        f"- [{a.labels.get('alertname')}] {a.annotations.get('summary', '')}" for a in firing_alerts
    )

    state = AgentState(
        pipeline_id=uuid4(),
        trigger_source=TriggerSource.ALERTMANAGER,
        target_services=services,
        messages=[{"role": "alert", "content": alert_details}],
    )

    background_tasks.add_task(_run_pipeline, state)

    return {"status": "pipeline_triggered", "pipeline_id": str(state.pipeline_id), "services": services}


@app.get("/healthz")
async def health():
    return {"status": "ok"}
