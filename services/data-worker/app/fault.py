"""Intentional fault injection endpoints for AIOps demo."""

import asyncio
import os
import resource
import time

# === OOM Fault ===
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
    return usage.ru_maxrss / (1024 * 1024)


# === HTTP 500 Fault ===
_error_mode = False


def enable_error_mode():
    global _error_mode
    _error_mode = True


def disable_error_mode():
    global _error_mode
    _error_mode = False


def is_error_mode() -> bool:
    return _error_mode


# === Latency Fault ===
_latency_ms = 0


def set_latency(ms: int):
    global _latency_ms
    _latency_ms = ms


def get_latency() -> int:
    return _latency_ms


async def apply_latency():
    if _latency_ms > 0:
        await asyncio.sleep(_latency_ms / 1000.0)


# === CPU Spike Fault ===
_cpu_burn = False


def enable_cpu_burn():
    global _cpu_burn
    _cpu_burn = True


def disable_cpu_burn():
    global _cpu_burn
    _cpu_burn = False


async def trigger_cpu_burn():
    """Burn CPU in a tight loop until disabled."""
    while _cpu_burn:
        _ = sum(i * i for i in range(100000))
        await asyncio.sleep(0.01)


# === Disk Fill Fault ===
_disk_files: list[str] = []


def trigger_disk_fill(size_mb: int = 100):
    """Write large temp files to fill disk."""
    import tempfile
    f = tempfile.NamedTemporaryFile(delete=False, suffix=".fill")
    f.write(b"X" * (size_mb * 1024 * 1024))
    f.close()
    _disk_files.append(f.name)
    return f.name


def cleanup_disk_fill():
    import os as _os
    for f in _disk_files:
        try:
            _os.unlink(f)
        except OSError:
            pass
    _disk_files.clear()
