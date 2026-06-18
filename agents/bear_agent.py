"""
BearAnalyst — Senatus AI Investment Committee
Role: Adversarially challenges the bull thesis.
Model: claude-sonnet-4-6 via AI/ML API
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
    bulls = full_text.count("MOTION: BUY")
    bears = full_text.count("MOTION: AVOID")
    return bears < bulls


SYSTEM_PROMPT = """You are BearAnalyst on an investment committee. Challenge the bull thesis after BullAnalyst posts.

When you see "MOTION: BUY" in the room, respond ONCE:

---
## 📉 BEAR CASE: [TICKER]
**Counter:** [Challenge one of BullAnalyst's specific claims]

**Key Risks:**
- [risk 1 from data]
- [risk 2 from data]

**Valuation Concern:** [why price may be stretched]
**Bear Case:** [one sharp sentence]

🔴 **MOTION: AVOID** | Confidence: [50-85]%
---
@ComplianceOfficer Please conduct your compliance review.

Only use data from the Research Report. Never invent numbers."""


async def main():
    load_dotenv()
    agent_id, api_key = load_agent_config("bear")

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
            print("[BearAnalyst] Using AI/ML API (claude-haiku-4-5)")
            agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
            print("[BearAnalyst] Connected to Band. Listening...")
            await agent.run()
        except Exception as e:
            print(f"[BearAnalyst] Disconnected: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
