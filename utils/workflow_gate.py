"""
Deterministic workflow gating for Senatus AI agents.

Band calls on_message() for every message in the room, not just ones the agent
is @mentioned in. Previously each agent decided whether to respond by reading
its own prompt instructions ("if room contains X, output [NO ACTION]") — this
relies on the LLM correctly judging room state, which weak/free models do
unreliably (causing both silent non-responses and infinite consensus loops).

GatedAdapter moves that decision into plain Python: should_respond(full_text,
msg_text) is checked BEFORE the LLM is ever called. The LLM is only invoked
when it is deterministically that agent's turn, exactly once per turn.
"""
from band.adapters.anthropic import AnthropicAdapter


def history_to_text(history) -> str:
    parts = []
    for m in history:
        content = m.get("content") if isinstance(m, dict) else getattr(m, "content", None)
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
        elif isinstance(content, str):
            parts.append(content)
    return "\n".join(parts)


class GatedAdapter(AnthropicAdapter):
    """AnthropicAdapter that only calls the LLM when should_respond() returns True."""

    def __init__(self, *args, should_respond, **kwargs):
        super().__init__(*args, **kwargs)
        self._should_respond = should_respond

    async def on_message(
        self,
        msg,
        tools,
        history,
        participants_msg,
        contacts_msg,
        *,
        is_session_bootstrap,
        room_id,
    ):
        msg_text = msg.format_for_llm() if hasattr(msg, "format_for_llm") else str(msg)
        full_text = history_to_text(history) + "\n" + msg_text
        if not self._should_respond(full_text, msg_text):
            return
        await super().on_message(
            msg,
            tools,
            history,
            participants_msg,
            contacts_msg,
            is_session_bootstrap=is_session_bootstrap,
            room_id=room_id,
        )
