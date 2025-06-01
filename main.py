import os
import json
import base64
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from app.transcriber import transcribe_user_audio_chunk

load_dotenv()

app = FastAPI()

NGROK_URL = os.getenv("NGROK_URL")  


@app.get("/")
def home():
    return HTMLResponse("Twilio transcription server running.")

@app.post("/twiml")
def twiml():
    twiml_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Disclaimer: This call may be recorded for quality and training purposes. Welcome to Gromo services. How can I help you today?</Say>
  <Start>
    <Stream url="wss://{NGROK_URL[8:]}/audio" />
  </Start>
  <Pause length="600"/>
</Response>
"""
    return HTMLResponse(content=twiml_xml, media_type="application/xml")


@app.websocket("/audio")
async def audio_stream(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection accepted")
    try:
        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)

            if data["event"] == "media":
                audio_b64 = data["media"]["payload"]
                audio_bytes = base64.b64decode(audio_b64)

                transcript = await transcribe_user_audio_chunk(audio_bytes)
                if transcript:
                    print(f"User said: {transcript}")
    except Exception as e:
        print("WebSocket error:", e)
    finally:
        print("WebSocket disconnected")
