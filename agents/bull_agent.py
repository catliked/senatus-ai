"""
BullAnalyst — Senatus AI Investment Committee
Role: Constructs the strongest possible case FOR the investment.
Model: gpt-4o via AI/ML API (mid-tier, coherent argument construction)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from band import Agent
from band.config.loader import load_agent_config
from utils.workflow_gate import GatedAdapter
from utils.openai_shim import OpenAIShimClient


def should_respond(full_text: str, msg_text: str) -> bool:
    # Pause if compliance interrupted mid-debate and no resume signal yet
    if "COMPLIANCE INTERRUPT:" in full_text:
        if not any(p in full_text for p in ["Resuming committee deliberation", "APPROVED", "OVERRIDE"]):
            return False
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

INTERRUPT HANDLING: If a human posts mid-debate, address them directly first, then state "Resuming committee deliberation." and continue your task if incomplete.
Only use data from the Research Report. Never invent numbers."""


async def main():
    load_dotenv()
    agent_id, api_key = load_agent_config("bull")

    while True:
        try:
            adapter = GatedAdapter(
                model="gpt-4o",
                prompt=SYSTEM_PROMPT,
                provider_key=os.environ["AIML_API_KEY"],
                should_respond=should_respond,
            )
            adapter.client = OpenAIShimClient(
                api_key=os.environ["AIML_API_KEY"],
                base_url="https://api.aimlapi.com/v1",
            )
            print("[BullAnalyst] Using AI/ML API (gpt-4o)")
            agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
            print("[BullAnalyst] Connected to Band. Listening...")
            await agent.run()
        except Exception as e:
            print(f"[BullAnalyst] Disconnected: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
