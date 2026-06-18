"""
Senatus AI — FastAPI Backend
Receives ticker + thesis from the frontend, fetches market data,
and fires the first message into the Band room to trigger the agent debate.
Demo mode: when AIML_API_KEY is empty or DEMO_MODE=true, returns demo_mode flag
so the frontend runs a local simulation instead of polling the Band room.
"""
import os
import yaml
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from utils.market_data import get_stock_data, format_stock_summary
from utils.band_client import send_message_to_room, send_human_message, get_room_messages

load_dotenv()

app = FastAPI(title="Senatus AI")

# Serve frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


def _is_demo_mode() -> bool:
    """Demo mode when AIML_API_KEY is missing/empty or DEMO_MODE=true."""
    if os.getenv("DEMO_MODE", "false").lower() == "true":
        return True
    return not bool(os.getenv("AIML_API_KEY", "").strip())


def _load_trigger_config() -> tuple[str, str, str]:
    env_sender = os.getenv("SYNTHESIS_AGENT_API_KEY", "")
    env_mention_id = os.getenv("RESEARCH_AGENT_ID", "")
    if env_sender and env_mention_id:
        return env_sender, env_mention_id, "ResearchAgent"
    try:
        with open("agent_config.yaml", "r") as f:
            config = yaml.safe_load(f)
        sender_key = config["synthesis"]["api_key"]
        mention_id = config["research"]["agent_id"]
        return sender_key, mention_id, "ResearchAgent"
    except FileNotFoundError:
        raise RuntimeError("Set SYNTHESIS_AGENT_API_KEY + RESEARCH_AGENT_ID env vars or provide agent_config.yaml")


def _load_synthesis_agent_id() -> str:
    env_id = os.getenv("SYNTHESIS_AGENT_ID", "")
    if env_id:
        return env_id
    with open("agent_config.yaml", "r") as f:
        config = yaml.safe_load(f)
    return config["synthesis"]["agent_id"]


class AnalysisRequest(BaseModel):
    ticker: str
    thesis: str


class AnalysisResponse(BaseModel):
    status: str
    ticker: str
    room_id: str
    band_room_url: str
    message: str
    committee_id: str
    demo_mode: bool = False


class ApprovalRequest(BaseModel):
    decision: str  # "APPROVED" or "OVERRIDE"
    verdict: str   # BUY / HOLD / AVOID


class AskRequest(BaseModel):
    question: str


class InterveneRequest(BaseModel):
    message: str
    mention_agent: str = "synthesis"  # research | bull | bear | compliance | synthesis


AGENT_DISPLAY_NAMES = {
    "research": "ResearchAgent",
    "bull": "BullAnalyst",
    "bear": "BearAnalyst",
    "compliance": "ComplianceOfficer",
    "synthesis": "SynthesisChair",
}


def _load_agent_id(agent_name: str) -> str:
    """Return the Band agent UUID for the given agent key."""
    agent_name = agent_name.lower()
    if agent_name not in AGENT_DISPLAY_NAMES:
        raise ValueError(f"Unknown agent '{agent_name}'. Must be one of: {list(AGENT_DISPLAY_NAMES)}")
    with open("agent_config.yaml", "r") as f:
        config = yaml.safe_load(f)
    return config[agent_name]["agent_id"]


@app.get("/")
async def root():
    return FileResponse("frontend/index.html")


