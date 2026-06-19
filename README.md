# Senatus AI — Enterprise Investment Committee Platform

> **Band of Agents Hackathon 2026** — Multi-agent financial deliberation with mandatory human governance

Senatus AI is a 5-agent investment committee that debates any publicly traded stock in a [Band](https://app.band.ai) chat room and requires human chairperson approval before any investment decision is logged. Agents run in parallel persistent WebSocket sessions, coordinate via structured message markers, and are gated by deterministic Python logic — not LLM self-judgment — to prevent spurious responses.

---

## Architecture

```
Human → /analyze → FastAPI backend → Band room (REST trigger)
                                          │
                         ┌────────────────▼────────────────┐
                         │         Band Chat Room           │
                         │                                  │
                         │  ResearchAgent  (gpt-4o-mini)   │
                         │       ↓                          │
                         │  BullAnalyst    (gpt-4o)         │
                         │       ↓                          │
                         │  BearAnalyst    (deepseek-r1)    │
                         │       ↓                          │
                         │  ComplianceOfficer (claude-3-5-sonnet) │
                         │       ↓                          │
                         │  SynthesisChair (o4-mini)        │
                         └────────────────┬────────────────┘
                                          │
                              Human Approval Portal
                              (APPROVE / OVERRIDE / ASK / INTERRUPT)
```

### Agent Roles & Models

| Agent | Cognitive Task | Model | Why |
|---|---|---|---|
| ResearchAgent | High-volume data summarization | `gpt-4o-mini` | Fast-tier, cost-efficient for structured formatting |
| BullAnalyst | Coherent argument construction | `gpt-4o` | Mid-tier reasoning for persuasive investment thesis |
| BearAnalyst | Adversarial reasoning | `deepseek-r1` | Reasoning-tier for critical challenge and risk identification |
| ComplianceOfficer | Strict instruction-following | `claude-3-5-sonnet` | Precision-tier for regulatory screening and rule adherence |
| SynthesisChair | Final synthesis & verdict | `o4-mini` | Reasoning-tier for weighing competing arguments into a verdict |

---

## Human-in-the-Loop Design

Human oversight operates at **three levels**:

1. **Mid-debate interrupt** — Human can message any agent at any time via the Interrupt panel. The addressed agent responds directly, then resumes deliberation ("Resuming committee deliberation.").
2. **Compliance escalation** — ComplianceOfficer monitors the room continuously, not just at its scheduled turn. If it detects SEC/FDA/DOJ/fraud keywords, it posts a `COMPLIANCE INTERRUPT:` and pauses deliberation until the human responds.
3. **Final fiduciary gate** — SynthesisChair's verdict is explicitly marked `AWAITING HUMAN CHAIRPERSON APPROVAL`. The human must APPROVE or OVERRIDE before the decision is logged to the audit trail.

---

## Workflow Gating

Agents share a single Band room. Every message is delivered to every agent. Deterministic Python gating (`GatedAdapter` in `utils/workflow_gate.py`) decides whether an agent's turn has arrived — the LLM is never called unless the gate passes:

- **ResearchAgent**: fires when `"=== RAW MARKET DATA:"` appears in the trigger and no research report exists yet
- **BullAnalyst**: fires when `RESEARCH REPORT:` count > `MOTION: BUY` count  
- **BearAnalyst**: fires when `MOTION: BUY` count > `MOTION: AVOID` count (pauses on compliance interrupt)
- **ComplianceOfficer**: fires at scheduled turn (after Bear) OR on red-flag keyword detection mid-debate
- **SynthesisChair**: fires after compliance clears, or immediately on `APPROVED`/`OVERRIDE`

Bootstrap replay on WebSocket reconnect is explicitly skipped (`is_session_bootstrap → return`) to prevent re-firing on historical messages.

---

## Setup

### Prerequisites
- Python 3.11+
- [Band account](https://app.band.ai) — create 5 External Agents and 1 room
- AI/ML API key from [aimlapi.com](https://aimlapi.com)

### Install
```bash
pip install -r requirements.txt
# or with uv:
uv sync
```

### Configure `.env`
```env
BAND_API_KEY=band_u_...          # Your personal Band key (human user)
AIML_API_KEY=your_key_here       # AI/ML API key
BAND_ROOM_ID=your-room-uuid      # Band room UUID
DEMO_MODE=false                  # Set true for scripted simulation (no API calls)
```

### Configure `agent_config.yaml`
```yaml
research:
  agent_id: <uuid>
  api_key: band_a_...
bull:
  agent_id: <uuid>
  api_key: band_a_...
bear:
  agent_id: <uuid>
  api_key: band_a_...
compliance:
  agent_id: <uuid>
  api_key: band_a_...
synthesis:
  agent_id: <uuid>
  api_key: band_a_...
```

### Run
```bash
# Terminal 1 — FastAPI backend + frontend
uvicorn main:app --reload --port 8000

# Terminals 2–6 — one per agent
python agents/research_agent.py
python agents/bull_agent.py
python agents/bear_agent.py
python agents/compliance_agent.py
python agents/synthesis_agent.py

# Open http://localhost:8000
```

---

## Demo Mode

Set `DEMO_MODE=true` in `.env`. The backend returns a `demo_mode` flag; the frontend runs a 25-second scripted simulation entirely client-side. No Band WebSocket or AI/ML API calls are made. Ideal for UI testing and demo recording without spending credits.

---

## Project Structure

```
├── main.py                    # FastAPI backend (analyze, approve, intervene, ask, health)
├── agents/
│   ├── research_agent.py
│   ├── bull_agent.py
│   ├── bear_agent.py
│   ├── compliance_agent.py
│   └── synthesis_agent.py
├── utils/
│   ├── workflow_gate.py       # GatedAdapter — deterministic LLM gating + bootstrap skip
│   ├── openai_shim.py         # AnthropicAdapter shim for non-Claude models via AI/ML API
│   ├── band_client.py         # Band REST client (send/receive room messages)
│   └── market_data.py         # yfinance data fetcher + formatter
├── frontend/
│   └── index.html             # Single-page dashboard (vanilla JS, Chart.js)
├── agent_config.yaml          # Band agent UUIDs and keys (gitignored)
└── .env                       # Secrets (gitignored)
```

---

## Key Design Decisions

- **No orchestrator agent** — Workflow sequencing is enforced by Python marker counts, not by an LLM routing agent. This eliminates a whole class of hallucination-based routing failures.
- **Model diversity by cognitive load** — Cheap fast model for data formatting, reasoning models for adversarial and synthesis tasks, precision model for compliance.
- **Persistent WebSocket agents** — Each agent runs a permanent connection to Band, not a stateless function call. This enables true mid-debate interrupts and async human interjections.
- **Audit trail** — Every agent action and human decision is timestamped in the frontend and exportable as a printable HTML/PDF report.

---

Built with [Band SDK](https://app.band.ai) · [AI/ML API](https://aimlapi.com) · FastAPI · yfinance
