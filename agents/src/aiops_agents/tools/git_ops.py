import base64
import time

import httpx
from langchain_core.tools import tool

from aiops_agents.config import GITHUB_REPO, GITHUB_TOKEN


def _headers():
    return {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}


@tool
def get_file_content(file_path: str, branch: str = "main") -> str:
    """Get content of a file from the GitHub repository.

    Args:
        file_path: Path to file in the repository (e.g., 'services/data-worker/k8s/deployment.yaml')
        branch: Git branch to read from

    Returns:
        File content as string.
    """
    headers = {**_headers(), "Accept": "application/vnd.github.v3.raw"}
    response = httpx.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}",
        headers=headers,
        params={"ref": branch},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.text


@tool
def patch_file(file_path: str, old_content: str, new_content: str, branch: str = "main") -> str:
    """Patch a specific section of a file in the repository by replacing old content with new.

    Always creates a fresh branch from latest main to avoid merge conflicts.

    Args:
        file_path: Path to the file in the repository
        old_content: Exact string to find and replace
        new_content: Replacement string
        branch: Base branch to create fix from (always reads latest)

    Returns:
        Status message with the new branch name.
    """
    headers = _headers()

    # Always get latest file from main (not a stale branch)
    resp = httpx.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}",
        headers=headers,
        params={"ref": branch},
        timeout=10.0,
    )
    resp.raise_for_status()
    file_data = resp.json()

    content = base64.b64decode(file_data["content"]).decode()
    if old_content not in content:
        return f"ERROR: old_content not found in {file_path}"

    new_file_content = content.replace(old_content, new_content)
    encoded = base64.b64encode(new_file_content.encode()).decode()

    # Unique branch name with timestamp (prevents conflict with old branches)
    timestamp = int(time.time())
    fix_branch = f"fix/aiops-{timestamp}"

    # Get latest main SHA
    main_ref = httpx.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/git/ref/heads/{branch}",
        headers=headers,
        timeout=10.0,
    )
    main_ref.raise_for_status()
    sha = main_ref.json()["object"]["sha"]

    # Delete old branch if exists (cleanup)
    httpx.delete(
        f"https://api.github.com/repos/{GITHUB_REPO}/git/refs/heads/{fix_branch}",
        headers=headers,
        timeout=5.0,
    )

    # Create fresh branch from latest main
    httpx.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/git/refs",
        headers=headers,
        json={"ref": f"refs/heads/{fix_branch}", "sha": sha},
        timeout=10.0,
    )

    # Commit the change
    httpx.put(
        f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}",
        headers=headers,
        json={
            "message": f"fix: auto-patch {file_path}",
            "content": encoded,
            "sha": file_data["sha"],
            "branch": fix_branch,
        },
        timeout=10.0,
    )

    return f"OK: patched {file_path} on branch {fix_branch}"


@tool
def create_pull_request(title: str, body: str, head_branch: str, base_branch: str = "main") -> str:
    """Create a Pull Request on GitHub.

    Args:
        title: PR title
        body: PR description with fix rationale
        head_branch: Source branch with the fix
        base_branch: Target branch (usually 'main')

    Returns:
        Pull request URL.
    """
    response = httpx.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/pulls",
        headers=_headers(),
        json={
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
        },
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()["html_url"]
