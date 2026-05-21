import os
import subprocess
import tempfile

import httpx
from langchain_core.tools import tool

from aiops_agents.config import GITHUB_REPO, GITHUB_TOKEN


@tool
def get_file_content(file_path: str, branch: str = "main") -> str:
    """Get content of a file from the GitHub repository.

    Args:
        file_path: Path to file in the repository (e.g., 'services/data-worker/k8s/deployment.yaml')
        branch: Git branch to read from

    Returns:
        File content as string.
    """
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3.raw"}
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

    Args:
        file_path: Path to the file in the repository
        old_content: Exact string to find and replace
        new_content: Replacement string
        branch: Branch to create the commit on (will create new branch from this)

    Returns:
        Status message with the new branch name.
    """
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    # Get current file
    resp = httpx.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}",
        headers=headers,
        params={"ref": branch},
        timeout=10.0,
    )
    resp.raise_for_status()
    file_data = resp.json()

    import base64

    content = base64.b64decode(file_data["content"]).decode()
    if old_content not in content:
        return f"ERROR: old_content not found in {file_path}"

    new_file_content = content.replace(old_content, new_content)
    encoded = base64.b64encode(new_file_content.encode()).decode()

    # Create fix branch and commit
    fix_branch = f"fix/aiops-auto-{file_path.replace('/', '-')}"

    # Create branch
    main_ref = httpx.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/git/ref/heads/{branch}",
        headers=headers,
        timeout=10.0,
    )
    main_ref.raise_for_status()
    sha = main_ref.json()["object"]["sha"]

    httpx.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/git/refs",
        headers=headers,
        json={"ref": f"refs/heads/{fix_branch}", "sha": sha},
        timeout=10.0,
    )

    # Update file on new branch
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
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = httpx.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/pulls",
        headers=headers,
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
