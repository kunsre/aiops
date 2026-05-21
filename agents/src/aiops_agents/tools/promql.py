import httpx
from langchain_core.tools import tool

from aiops_agents.config import VICTORIAMETRICS_URL


@tool
def query_promql(query: str, time_range: str = "5m") -> str:
    """Query VictoriaMetrics with PromQL to retrieve resource metrics.

    Args:
        query: PromQL expression (e.g., 'container_memory_usage_bytes{name=~".*data-worker.*"}')
        time_range: Time range for range query (e.g., '5m', '1h')

    Returns:
        JSON string of query results with timestamps and values.
    """
    response = httpx.get(
        f"{VICTORIAMETRICS_URL}/api/v1/query",
        params={"query": query, "time": "now"},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.text


@tool
def query_promql_range(query: str, start: str = "now-5m", end: str = "now", step: str = "15s") -> str:
    """Query VictoriaMetrics with PromQL range query for time series data.

    Args:
        query: PromQL expression
        start: Start time (e.g., 'now-5m', ISO timestamp)
        end: End time (e.g., 'now', ISO timestamp)
        step: Query resolution step (e.g., '15s', '1m')

    Returns:
        JSON string of time series results.
    """
    response = httpx.get(
        f"{VICTORIAMETRICS_URL}/api/v1/query_range",
        params={"query": query, "start": start, "end": end, "step": step},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.text
