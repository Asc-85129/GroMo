import aiohttp
import asyncio
import base64
import json
import websockets
import os
from dotenv import load_dotenv
load_dotenv()

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

class Transcriber:
    def __init__(self, call_sid: str):
        self.call_sid = call_sid
        self.session = None
        self.ws = None
        self.transcript = ""

    async def connect(self):
        headers = {
            "Authorization": ASSEMBLYAI_API_KEY,
        }
        self.session = aiohttp.ClientSession()
        self.ws = await self.session.ws_connect("wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000", headers=headers)
        asyncio.create_task(self.receive_transcript())

    async def send_audio(self, audio_bytes: bytes):
        if self.ws:
            await self.ws.send_bytes(audio_bytes)

    async def receive_transcript(self):
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data.get("text"):
                    print(f"Transcript ({self.call_sid}):", data["text"])
                    self.transcript += data["text"] + " "

    async def close(self):
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()

