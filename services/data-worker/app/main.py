import asyncio
import os

from fastapi import FastAPI, BackgroundTasks

from app.fault import trigger_oom, get_memory_usage_mb

app = FastAPI(title="data-worker", version="0.1.0")


@app.get("/healthz")
async def health():
    return {"status": "ok", "memory_mb": get_memory_usage_mb()}


@app.post("/process")
async def process_data():
    """Simulate data processing workload."""
    await asyncio.sleep(0.5)
    return {"status": "processed", "records": 1000}


@app.post("/fault/oom")
async def fault_oom(background_tasks: BackgroundTasks):
    """Trigger intentional memory leak for OOM demo."""
    background_tasks.add_task(trigger_oom)
    return {"status": "oom_triggered", "message": "Memory leak started in background"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
