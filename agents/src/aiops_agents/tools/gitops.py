import httpx
from langchain_core.tools import tool

from aiops_agents.config import ARGOCD_TOKEN, ARGOCD_URL, GITHUB_REPO, GITHUB_TOKEN


@tool
def approve_and_merge_pr(pr_number: int) -> str:
    """Approve and merge a Pull Request to trigger GitOps deployment.

    Args:
        pr_number: GitHub PR number to merge

    Returns:
        Merge status message.
    """
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    # Merge the PR
    response = httpx.put(
        f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}/merge",
        headers=headers,
        json={"merge_method": "squash"},
        timeout=10.0,
    )
    if response.status_code == 200:
        return f"OK: PR #{pr_number} merged successfully"
    return f"MERGE FAILED: {response.status_code} {response.text}"


@tool
def sync_argocd_app(app_name: str) -> str:
    """Trigger an ArgoCD application sync.

    Args:
        app_name: Name of the ArgoCD application to sync

    Returns:
        Sync status message.
    """
    headers = {"Authorization": f"Bearer {ARGOCD_TOKEN}"}
    response = httpx.post(
        f"{ARGOCD_URL}/api/v1/applications/{app_name}/sync",
        headers=headers,
        json={},
        timeout=30.0,
    )
    if response.status_code == 200:
        return f"OK: ArgoCD app '{app_name}' sync triggered"
    return f"SYNC FAILED: {response.status_code} {response.text}"


@tool
def get_argocd_app_status(app_name: str) -> str:
    """Get the current sync and health status of an ArgoCD application.

    Args:
        app_name: Name of the ArgoCD application

    Returns:
        JSON with sync status and health status.
    """
    headers = {"Authorization": f"Bearer {ARGOCD_TOKEN}"}
    response = httpx.get(
        f"{ARGOCD_URL}/api/v1/applications/{app_name}",
        headers=headers,
        timeout=10.0,
    )
    if response.status_code != 200:
        return f"ERROR: {response.status_code} {response.text}"

    app = response.json()
    status = app.get("status", {})
    return (
        f"sync: {status.get('sync', {}).get('status', 'unknown')}, "
        f"health: {status.get('health', {}).get('status', 'unknown')}"
    )
