import os

import boto3
from botocore.config import Config
from langchain_aws import ChatBedrockConverse

AGENT_MODELS = {
    "monitor": os.getenv("MODEL_MONITOR", "us.anthropic.claude-haiku-4-5-20251001-v1:0"),
    "generator": os.getenv("MODEL_GENERATOR", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"),
    "evaluator": os.getenv("MODEL_EVALUATOR", "us.anthropic.claude-haiku-4-5-20251001-v1:0"),
    "planner": os.getenv("MODEL_PLANNER", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"),
}


def _create_bedrock_client():
    """Create Bedrock runtime client.

    Supports two auth modes:
    1. Bearer token (AWS_BEARER_TOKEN_BEDROCK env var) - for proxy/custom auth setups
    2. Standard AWS credentials (default boto3 chain) - IAM user, role, SSO, etc.
    """
    region = os.getenv("AWS_REGION", "us-east-1")
    token = os.getenv("AWS_BEARER_TOKEN_BEDROCK")

    config_kwargs = {
        "retries": {"max_attempts": 3, "mode": "standard"},
        "connect_timeout": 10,
        "read_timeout": 120,
    }

    if token:
        config_kwargs["additional_headers"] = {"Authorization": f"Bearer {token}"}

    bedrock_config = Config(**config_kwargs)

    return boto3.client(
        service_name="bedrock-runtime",
        region_name=region,
        config=bedrock_config,
    )


def get_llm(agent_name: str = "monitor", temperature: float = 0.0, max_tokens: int = 4096):
    """Get LLM instance for a specific agent.

    Override model per agent via env: MODEL_MONITOR, MODEL_GENERATOR, etc.
    """
    model_id = AGENT_MODELS.get(agent_name, AGENT_MODELS["monitor"])
    client = _create_bedrock_client()

    return ChatBedrockConverse(
        client=client,
        model_id=model_id,
        temperature=temperature,
        max_tokens=max_tokens,
    )


VICTORIAMETRICS_URL = os.getenv("VICTORIAMETRICS_URL", "http://localhost:8428")
VICTORIALOGS_URL = os.getenv("VICTORIALOGS_URL", "http://localhost:9428")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
ARGOCD_URL = os.getenv("ARGOCD_URL", "http://localhost:8080")
ARGOCD_TOKEN = os.getenv("ARGOCD_TOKEN", "")
