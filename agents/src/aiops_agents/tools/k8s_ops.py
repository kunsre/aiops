import subprocess

from langchain_core.tools import tool


@tool
def kubectl_apply(manifest_yaml: str, namespace: str = "aiops-sandbox") -> str:
    """Apply a Kubernetes manifest to a namespace (dry-run validated first).

    Args:
        manifest_yaml: YAML content of the K8s resource to apply
        namespace: Target namespace (defaults to sandbox for safety)

    Returns:
        kubectl output or error message.
    """
    dry_run = subprocess.run(
        ["kubectl", "apply", "-f", "-", "--dry-run=client", "-n", namespace],
        input=manifest_yaml,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if dry_run.returncode != 0:
        return f"DRY-RUN FAILED: {dry_run.stderr}"

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
def kubectl_get_pod_logs(pod_selector: str, namespace: str = "aiops", previous: bool = False, tail: int = 200) -> str:
    """Get logs from a Kubernetes pod or deployment.

    Args:
        pod_selector: Pod name, or label selector like 'app=data-worker', or 'deployment/data-worker'
        namespace: Pod namespace
        previous: If True, get logs from the previous terminated container
        tail: Number of lines from the end

    Returns:
        Pod log output.
    """
    cmd = ["kubectl", "logs", pod_selector, "-n", namespace, f"--tail={tail}"]
    if previous:
        cmd.append("--previous")
    if "=" in pod_selector and "/" not in pod_selector:
        cmd = ["kubectl", "logs", "-l", pod_selector, "-n", namespace, f"--tail={tail}"]
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
        name: Resource name (or label selector with -l prefix)
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
        resource: Resource type and optional name (e.g., 'pods', 'deployments', 'services', 'events', 'nodes', 'pvc')
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
def kubectl_exec(pod_selector: str, command: str, namespace: str = "aiops") -> str:
    """Execute a command inside a running pod for diagnostics.

    Args:
        pod_selector: Pod name (e.g., 'data-worker-abc123')
        command: Shell command to run (e.g., 'df -h', 'cat /proc/meminfo', 'netstat -tlnp')
        namespace: Pod namespace

    Returns:
        Command output from inside the container.
    """
    result = subprocess.run(
        ["kubectl", "exec", pod_selector, "-n", namespace, "--", "sh", "-c", command],
        capture_output=True,
        text=True,
        timeout=30,
    )
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
def kubectl_get_configmap(name: str, namespace: str = "aiops") -> str:
    """Get a ConfigMap's data content.

    Args:
        name: ConfigMap name
        namespace: ConfigMap namespace

    Returns:
        ConfigMap data as YAML.
    """
    result = subprocess.run(
        ["kubectl", "get", "configmap", name, "-n", namespace, "-o=yaml"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return f"ERROR: {result.stderr}"
    return result.stdout


@tool
def kubectl_rollout_restart(deployment: str, namespace: str = "aiops") -> str:
    """Restart a deployment by triggering a rolling restart.

    Args:
        deployment: Deployment name (e.g., 'data-worker')
        namespace: Deployment namespace

    Returns:
        Rollout restart status.
    """
    result = subprocess.run(
        ["kubectl", "rollout", "restart", f"deployment/{deployment}", "-n", namespace],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return f"ERROR: {result.stderr}"
    return f"OK: {result.stdout}"


@tool
def kubectl_scale(deployment: str, replicas: int, namespace: str = "aiops") -> str:
    """Scale a deployment to a specific number of replicas.

    Args:
        deployment: Deployment name
        replicas: Desired replica count
        namespace: Deployment namespace

    Returns:
        Scale result.
    """
    result = subprocess.run(
        ["kubectl", "scale", f"deployment/{deployment}", f"--replicas={replicas}", "-n", namespace],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return f"ERROR: {result.stderr}"
    return f"OK: {result.stdout}"
