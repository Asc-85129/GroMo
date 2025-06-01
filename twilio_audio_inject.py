import os
from fastapi.responses import FileResponse
from fastapi import APIRouter
from pydantic import BaseModel
from twilio.twiml.voice_response import VoiceResponse

AUDIO_DIR = "public_audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

router = APIRouter()

class AudioPayload(BaseModel):
    filename: str

@router.post("/inject-audio")
def inject_audio(payload: AudioPayload):
    response = VoiceResponse()
    public_url = f"https://yourdomain.com/audio/{payload.filename}"
    response.play(public_url)
    return str(response)

@router.get("/audio/{filename}")
async def serve_audio(filename: str):
    file_path = os.path.join(AUDIO_DIR, filename)
    return FileResponse(file_path, media_type="audio/wav")
