"""Thin LangChain-compatible wrapper around AnthropicBedrock client."""

import os
from typing import Any, Optional

import anthropic
from langchain_anthropic import ChatAnthropic
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class ChatBedrockAnthropic(ChatAnthropic):
    """ChatAnthropic subclass that uses AnthropicBedrock client for Bearer token auth."""

    aws_region: str = "us-east-1"
    bedrock_token: Optional[str] = None

    def __init__(self, **kwargs: Any):
        # Pull out our custom fields before passing to parent
        aws_region = kwargs.pop("aws_region", os.getenv("AWS_REGION", "us-east-1"))
        bedrock_token = kwargs.pop("bedrock_token", os.getenv("AWS_BEARER_TOKEN_BEDROCK", ""))

        # ChatAnthropic requires anthropic_api_key even if we override the client
        if "anthropic_api_key" not in kwargs:
            kwargs["anthropic_api_key"] = bedrock_token or "dummy"

        super().__init__(**kwargs)

        # Override the internal client with AnthropicBedrock
        self._client = anthropic.AnthropicBedrock(
            aws_region=aws_region,
            api_key=bedrock_token or None,
        )

    @property
    def _llm_type(self) -> str:
        return "bedrock-anthropic"
