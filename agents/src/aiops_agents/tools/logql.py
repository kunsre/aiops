import httpx
from langchain_core.tools import tool

from aiops_agents.config import VICTORIALOGS_URL


@tool
def query_logql(query: str, limit: int = 100, time_range: str = "5m") -> str:
    """Query VictoriaLogs for application log entries.

    Args:
        query: LogQL/VictoriaLogs query filter (e.g., 'service:data-worker AND error')
        limit: Maximum number of log entries to return
        time_range: How far back to search (e.g., '5m', '1h')

    Returns:
        JSON string of matching log entries with timestamps.
    """
    response = httpx.get(
        f"{VICTORIALOGS_URL}/select/logsql/query",
        params={"query": query, "limit": str(limit), "start": f"now-{time_range}"},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.text
