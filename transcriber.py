import whisper
from pydub import AudioSegment
import io
import tempfile
import os

# Load Whisper model once
model = whisper.load_model("base")  # use "tiny" if needed

# Set a safe custom temp directory
safe_temp_dir = os.path.join(os.getcwd(), "temp_audio_files")
os.makedirs(safe_temp_dir, exist_ok=True)
tempfile.tempdir = safe_temp_dir

async def transcribe_user_audio_chunk(audio_bytes: bytes) -> str:
    try:
        # Convert raw audio (Twilio: 8kHz, 16-bit PCM, mono)
        audio = AudioSegment.from_raw(io.BytesIO(audio_bytes), sample_width=2, frame_rate=8000, channels=1)

        # Create a safe temp .wav file in your controlled directory
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=safe_temp_dir) as tmp:
            temp_wav_path = tmp.name
            audio.export(temp_wav_path, format="wav")

        # Transcribe using Whisper
        result = model.transcribe(temp_wav_path)

        # Clean up temp file
        os.remove(temp_wav_path)

        return result["text"].strip()
    except Exception as e:
        print(f"Transcription error: {e}")
        return ""
