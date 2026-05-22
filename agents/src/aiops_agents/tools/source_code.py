import httpx
from langchain_core.tools import tool

from aiops_agents.config import GITHUB_REPO, GITHUB_TOKEN


@tool
def read_source_file(file_path: str, branch: str = "main") -> str:
    """Read a source code file from the repository for analysis.

    Args:
        file_path: Path to file in the repo (e.g., 'services/data-worker/app/main.py')
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
    if response.status_code == 404:
        return f"FILE NOT FOUND: {file_path} on branch {branch}"
    response.raise_for_status()
    return response.text


@tool
def list_directory(path: str = "", branch: str = "main") -> str:
    """List files and directories in a repository path.

    Args:
        path: Directory path in repo (e.g., 'services/data-worker/app'). Empty for root.
        branch: Git branch

    Returns:
        List of files and directories with their types.
    """
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = httpx.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}",
        headers=headers,
        params={"ref": branch},
        timeout=10.0,
    )
    if response.status_code == 404:
        return f"PATH NOT FOUND: {path}"
    response.raise_for_status()

    items = response.json()
    if isinstance(items, list):
        return "\n".join(f"{'📁' if i['type'] == 'dir' else '📄'} {i['name']}" for i in items)
    return f"📄 {items['name']} ({items['size']} bytes)"


@tool
def search_code(query: str, file_extension: str = "") -> str:
    """Search for code patterns across the repository.

    Args:
        query: Search query (e.g., 'memory_limit', 'OOMKilled', 'resources.limits')
        file_extension: Optional file extension filter (e.g., 'yaml', 'py', 'go')

    Returns:
        Matching file paths and code snippets.
    """
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    q = f"{query} repo:{GITHUB_REPO}"
    if file_extension:
        q += f" extension:{file_extension}"

    response = httpx.get(
        "https://api.github.com/search/code",
        headers=headers,
        params={"q": q, "per_page": 10},
        timeout=10.0,
    )
    response.raise_for_status()

    results = response.json()
    if results["total_count"] == 0:
        return f"No results found for: {query}"

    output = []
    for item in results["items"][:10]:
        output.append(f"📄 {item['path']} (score: {item.get('score', 'N/A')})")
    return "\n".join(output)


@tool
def get_recent_commits(path: str = "", count: int = 10) -> str:
    """Get recent git commits, optionally filtered by path.

    Args:
        path: Optional file/directory path to filter commits
        count: Number of commits to retrieve

    Returns:
        Recent commits with SHA, message, author, and date.
    """
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    params = {"per_page": count}
    if path:
        params["path"] = path

    response = httpx.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/commits",
        headers=headers,
        params=params,
        timeout=10.0,
    )
    response.raise_for_status()

    commits = response.json()
    output = []
    for c in commits:
        sha = c["sha"][:7]
        msg = c["commit"]["message"].split("\n")[0]
        author = c["commit"]["author"]["name"]
        date = c["commit"]["author"]["date"][:10]
        output.append(f"{sha} {date} [{author}] {msg}")
    return "\n".join(output)