@app.get("/health")
async def health():
    demo = _is_demo_mode()
    return {
        "status": "ok",
        "service": "Senatus AI",
        "demo_mode": demo,
        "ai_configured": not demo,
    }


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(req: AnalysisRequest):
    ticker = req.ticker.upper().strip()
    thesis = req.thesis.strip()

    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")
    if not thesis:
        raise HTTPException(status_code=400, detail="Investment thesis is required")

    committee_id = f"SAI-{datetime.now().strftime('%Y%m%d')}-{ticker}-{datetime.now().strftime('%H%M%S')}"
    demo = _is_demo_mode()

    if demo:
        return AnalysisResponse(
            status="demo",
            ticker=ticker,
            room_id="demo",
            band_room_url="#",
            message=f"Demo mode active. Configure AIML_API_KEY in .env for live AI deliberation.",
            committee_id=committee_id,
            demo_mode=True,
        )

    room_id = os.getenv("BAND_ROOM_ID", "")
    if not room_id or "PASTE" in room_id:
        raise HTTPException(
            status_code=503,
            detail="BAND_ROOM_ID not configured in .env.",
        )

    stock_data = get_stock_data(ticker)
    data_summary = format_stock_summary(stock_data)

    trigger_message = (
        f"New analysis request from the investment committee.\n\n"
        f"**Committee ID:** {committee_id}\n"
        f"**Ticker:** {ticker}\n"
        f"**Thesis:** {thesis}\n\n"
        f"{data_summary}\n\n"
        f"Please format this into the official Research Report and begin the committee deliberation."
    )

    try:
        sender_key, research_id, _ = _load_trigger_config()
        send_message_to_room(
            room_id=room_id,
            text=trigger_message,
            sender_api_key=sender_key,
            mention_agent_id=research_id,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=502, detail=f"Failed to send message to Band room: {e}")

    return AnalysisResponse(
        status="started",
        ticker=ticker,
        room_id=room_id,
        band_room_url=f"https://app.band.ai/chat/{room_id}",
        message=f"Committee deliberation initiated for {ticker}.",
        committee_id=committee_id,
        demo_mode=False,
    )


@app.get("/room-status")
async def room_status():
    room_id = os.getenv("BAND_ROOM_ID", "")
    if not room_id:
        raise HTTPException(status_code=503, detail="BAND_ROOM_ID not configured")
    try:
        sender_key, _, _ = _load_trigger_config()
        messages = get_room_messages(room_id, sender_key)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=502, detail=f"Failed to fetch room messages: {e}")
    return {"messages": messages}


@app.post("/approve")
async def approve(req: ApprovalRequest):
    if _is_demo_mode():
        return {"status": "demo"}
    room_id = os.getenv("BAND_ROOM_ID", "")
    human_key = os.getenv("BAND_API_KEY", "")
    if not room_id or not human_key:
        raise HTTPException(status_code=503, detail="BAND_ROOM_ID or BAND_API_KEY not configured")
    try:
        synthesis_id = _load_synthesis_agent_id()
        text = f"@SynthesisChair {req.decision} — {req.verdict}"
        send_human_message(room_id=room_id, text=text, human_api_key=human_key, mention_agent_id=synthesis_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to post approval: {e}")
    return {"status": "sent"}


@app.post("/intervene")
async def intervene(req: InterveneRequest):
    """Human sends a message mid-debate to any agent, bypassing the fixed sequence."""
    if _is_demo_mode():
        return {"status": "demo"}
    room_id = os.getenv("BAND_ROOM_ID", "")
    human_key = os.getenv("BAND_API_KEY", "")
    if not room_id or not human_key:
        raise HTTPException(status_code=503, detail="BAND_ROOM_ID or BAND_API_KEY not configured")
    try:
        agent_id = _load_agent_id(req.mention_agent)
        display_name = AGENT_DISPLAY_NAMES[req.mention_agent.lower()]
        text = f"@{display_name} [HUMAN INTERRUPT] {req.message}"
        send_human_message(room_id=room_id, text=text, human_api_key=human_key, mention_agent_id=agent_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to post intervention: {e}")
    return {"status": "sent"}


@app.post("/ask")
async def ask(req: AskRequest):
    if _is_demo_mode():
        return {"status": "demo"}
    room_id = os.getenv("BAND_ROOM_ID", "")
    human_key = os.getenv("BAND_API_KEY", "")
    if not room_id or not human_key:
        raise HTTPException(status_code=503, detail="BAND_ROOM_ID or BAND_API_KEY not configured")
    try:
        synthesis_id = _load_synthesis_agent_id()
        text = f"@SynthesisChair QUESTION — {req.question}"
        send_human_message(room_id=room_id, text=text, human_api_key=human_key, mention_agent_id=synthesis_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to post question: {e}")
    return {"status": "sent"}
