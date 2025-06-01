from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from twilio.twiml.voice_response import VoiceResponse, Start
from typing import Dict
import base64
import os

from transcription import Transcriber
from agno_workflow import GPSuggestions
from tts.elevenlabs_tts import generate_tts_audio
from injection.twilio_audio_inject import stream_audio_back
from frontend_ui.pitch_display import retrieve_cached_pitch

# Initialize FastAPI
app = FastAPI(title="AI Sales Call Assistant")
router = APIRouter()

# Mount public audio directory for Twilio
app.mount("/audio", StaticFiles(directory="public_audio"), name="audio")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active transcribers
active_transcribers: Dict[str, 'Transcriber'] = {}

# --- Voice Webhook for Twilio Call ---
@router.post("/twilio/voice")
async def twilio_voice_webhook(request: Request):
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")

    response = VoiceResponse()
    start = Start()
    stream_url = f"wss://1c04-49-36-81-71.ngrok-free.app/ws/audio-stream/{call_sid}"
    start.stream(url=stream_url, track="inbound_track,outbound_track")
    response.append(start)

    response.say(
        "Disclaimer: This call may be recorded for quality and training purposes. "
        "Welcome to Gromo services. How can I help you today?",
        voice="Polly.Joanna",
    )

    return Response(content=str(response), media_type="application/xml")


# --- WebSocket Audio Stream Handler ---
@router.websocket("/ws/audio-stream/{call_sid}")
async def audio_stream_ws(websocket: WebSocket, call_sid: str):
    await websocket.accept()
    print(f"WebSocket connected for call {call_sid}")
    transcriber = Transcriber(call_sid)
    await transcriber.connect()
    active_transcribers[call_sid] = transcriber

    try:
        while True:
            data = await websocket.receive_json()
            event = data.get("event")

            if event == "start":
                print(f"Streaming started for call {call_sid}")
            elif event == "media":
                audio_b64 = data["media"].get("payload")
                if audio_b64:
                    audio_bytes = base64.b64decode(audio_b64)
                    await transcriber.send_audio(audio_bytes)
            elif event == "stop":
                print(f"Streaming stopped for call {call_sid}")
                break
    except Exception as e:
        print(f"WebSocket error for call {call_sid}: {e}")
    finally:
        await transcriber.close()
        await websocket.close()
        active_transcribers.pop(call_sid, None)
        print(f"WebSocket closed for call {call_sid}")


# --- Generate GPT Pitch ---
class GPTInput(BaseModel):
    text: str
    user_id: str

@router.post("/agno/generate-pitch")
async def run_workflow(data: GPTInput):
    pitch = GPSuggestions().run(data.text, user_id=data.user_id)
    return {"pitch": pitch}


# --- TTS Generation ---
class TextInput(BaseModel):
    text: str

@router.post("/tts/synthesize")
async def synthesize_audio(data: TextInput):
    audio = generate_tts_audio(data.text)
    return Response(content=audio, media_type="audio/mpeg")


# --- Audio Injection ---
class InjectRequest(BaseModel):
    audio_text: str
    call_sid: str

@router.post("/inject/play")
async def inject_audio(data: InjectRequest):
    audio = generate_tts_audio(data.audio_text)
    stream_audio_back(data.call_sid, audio)
    return {"status": "Injected", "call_sid": data.call_sid}


# --- WebSocket Audio Injector (optional, currently only logs) ---
@router.websocket("/ws/inject-audio/{call_sid}")
async def inject_audio_ws(websocket: WebSocket, call_sid: str):
    await websocket.accept()
    try:
        while True:
            audio_data = await websocket.receive_bytes()
            print(f"Received {len(audio_data)} bytes for call {call_sid}")
    except WebSocketDisconnect:
        print(f"WebSocket injection closed for call {call_sid}")


# --- Retrieve Pitch for Screen UI ---
@router.get("/pitch-screen/{call_id}")
async def get_pitch_screen(call_id: str):
    pitch = retrieve_cached_pitch(call_id)
    return {"call_id": call_id, "pitch": pitch}


# Register router
app.include_router(router)
