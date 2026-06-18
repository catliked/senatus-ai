"""
OpenRouter → Anthropic SDK bridge for Band SDK compatibility.

The Band SDK's AnthropicAdapter calls:
    self.client.messages.create(model, max_tokens, system, messages, tools)
and expects an anthropic.types.Message back.

This bridge intercepts that call, converts to OpenAI format, hits OpenRouter's
free-tier API, and wraps the response back into Anthropic format.

Usage:
    from utils.openrouter_bridge import OpenRouterBridge
    adapter.client = OpenRouterBridge(api_key=OPENROUTER_KEY, model="mistralai/mistral-7b-instruct:free")
    # To change model: set OPENROUTER_MODEL in .env
"""

import asyncio
import logging
import re

from openai import AsyncOpenAI
from anthropic.types import Message, TextBlock, Usage

logger = logging.getLogger(__name__)


class _MessagesNamespace:
    def __init__(self, parent: "OpenRouterBridge"):
        self._parent = parent

    async def create(self, model, max_tokens, system, messages, tools=None, **kwargs):
        return await self._parent._create(max_tokens, system, messages)


class OpenRouterBridge:
    """Drop-in replacement for AsyncAnthropic that routes through OpenRouter."""

    def __init__(self, api_key: str, model: str):
        self._model = model
        self._openai = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://senatus.ai",
                "X-Title": "Senatus AI Investment Committee",
            },
        )
        self.messages = _MessagesNamespace(self)

    def _to_openai_messages(self, system: str, messages: list) -> list:
        result = [{"role": "system", "content": system}]
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_result":
                            parts.append(f"[Tool result: {block.get('content', '')}]")
                    elif hasattr(block, "text"):
                        parts.append(block.text)
                content = " ".join(parts) if parts else "[empty]"
            result.append({"role": role, "content": str(content)})
        return result

    async def _create(self, max_tokens: int, system: str, messages: list) -> Message:
        openai_messages = self._to_openai_messages(system, messages)
        # Free tier hard-caps at 4096 completion tokens. Reasoning models burn most of
        # that on internal chain-of-thought, leaving nothing for content. Cap at 2048
        # to stay well within limits; our prompts are short enough to fit.
        capped_tokens = min(max_tokens, 2048)
        text = ""
        last_error = None

        for attempt in range(3):
            response = await self._openai.chat.completions.create(
                model=self._model,
                max_tokens=capped_tokens,
                messages=openai_messages,
            )
            if response.choices:
                text = response.choices[0].message.content or ""
                if text.strip():
                    break
            logger.warning(
                "OpenRouter returned no usable content (attempt %d/3): %s",
                attempt + 1,
                response.model_dump_json() if hasattr(response, "model_dump_json") else response,
            )
            last_error = response
            await asyncio.sleep(1.5 * (attempt + 1))

        if not text.strip():
            raise RuntimeError(
                f"OpenRouter model '{self._model}' returned no usable content after 3 attempts. "
                f"Last raw response: {last_error}"
            )

        # Reasoning models wrap their chain-of-thought in <think>...</think>.
        # Strip it so only the final answer reaches the Band room.
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        if not text:
            raise RuntimeError(f"OpenRouter model '{self._model}' returned only reasoning, no answer.")

        return Message(
            id=response.id,
            type="message",
            role="assistant",
            content=[TextBlock(type="text", text=text)],
            model=self._model,
            stop_reason="end_turn",
            stop_sequence=None,
            usage=Usage(
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
            ),
        )
