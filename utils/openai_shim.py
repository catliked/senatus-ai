"""
OpenAI-compatible shim for use with Band SDK's AnthropicAdapter.

AnthropicAdapter calls self.client.messages.create() and expects an Anthropic-format
response. This shim wraps the OpenAI SDK so non-Claude models (GPT-4o, DeepSeek-R1,
o4-mini) can be used without changing the adapter layer.

Usage:
    adapter.client = OpenAIShimClient(api_key=..., base_url="https://api.aimlapi.com/v1")
"""
import re
from openai import AsyncOpenAI


def _strip_think(text: str) -> str:
    """Remove <think>...</think> blocks produced by reasoning models (DeepSeek-R1, etc.)."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


class _ContentBlock:
    def __init__(self, text: str):
        self.text = text
        self.type = "text"


class _Usage:
    def __init__(self, input_tokens: int, output_tokens: int):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _AnthropicResponse:
    """Mimics anthropic.types.Message so AnthropicAdapter can read it normally."""
    def __init__(self, text: str, input_tokens: int, output_tokens: int):
        self.content = [_ContentBlock(text)]
        self.stop_reason = "end_turn"
        self.usage = _Usage(input_tokens, output_tokens)


class _MessagesResource:
    def __init__(self, oai: AsyncOpenAI):
        self._oai = oai

    async def create(
        self,
        *,
        model: str,
        messages: list,
        max_tokens: int = 1024,
        system: str | None = None,
        temperature: float | None = None,
        **kwargs,  # absorbs Anthropic-specific params (betas, anthropic_version, etc.)
    ) -> _AnthropicResponse:
        oai_messages = []
        if system:
            oai_messages.append({"role": "system", "content": system})

        for m in messages:
            content = m.get("content", "")
            if isinstance(content, list):
                # Flatten Anthropic content blocks to plain text
                content = " ".join(
                    b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            oai_messages.append({"role": m["role"], "content": content})

        call_kwargs: dict = {}
        if temperature is not None:
            call_kwargs["temperature"] = temperature

        resp = await self._oai.chat.completions.create(
            model=model,
            messages=oai_messages,
            max_tokens=max_tokens,
            **call_kwargs,
        )

        raw = resp.choices[0].message.content or ""
        text = _strip_think(raw)

        return _AnthropicResponse(
            text=text,
            input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            output_tokens=resp.usage.completion_tokens if resp.usage else 0,
        )


class OpenAIShimClient:
    """
    Drop-in replacement for AsyncAnthropic.
    Set adapter.client = OpenAIShimClient(...) for non-Claude models.
    """
    def __init__(self, api_key: str, base_url: str = "https://api.aimlapi.com/v1"):
        self.messages = _MessagesResource(
            AsyncOpenAI(api_key=api_key, base_url=base_url)
        )
