import os

from langchain_aws import ChatBedrockConverse


def get_llm(temperature: float = 0.0, max_tokens: int = 4096):
    return ChatBedrockConverse(
        model=os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-20250514-v1:0"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        temperature=temperature,
        max_tokens=max_tokens,
    )


VICTORIAMETRICS_URL = os.getenv("VICTORIAMETRICS_URL", "http://localhost:8428")
VICTORIALOGS_URL = os.getenv("VICTORIALOGS_URL", "http://localhost:9428")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
ARGOCD_URL = os.getenv("ARGOCD_URL", "http://localhost:8080")
ARGOCD_TOKEN = os.getenv("ARGOCD_TOKEN", "")
