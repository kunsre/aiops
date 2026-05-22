import os

from langchain_aws import ChatBedrockConverse

# 에이전트별 모델 분리: 환경변수로 개별 지정 가능
# 나중에 Haiku/Llama 등 저비용 모델로 교체하거나,
# 파인튜닝 커스텀 모델 ARN을 넣으면 해당 에이전트만 전환됨
AGENT_MODELS = {
    "monitor": os.getenv("MODEL_MONITOR", "us.anthropic.claude-haiku-4-5-20251001-v1:0"),
    "generator": os.getenv("MODEL_GENERATOR", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"),
    "evaluator": os.getenv("MODEL_EVALUATOR", "us.anthropic.claude-haiku-4-5-20251001-v1:0"),
    "planner": os.getenv("MODEL_PLANNER", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"),
}


def get_llm(agent_name: str = "monitor", temperature: float = 0.0, max_tokens: int = 4096):
    """Get LLM instance for a specific agent.

    Each agent can use a different model by setting environment variables:
      MODEL_MONITOR=anthropic.claude-3-haiku-20240307-v1:0
      MODEL_GENERATOR=anthropic.claude-sonnet-4-20250514-v1:0
      MODEL_EVALUATOR=meta.llama3-8b-instruct-v1:0
      MODEL_PLANNER=arn:aws:bedrock:us-east-1:123456:custom-model/my-finetuned-sre

    Args:
        agent_name: Which agent is requesting the LLM (monitor/generator/evaluator/planner)
        temperature: Sampling temperature
        max_tokens: Max output tokens
    """
    model_id = AGENT_MODELS.get(agent_name, AGENT_MODELS["monitor"])

    return ChatBedrockConverse(
        model=model_id,
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
