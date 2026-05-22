import asyncio
import os

from fastapi import BackgroundTasks, FastAPI, HTTPException

from app.config import BATCH_SIZE, DB_TIMEOUT, MAX_RETRIES
from app.fault import (
    apply_latency,
    cleanup_disk_fill,
    disable_cpu_burn,
    disable_error_mode,
    enable_cpu_burn,
    enable_error_mode,
    get_latency,
    get_memory_usage_mb,
    is_error_mode,
    set_latency,
    trigger_cpu_burn,
    trigger_disk_fill,
    trigger_oom,
)

app = FastAPI(title="data-worker", version="0.1.0")


@app.get("/healthz")
async def health():
    if is_error_mode():
        raise HTTPException(status_code=500, detail="Service in error mode")
    return {"status": "ok", "memory_mb": get_memory_usage_mb()}


@app.post("/process")
async def process_data():
    """Simulate data processing workload."""
    if is_error_mode():
        raise HTTPException(status_code=500, detail="Processing failed: NullPointerException in DataPipeline.transform()")
    await apply_latency()

    # BUG: DB_TIMEOUT=1s causes timeout on any query taking >1s
    for attempt in range(MAX_RETRIES + 1):
        try:
            await asyncio.wait_for(_simulate_db_query(), timeout=DB_TIMEOUT)
            break
        except asyncio.TimeoutError:
            if attempt == MAX_RETRIES:
                raise HTTPException(
                    status_code=504,
                    detail=f"Database query timeout after {DB_TIMEOUT}s (retries: {MAX_RETRIES})",
                )

    return {"status": "processed", "records": BATCH_SIZE}


@app.post("/process/batch")
async def process_batch():
    """Process large batch - BUG: BATCH_SIZE=10000 causes memory spike."""
    data = [bytearray(1024) for _ in range(BATCH_SIZE)]
    await asyncio.sleep(0.1)
    return {"status": "batch_processed", "records": len(data), "batch_size": BATCH_SIZE}


async def _simulate_db_query():
    """Simulates a DB query that takes 2-3 seconds."""
    await asyncio.sleep(2.5)


# === Fault Injection Endpoints ===

@app.post("/fault/oom")
async def fault_oom(background_tasks: BackgroundTasks):
    """Trigger memory leak → OOMKilled."""
    background_tasks.add_task(trigger_oom)
    return {"status": "oom_triggered", "message": "Memory leak started"}


@app.post("/fault/error500")
async def fault_error500():
    """Enable HTTP 500 on all endpoints."""
    enable_error_mode()
    return {"status": "error_mode_enabled", "message": "All requests will return 500"}


@app.post("/fault/error500/disable")
async def fault_error500_disable():
    disable_error_mode()
    return {"status": "error_mode_disabled"}


@app.post("/fault/latency/{ms}")
async def fault_latency(ms: int):
    set_latency(ms)
    return {"status": "latency_injected", "latency_ms": ms}


@app.post("/fault/latency/disable")
async def fault_latency_disable():
    set_latency(0)
    return {"status": "latency_removed"}


@app.post("/fault/cpu")
async def fault_cpu(background_tasks: BackgroundTasks):
    enable_cpu_burn()
    background_tasks.add_task(trigger_cpu_burn)
    return {"status": "cpu_burn_started"}


@app.post("/fault/cpu/disable")
async def fault_cpu_disable():
    disable_cpu_burn()
    return {"status": "cpu_burn_stopped"}


@app.post("/fault/disk/{size_mb}")
async def fault_disk(size_mb: int = 100):
    path = trigger_disk_fill(size_mb)
    return {"status": "disk_filled", "file": path, "size_mb": size_mb}


@app.post("/fault/disk/cleanup")
async def fault_disk_cleanup():
    cleanup_disk_fill()
    return {"status": "disk_cleaned"}


@app.post("/fault/crash")
async def fault_crash():
    os._exit(1)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
