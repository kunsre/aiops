from fastapi import FastAPI
from pydantic import BaseModel

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


@app.post("/webhook/alertmanager")
async def receive_alert(payload: AlertmanagerPayload):
    """Receive Alertmanager webhook and trigger the agent pipeline."""
    # TODO: invoke graph with alert data
    return {"status": "received", "alert_count": len(payload.alerts)}


@app.get("/healthz")
async def health():
    return {"status": "ok"}
