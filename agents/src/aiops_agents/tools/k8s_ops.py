import subprocess

from langchain_core.tools import tool


@tool
def kubectl_apply(manifest_yaml: str, namespace: str = "aiops-sandbox") -> str:
    """Apply a Kubernetes manifest to the sandbox namespace using dry-run first.

    Args:
        manifest_yaml: YAML content of the K8s resource to apply
        namespace: Target namespace (defaults to sandbox for safety)

    Returns:
        kubectl output or error message.
    """
    # Dry-run validation first
    dry_run = subprocess.run(
        ["kubectl", "apply", "-f", "-", "--dry-run=client", "-n", namespace],
        input=manifest_yaml,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if dry_run.returncode != 0:
        return f"DRY-RUN FAILED: {dry_run.stderr}"

    # Actual apply
    result = subprocess.run(
        ["kubectl", "apply", "-f", "-", "-n", namespace],
        input=manifest_yaml,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        return f"APPLY FAILED: {result.stderr}"
    return f"OK: {result.stdout}"


@tool
def kubectl_get_pod_logs(pod_name: str, namespace: str = "aiops-sandbox", previous: bool = False) -> str:
    """Get logs from a Kubernetes pod.

    Args:
        pod_name: Name of the pod (or deployment/name for latest pod)
        namespace: Pod namespace
        previous: If True, get logs from the previous terminated container

    Returns:
        Pod log output (stderr included for crashed containers).
    """
    cmd = ["kubectl", "logs", pod_name, "-n", namespace, "--tail=200"]
    if previous:
        cmd.append("--previous")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return f"ERROR: {result.stderr}"
    return result.stdout


@tool
def kubectl_describe_pod(pod_name: str, namespace: str = "aiops-sandbox") -> str:
    """Describe a Kubernetes pod to get events and status details.

    Args:
        pod_name: Name of the pod
        namespace: Pod namespace

    Returns:
        Pod description including events section.
    """
    result = subprocess.run(
        ["kubectl", "describe", "pod", pod_name, "-n", namespace],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return f"ERROR: {result.stderr}"
    return result.stdout
