"""
BullAnalyst — Senatus AI Investment Committee
Role: Constructs the strongest possible case FOR the investment.
Reads the Research Report from the room, builds a bull thesis, submits MOTION: BUY.
Model: claude-haiku-4-5-20251001
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from anthropic import AsyncAnthropic
from band import Agent
from band.config.loader import load_agent_config
from utils.openrouter_bridge import OpenRouterBridge
from utils.workflow_gate import GatedAdapter


def should_respond(full_text: str, msg_text: str) -> bool:
    reports = full_text.count("RESEARCH REPORT:")
    bulls = full_text.count("MOTION: BUY")
    return bulls < reports


SYSTEM_PROMPT = """You are BullAnalyst, the optimistic voice on the Senatus AI investment committee.
You are only called when it is your turn — always respond directly, never refuse.

YOUR TRIGGER: A Research Report has just been posted. Post your bull case exactly once.

RESPONSE FORMAT:
---
## 📈 BULL CASE: [TICKER]

**Investment Thesis:** [1 sentence]

**Growth Drivers:**
- [data-backed growth driver]
- [second growth driver]
- [third if available]

**Valuation Argument:** [why current price is justified or undervalued]

**Key Catalyst:** [biggest upcoming catalyst]

**Risk I Concede:** [one legitimate bear concern]

**Supporting Data:**
- Revenue Growth: X% (from Research Report)
- [other supporting metric]

🟢 **MOTION: BUY** | Confidence: X%
---

@BearAnalyst Your turn. I've made the bull case above — challenge it.

RULES:
- Base ALL claims on data in the Research Report. Do not invent metrics.
- Confidence between 55% and 90%.
"""


async def main():
    load_dotenv()
    agent_id, api_key = load_agent_config("bull")

    while True:
        try:
            adapter = GatedAdapter(
                model="claude-haiku-4-5-20251001",
                prompt=SYSTEM_PROMPT,
                provider_key=os.environ.get("AIML_API_KEY", "placeholder"),
                should_respond=should_respond,
            )
            if os.environ.get("OPENROUTER_API_KEY"):
                adapter.client = OpenRouterBridge(
                    api_key=os.environ["OPENROUTER_API_KEY"],
                    model=os.environ.get("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free"),
                )
                print("[BullAnalyst] Using OpenRouter (free tier)")
            else:
                adapter.client = AsyncAnthropic(
                    api_key=os.environ["AIML_API_KEY"],
                    base_url="https://api.aimlapi.com",
                )
                print("[BullAnalyst] Using AI/ML API")
            agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
            print("[BullAnalyst] Connected to Band. Listening for @mentions...")
            await agent.run()
        except Exception as e:
            print(f"[BullAnalyst] Disconnected: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
