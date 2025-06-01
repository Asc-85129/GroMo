from elevenlabs import generate, save, set_api_key
import io
import websockets
import os
from dotenv import load_dotenv
load_dotenv()

ELEVENLABS_API_KEY = os.getenv()

set_api_key(ELEVENLABS_API_KEY)

def generate_tts_audio(text: str, voice: str = "Rachel") -> bytes:
    audio = generate(
        text=text,
        voice=voice,
        model="eleven_monolingual_v1"
    )
    audio_bytes = io.BytesIO()
    save(audio, audio_bytes)
    return audio_bytes.getvalue()
"""
import shutil

async def synthesize(text, lang):
    voice_id = os.getenv("EN_VOICE_ID") if lang == "en" else os.getenv("HI_VOICE_ID")
    headers = {
        "xi-api-key": os.getenv("ELEVENLABS_API_KEY"),
        "Content-Type": "application/json"
    }
    payload = {"text": text}
    res = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream",
        json=payload, headers=headers
    )

    temp_path = "tts_response.wav"
    final_path = f"public_audio/tts_response.wav"
    with open(temp_path, "wb") as f:
        f.write(res.content)
    shutil.move(temp_path, final_path)
    return "tts_response.wav"
"""