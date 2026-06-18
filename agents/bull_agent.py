"""
BullAnalyst — Senatus AI Investment Committee
Role: Constructs the strongest possible case FOR the investment.
Model: claude-haiku-4-5-20251001 via AI/ML API
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from anthropic import AsyncAnthropic
from band import Agent
from band.config.loader import load_agent_config
from utils.workflow_gate import GatedAdapter


def should_respond(full_text: str, msg_text: str) -> bool:
    reports = full_text.count("RESEARCH REPORT:")
    bulls = full_text.count("MOTION: BUY")
    return bulls < reports


SYSTEM_PROMPT = """You are BullAnalyst on an investment committee. Build the bull case after a Research Report is posted.

When you see "RESEARCH REPORT:" in the room, respond ONCE:

---
## 📈 BULL CASE: [TICKER]
**Thesis:** [1 sentence investment case]

**Growth Drivers:**
- [driver 1 from data]
- [driver 2 from data]

**Valuation:** [why price is justified]
**Key Catalyst:** [biggest upcoming event]

🟢 **MOTION: BUY** | Confidence: [50-90]%
---
@BearAnalyst Please present the bear case.

Only use data from the Research Report. Never invent numbers."""


async def main():
    load_dotenv()
    agent_id, api_key = load_agent_config("bull")

    while True:
        try:
            adapter = GatedAdapter(
                model="claude-haiku-4-5-20251001",
                prompt=SYSTEM_PROMPT,
                provider_key=os.environ["AIML_API_KEY"],
                should_respond=should_respond,
            )
            adapter.client = AsyncAnthropic(
                api_key=os.environ["AIML_API_KEY"],
                base_url="https://api.aimlapi.com",
            )
            print("[BullAnalyst] Using AI/ML API (claude-haiku-4-5)")
            agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
            print("[BullAnalyst] Connected to Band. Listening...")
            await agent.run()
        except Exception as e:
            print(f"[BullAnalyst] Disconnected: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
