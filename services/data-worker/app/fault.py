import asyncio
import os
import resource

_leak_storage: list[bytearray] = []

CHUNK_SIZE = int(os.getenv("OOM_CHUNK_SIZE", str(10 * 1024 * 1024)))  # 10MB default
CHUNK_INTERVAL = float(os.getenv("OOM_CHUNK_INTERVAL", "0.1"))


async def trigger_oom():
    """Allocate memory in chunks until OOMKilled by container runtime."""
    while True:
        _leak_storage.append(bytearray(CHUNK_SIZE))
        await asyncio.sleep(CHUNK_INTERVAL)


def get_memory_usage_mb() -> float:
    """Return current RSS memory usage in MB."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_maxrss / (1024 * 1024)  # macOS returns bytes
