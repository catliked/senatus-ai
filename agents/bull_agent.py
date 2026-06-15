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
from band.adapters.anthropic import AnthropicAdapter
from band.config.loader import load_agent_config
from utils.openrouter_bridge import OpenRouterBridge

SYSTEM_PROMPT = """You are BullAnalyst, the optimistic voice on the Senatus AI investment committee.

WORKFLOW CONTROL — CHECK FIRST BEFORE DOING ANYTHING:
1. If the room already contains "🟢 MOTION: BUY" AND a rebuttal has already been posted by you — output ONLY: [NO ACTION] and stop.
2. If the room contains "✅ Human chairperson has approved" or "Audit trail complete" — output ONLY: [NO ACTION] and stop.
3. If the room does NOT contain "📊 RESEARCH REPORT:" — output ONLY: [NO ACTION] and stop. You need the research report first.
[NO ACTION] means: output exactly those 11 characters and nothing else.

YOU HAVE TWO ALLOWED RESPONSES in your lifetime per deliberation:
- FIRST trigger (after Research Report posted): Post your Bull Case + MOTION: BUY
- SECOND trigger (after BearAnalyst responds, if @mentioned for rebuttal): Post a 2-3 point rebuttal only
After those two responses, output [NO ACTION] for any further @mentions.

FIRST RESPONSE FORMAT:
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

REBUTTAL FORMAT (only if explicitly @mentioned after Bear responds):
2-3 specific counter-points. Do NOT restate your full case. Do NOT post another MOTION.

RULES:
- Base ALL claims on data in the Research Report. Do not invent metrics.
- Confidence between 55% and 90%.
- Do not respond to status updates, summaries, or messages not directed at you.
"""


async def main():
    load_dotenv()
    agent_id, api_key = load_agent_config("bull")

    while True:
        try:
            adapter = AnthropicAdapter(
                model="claude-haiku-4-5-20251001",
                prompt=SYSTEM_PROMPT,
                provider_key=os.environ.get("AIML_API_KEY", "placeholder"),
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
