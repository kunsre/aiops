"""Read-only Kubernetes diagnostic tools.

These tools provide observability into cluster state without
any write/mutate operations. All deployments go through ArgoCD.
"""
import subprocess

from langchain_core.tools import tool


@tool
def kubectl_get_pod_logs(pod_selector: str, namespace: str = "aiops", previous: bool = False, tail: int = 200) -> str:
    """Get logs from a Kubernetes pod or deployment.

    Args:
        pod_selector: Pod name, label selector like 'app=data-worker', or 'deployment/data-worker'
        namespace: Pod namespace
        previous: If True, get logs from the previous terminated container
        tail: Number of lines from the end

    Returns:
        Pod log output.
    """
    if "=" in pod_selector and "/" not in pod_selector:
        cmd = ["kubectl", "logs", "-l", pod_selector, "-n", namespace, f"--tail={tail}"]
    else:
        cmd = ["kubectl", "logs", pod_selector, "-n", namespace, f"--tail={tail}"]
    if previous:
        cmd.append("--previous")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return f"ERROR: {result.stderr}"
    return result.stdout


@tool
def kubectl_describe(resource: str, name: str, namespace: str = "aiops") -> str:
    """Describe any Kubernetes resource to get events and detailed status.

    Args:
        resource: Resource type (e.g., 'pod', 'deployment', 'service', 'node', 'pvc')
        name: Resource name
        namespace: Resource namespace

    Returns:
        Full resource description including events section.
    """
    result = subprocess.run(
        ["kubectl", "describe", resource, name, "-n", namespace],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return f"ERROR: {result.stderr}"
    return result.stdout


@tool
def kubectl_get(resource: str, namespace: str = "aiops", output: str = "wide") -> str:
    """List Kubernetes resources with their status.

    Args:
        resource: Resource type (e.g., 'pods', 'deployments', 'services', 'events', 'nodes')
        namespace: Resource namespace (use 'all' for all namespaces)
        output: Output format ('wide', 'yaml', 'json')

    Returns:
        Resource listing.
    """
    cmd = ["kubectl", "get", resource, f"-o={output}"]
    if namespace == "all":
        cmd.append("--all-namespaces")
    else:
        cmd.extend(["-n", namespace])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return f"ERROR: {result.stderr}"
    return result.stdout


@tool
def kubectl_get_events(namespace: str = "aiops", field_selector: str = "") -> str:
    """Get Kubernetes events, optionally filtered.

    Args:
        namespace: Namespace to query events from
        field_selector: Optional field selector (e.g., 'reason=OOMKilling', 'involvedObject.name=data-worker')

    Returns:
        Recent cluster events sorted by time.
    """
    cmd = ["kubectl", "get", "events", "-n", namespace, "--sort-by=.lastTimestamp"]
    if field_selector:
        cmd.append(f"--field-selector={field_selector}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return f"ERROR: {result.stderr}"
    return result.stdout


@tool
def kubectl_top(resource: str = "pods", namespace: str = "aiops") -> str:
    """Get resource usage (CPU/memory) for pods or nodes.

    Args:
        resource: 'pods' or 'nodes'
        namespace: Namespace for pods (ignored for nodes)

    Returns:
        CPU and memory usage table.
    """
    cmd = ["kubectl", "top", resource]
    if resource == "pods":
        cmd.extend(["-n", namespace])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return f"ERROR: {result.stderr}"
    return result.stdout
