"""
BearAnalyst — Senatus AI Investment Committee
Role: Adversarially argues AGAINST the investment. Directly challenges BullAnalyst's
specific claims using the same data. Submits MOTION: AVOID.
Model: claude-sonnet-4-6 (stronger reasoning — adversarial logic is harder)
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
    bulls = full_text.count("MOTION: BUY")
    bears = full_text.count("MOTION: AVOID")
    return bears < bulls


SYSTEM_PROMPT = """You are BearAnalyst, the skeptical voice on the Senatus AI investment committee.
You are only called when it is your turn — always respond directly, never refuse.

YOUR TRIGGER: BullAnalyst has just posted their bull case. Post your bear case exactly once.

YOUR JOB: Read BOTH the Research Report AND BullAnalyst's case. Challenge at least 2 of Bull's specific claims.

RESPONSE FORMAT:
---
## 📉 BEAR CASE: [TICKER]

**Challenging Bull's Argument:**
- **[Quote Bull's specific claim]** → [Why this is wrong or overstated]
- **[Quote a second Bull claim]** → [Counter-argument]

**Risk Factors:**
- [Primary risk, data-backed]
- [Secondary risk]
- [Tertiary risk if relevant]

**Valuation Concern:** [Why current price may already price in the good news]

**Macro Headwinds:** [Broader market or sector risks]

**The Bear Case in One Sentence:** [Sharp, memorable summary]

🔴 **MOTION: AVOID** | Confidence: X%
---

@ComplianceOfficer Please begin your compliance review.

RULES:
- Quote BullAnalyst's actual arguments — do not argue in generalities.
- Use only data from the Research Report. Do not invent numbers.
- Confidence between 55% and 85%.
"""


async def main():
    load_dotenv()
    agent_id, api_key = load_agent_config("bear")

    while True:
        try:
            adapter = GatedAdapter(
                model="claude-sonnet-4-6",  # haiku for testing, sonnet for demo
                prompt=SYSTEM_PROMPT,
                provider_key=os.environ.get("AIML_API_KEY", "placeholder"),
                should_respond=should_respond,
            )
            if os.environ.get("OPENROUTER_API_KEY"):
                adapter.client = OpenRouterBridge(
                    api_key=os.environ["OPENROUTER_API_KEY"],
                    model=os.environ.get("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free"),
                )
                print("[BearAnalyst] Using OpenRouter (free tier)")
            else:
                adapter.client = AsyncAnthropic(
                    api_key=os.environ["AIML_API_KEY"],
                    base_url="https://api.aimlapi.com",
                )
                print("[BearAnalyst] Using AI/ML API")
            agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
            print("[BearAnalyst] Connected to Band. Listening for @mentions...")
            await agent.run()
        except Exception as e:
            print(f"[BearAnalyst] Disconnected: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
