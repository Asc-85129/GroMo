import streamlit as st
import requests
import asyncio
import websockets
import json
import base64
import threading
import time
from typing import Dict, Any
import uuid
import pyaudio
import wave
import io
from datetime import datetime
import streamlit.components.v1 as components

# Configuration
FASTAPI_BASE_URL = "http://localhost:8000"
WS_BASE_URL = "ws://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="AI Sales Call Assistant",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Custom CSS for better UI
st.markdown(
    """
     
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .status-active {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .status-inactive {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .pitch-box {
        background-color: #e7f3ff;
        border: 1px solid #b3d9ff;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "call_active" not in st.session_state:
    st.session_state.call_active = False
if "call_sid" not in st.session_state:
    st.session_state.call_sid = None
if "transcription_log" not in st.session_state:
    st.session_state.transcription_log = []
if "pitch_history" not in st.session_state:
    st.session_state.pitch_history = []
if "ws_connection" not in st.session_state:
    st.session_state.ws_connection = None


class AudioStreamHandler:
    def __init__(self, call_sid: str):
        self.call_sid = call_sid
        self.ws_url = f"{WS_BASE_URL}/ws/audio-stream/{call_sid}"
        self.connection = None
        self.running = False

    async def connect(self):
        try:
            self.connection = await websockets.connect(self.ws_url)
            self.running = True
            return True
        except Exception as e:
            st.error(f"Failed to connect to WebSocket: {e}")
            return False

    async def send_audio(self, audio_data: bytes):
        if self.connection and self.running:
            try:
                audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                message = {"event": "media", "media": {"payload": audio_b64}}
                await self.connection.send(json.dumps(message))
            except Exception as e:
                st.error(f"Error sending audio: {e}")

    async def close(self):
        if self.connection:
            self.running = False
            await self.connection.close()


def make_api_request(endpoint: str, method: str = "GET", data: Dict[str, Any] = None):
    """Make API request to FastAPI backend"""
    url = f"{FASTAPI_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def generate_pitch(text: str, user_id: str):
    """Generate pitch using the AGno workflow"""
    data = {"text": text, "user_id": user_id}
    return make_api_request("/agno/generate-pitch", "POST", data)


def synthesize_tts(text: str):
    """Synthesize text to speech"""
    data = {"text": text}
    try:
        url = f"{FASTAPI_BASE_URL}/tts/synthesize"
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return response.content
        else:
            st.error(f"TTS Error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"TTS failed: {e}")
        return None


def inject_audio(audio_text: str, call_sid: str):
    """Inject audio into active call"""
    data = {"audio_text": audio_text, "call_sid": call_sid}
    return make_api_request("/inject/play", "POST", data)


def get_pitch_screen(call_id: str):
    """Retrieve cached pitch for call"""
    return make_api_request(f"/pitch-screen/{call_id}")


# Main UI
st.markdown(
    '<h1 class="main-header">📞 AI Sales Call Assistant</h1>', unsafe_allow_html=True
)

# Sidebar for configuration
with st.sidebar:
    st.header("🔧 Configuration")

    # API Base URL configuration
    api_url = st.text_input("FastAPI Base URL", value=FASTAPI_BASE_URL)
    if api_url != FASTAPI_BASE_URL:
        FASTAPI_BASE_URL = api_url

    # User ID for pitch generation
    user_id = st.text_input("User ID", value="default_user")

    st.markdown("---")

    # Call Status
    st.header("📊 Call Status")
    if st.session_state.call_active:
        st.markdown(
            '<div class="status-box status-active">🟢 Call Active</div>',
            unsafe_allow_html=True,
        )
        st.write(f"**Call SID:** {st.session_state.call_sid}")
    else:
        st.markdown(
            '<div class="status-box status-inactive">🔴 No Active Call</div>',
            unsafe_allow_html=True,
        )

# Main content area with tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "🎯 Pitch Generation",
        "🎤 Audio Controls",
        "📝 Transcription",
        "💉 Audio Injection",
        "📋 Call Management",
    ]
)

with tab1:
    st.header("🎯 AI Pitch Generation")

    col1, col2 = st.columns([2, 1])

    with col1:
        pitch_input = st.text_area(
            "Enter conversation context or customer query:",
            height=150,
            placeholder="e.g., Customer is asking about pricing for our premium package...",
        )

        if st.button("🚀 Generate Pitch", type="primary"):
            if pitch_input.strip():
                with st.spinner("Generating AI-powered pitch..."):
                    result = generate_pitch(pitch_input, user_id)
                    if result:
                        pitch_text = result.get("pitch", "No pitch generated")
                        st.session_state.pitch_history.append(
                            {
                                "timestamp": datetime.now().strftime("%H:%M:%S"),
                                "input": pitch_input,
                                "pitch": pitch_text,
                            }
                        )
                        st.success("Pitch generated successfully!")
            else:
                st.warning("Please enter some context or query first.")

    with col2:
        st.subheader("Quick Actions")
        if st.session_state.pitch_history:
            latest_pitch = st.session_state.pitch_history[-1]["pitch"]

            if st.button("🔊 Convert to Audio"):
                with st.spinner("Converting to speech..."):
                    audio_data = synthesize_tts(latest_pitch)
                    if audio_data:
                        st.audio(audio_data, format="audio/mpeg")

            if st.session_state.call_active and st.button("📤 Inject to Call"):
                with st.spinner("Injecting audio to call..."):
                    result = inject_audio(latest_pitch, st.session_state.call_sid)
                    if result:
                        st.success("Audio injected successfully!")

    # Display pitch history
    if st.session_state.pitch_history:
        st.subheader("📚 Pitch History")
        for i, entry in enumerate(
            reversed(st.session_state.pitch_history[-5:])
        ):  # Show last 5
            with st.expander(
                f"Pitch {len(st.session_state.pitch_history)-i} - {entry['timestamp']}"
            ):
                st.write("**Input:**", entry["input"])
                st.markdown(
                    f'<div class="pitch-box"><strong>Generated Pitch:</strong><br>{entry["pitch"]}</div>',
                    unsafe_allow_html=True,
                )

with tab2:
    st.header("🎤 Audio Controls")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Text-to-Speech")
        tts_text = st.text_area("Enter text to synthesize:", height=100)

        if st.button("🎵 Generate Audio"):
            if tts_text.strip():
                with st.spinner("Synthesizing audio..."):
                    audio_data = synthesize_tts(tts_text)
                    if audio_data:
                        st.audio(audio_data, format="audio/mpeg")

                        # Option to download audio
                        st.download_button(
                            label="💾 Download Audio",
                            data=audio_data,
                            file_name=f"tts_output_{int(time.time())}.mp3",
                            mime="audio/mpeg",
                        )
            else:
                st.warning("Please enter text to synthesize.")

    with col2:
        st.subheader("Call Audio Management")

        # Simulate call start/stop (in real implementation, this would connect to Twilio)
        if not st.session_state.call_active:
            if st.button("📞 Start Simulated Call", type="primary"):
                st.session_state.call_sid = f"call_{uuid.uuid4().hex[:8]}"
                st.session_state.call_active = True
                st.rerun()
        else:
            if st.button("📞 End Call", type="secondary"):
                st.session_state.call_active = False
                st.session_state.call_sid = None
                st.rerun()

with tab3:
    st.header("📝 Real-time Transcription")

    if st.session_state.call_active:
        st.info("Transcription would appear here during an active call")

        # Simulated transcription display
        if st.button("🔄 Refresh Transcription"):
            # In real implementation, this would fetch from the transcription service
            sample_transcription = [
                {
                    "timestamp": "14:30:15",
                    "speaker": "Customer",
                    "text": "I'm interested in your premium package",
                },
                {
                    "timestamp": "14:30:22",
                    "speaker": "Agent",
                    "text": "Great! Let me tell you about our premium features...",
                },
            ]
            st.session_state.transcription_log.extend(sample_transcription)

        # Display transcription log
        if st.session_state.transcription_log:
            for entry in st.session_state.transcription_log:
                speaker_color = "#1f77b4" if entry["speaker"] == "Agent" else "#ff7f0e"
                st.markdown(
                    f"""
                <div style="margin: 0.5rem 0; padding: 0.5rem; border-left: 3px solid {speaker_color};">
                    <strong style="color: {speaker_color};">{entry["speaker"]}</strong> 
                    <span style="color: #666; font-size: 0.8rem;">({entry["timestamp"]})</span><br>
                    {entry["text"]}
                </div>
                """,
                    unsafe_allow_html=True,
                )
    else:
        st.warning("No active call. Start a call to see transcription.")

with tab4:
    st.header("💉 Audio Injection")

    if st.session_state.call_active:
        col1, col2 = st.columns([3, 1])

        with col1:
            injection_text = st.text_area(
                "Enter text to inject as audio:",
                height=100,
                placeholder="This will be converted to speech and played during the call...",
            )

        with col2:
            st.write("**Current Call:**")
            st.code(st.session_state.call_sid)

            if st.button("🎯 Inject Audio", type="primary"):
                if injection_text.strip():
                    with st.spinner("Injecting audio..."):
                        result = inject_audio(injection_text, st.session_state.call_sid)
                        if result:
                            st.success("✅ Audio injected successfully!")
                            st.json(result)
                else:
                    st.warning("Please enter text to inject.")

        # Quick injection buttons
        st.subheader("🚀 Quick Injections")
        quick_responses = [
            "Thank you for holding. Let me get that information for you.",
            "I understand your concern. Let me explain how we can help.",
            "That's a great question. Here's what I recommend...",
            "Let me transfer you to a specialist who can better assist you.",
        ]

        cols = st.columns(2)
        for i, response in enumerate(quick_responses):
            with cols[i % 2]:
                if st.button(f"💬 Inject: '{response[:30]}...'", key=f"quick_{i}"):
                    with st.spinner("Injecting..."):
                        result = inject_audio(response, st.session_state.call_sid)
                        if result:
                            st.success("Injected!")
    else:
        st.warning("No active call. Start a call to inject audio.")

with tab5:
    st.header("📋 Call Management & Analytics")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Call History")
        if st.button("🔄 Refresh Call Data"):
            st.info("Call history would be loaded from the backend")

        # Sample call data
        call_data = [
            {"call_id": "call_001", "duration": "5:23", "status": "Completed"},
            {"call_id": "call_002", "duration": "3:45", "status": "In Progress"},
            {"call_id": "call_003", "duration": "7:12", "status": "Completed"},
        ]

        for call in call_data:
            with st.expander(f"📞 {call['call_id']} - {call['status']}"):
                st.write(f"**Duration:** {call['duration']}")
                st.write(f"**Status:** {call['status']}")

                if st.button(f"📊 View Pitch Screen", key=f"pitch_{call['call_id']}"):
                    result = get_pitch_screen(call["call_id"])
                    if result:
                        st.json(result)

    with col2:
        st.subheader("System Health")

        # API Health Check
        if st.button("🏥 Check API Health"):
            try:
                response = requests.get(f"{FASTAPI_BASE_URL}/docs")
                if response.status_code == 200:
                    st.success("✅ FastAPI Backend: Healthy")
                else:
                    st.error("❌ FastAPI Backend: Unhealthy")
            except:
                st.error("❌ FastAPI Backend: Unreachable")

        # WebSocket Health Check
        if st.button("🔌 Test WebSocket"):
            st.info("WebSocket test would be performed here")

        # Statistics
        st.subheader("📊 Session Statistics")
        stats_col1, stats_col2 = st.columns(2)
        with stats_col1:
            st.metric("Pitches Generated", len(st.session_state.pitch_history))
            st.metric("Active Calls", 1 if st.session_state.call_active else 0)
        with stats_col2:
            st.metric("Transcription Lines", len(st.session_state.transcription_log))
            st.metric("Session Duration", f"{int(time.time()) % 3600}s")

# Footer
st.markdown("---")
st.markdown(
    """
<div style="text-align: center; color: #666; padding: 1rem;">
    🤖 AI Sales Call Assistant | Built with Streamlit & FastAPI<br>
    Real-time audio processing, AI-powered pitch generation, and seamless call management
    
</div>
            
""",
    unsafe_allow_html=True,
)
# Embed ElevenLabs Convai Widget
components.html(
    """
    <elevenlabs-convai agent-id="agent_01jwbj5t1qfbyvpvtx8m8njeq9"></elevenlabs-convai>
    <script src="https://unpkg.com/@elevenlabs/convai-widget-embed" async type="text/javascript"></script>
    """,
    height=350,  # Or adjust as needed
)


# Auto-refresh for real-time updates (optional)
if st.session_state.call_active:
    time.sleep(1)  # Small delay for demo purposes
    # In production, you'd use st.rerun() with proper WebSocket handling
