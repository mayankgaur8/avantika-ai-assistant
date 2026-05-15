import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/coach", tags=["coach"])

class ChatRequest(BaseModel):
    message: str
    target_language: str = "English"
    use_mock: bool = True

async def mock_stream_generator(message: str, target_language: str):
    """
    Simulates a streaming response communicating with our AI coaching agents.
    """
    response_words = f"Hello! I am your AI {target_language} Coach. You said: '{message}'. Let's practice!".split(" ")
    for word in response_words:
        yield f"data: {word} \n\n"
        await asyncio.sleep(0.1)
    
    # Send an evaluation tip event
    yield f"event: evaluation\ndata: {{\"tip\": \"Remember to use the correct tone.\", \"score\": 90}}\n\n"
    yield "data: [DONE]\n\n"

@router.post("/chat")
async def chat_with_coach(request: ChatRequest):
    """
    A streaming endpoint communicating with our AI coaching agents.
    """
    # In a real scenario, this would call the agent-service API using httpx or Server-Sent Events
    return StreamingResponse(
        mock_stream_generator(request.message, request.target_language),
        media_type="text/event-stream"
    )
