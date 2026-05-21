import subprocess
import time

import httpx
from langchain_core.tools import tool


@tool
def trigger_test_pipeline(deployment_name: str, namespace: str = "aiops-sandbox") -> str:
    """Deploy a service to sandbox namespace and wait for it to become ready.

    Args:
        deployment_name: Name of the K8s deployment to wait for
        namespace: Target namespace

    Returns:
        Status of the deployment rollout.
    """
    result = subprocess.run(
        ["kubectl", "rollout", "status", f"deployment/{deployment_name}", "-n", namespace, "--timeout=120s"],
        capture_output=True,
        text=True,
        timeout=150,
    )
    if result.returncode != 0:
        return f"ROLLOUT FAILED: {result.stderr}\n{result.stdout}"
    return f"OK: {result.stdout}"


@tool
def run_health_check(url: str, retries: int = 5, interval: float = 2.0) -> str:
    """Run health check against a service endpoint with retries.

    Args:
        url: Full URL to the health endpoint (e.g., 'http://localhost:8000/healthz')
        retries: Number of retry attempts
        interval: Seconds between retries

    Returns:
        Health check result or error details.
    """
    last_error = ""
    for i in range(retries):
        try:
            resp = httpx.get(url, timeout=5.0)
            if resp.status_code == 200:
                return f"OK: {resp.text}"
            last_error = f"HTTP {resp.status_code}: {resp.text}"
        except Exception as e:
            last_error = str(e)
        time.sleep(interval)

    return f"HEALTH CHECK FAILED after {retries} attempts: {last_error}"


@tool
def run_load_test(target_url: str, duration: str = "30s", rps: int = 50) -> str:
    """Run a basic load test against a service endpoint using k6 or curl-based stress.

    Args:
        target_url: URL to hit with load
        duration: Test duration (e.g., '30s', '1m')
        rps: Requests per second target

    Returns:
        Load test summary including latency and error rate.
    """
    # Use a simple curl-based load test if k6 is not available
    result = subprocess.run(
        [
            "k6",
            "run",
            "--vus",
            str(rps),
            "--duration",
            duration,
            "-e",
            f"TARGET_URL={target_url}",
            "/app/tests/load/k6-script.js",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        return f"LOAD TEST FAILED: {result.stderr}"
    return result.stdout
