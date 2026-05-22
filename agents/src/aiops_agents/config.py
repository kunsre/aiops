import os

from aiops_agents.llm import ChatBedrockAnthropic

AGENT_MODELS = {
    "monitor": os.getenv("MODEL_MONITOR", "us.anthropic.claude-haiku-4-5-20251001-v1:0"),
    "generator": os.getenv("MODEL_GENERATOR", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"),
    "evaluator": os.getenv("MODEL_EVALUATOR", "us.anthropic.claude-haiku-4-5-20251001-v1:0"),
    "planner": os.getenv("MODEL_PLANNER", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"),
}


def get_llm(agent_name: str = "monitor", temperature: float = 0.0, max_tokens: int = 4096):
    """Get LLM instance for a specific agent.

    Uses AnthropicBedrock with Bearer token auth (AWS_BEARER_TOKEN_BEDROCK env var).
    Override model per agent via env: MODEL_MONITOR, MODEL_GENERATOR, etc.
    """
    model_id = AGENT_MODELS.get(agent_name, AGENT_MODELS["monitor"])

    return ChatBedrockAnthropic(
        model=model_id,
        temperature=temperature,
        max_tokens=max_tokens,
    )


VICTORIAMETRICS_URL = os.getenv("VICTORIAMETRICS_URL", "http://localhost:8428")
VICTORIALOGS_URL = os.getenv("VICTORIALOGS_URL", "http://localhost:9428")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "kunsre/aiops")
ARGOCD_URL = os.getenv("ARGOCD_URL", "http://localhost:8080")
ARGOCD_TOKEN = os.getenv("ARGOCD_TOKEN", "")
