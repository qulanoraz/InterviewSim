# app/services/deepgram_service.py
from dotenv import load_dotenv
load_dotenv()   # на всякий случай

import os, asyncio, base64
from deepgram import DeepgramClient, PrerecordedOptions
from flask import current_app
from app.utils.logger import get_logger

logger = get_logger(__name__)

print("DEBUG: DEEPGRAM_API_KEY in deepgram_service =", os.environ.get("DEEPGRAM_API_KEY"))

def _get_deepgram_key():
    # 1) сначала из environment
    key = os.getenv('DEEPGRAM_API_KEY')
    # 2) если нет — из current_app.config (на случай, если вы грузите конфиг туда)
    if not key and current_app:
        key = current_app.config.get('DEEPGRAM_API_KEY')
    return key

def _init_client():
    key = _get_deepgram_key()
    if not key:
        raise RuntimeError("Deepgram API key not configured (checked ENV and current_app)")
    return DeepgramClient(key)

async def _transcribe_async(audio_bytes: bytes) -> str:
    dg = _init_client()
    source = {"buffer": audio_bytes, "mimetype": "audio/wav"}
    options = {"punctuate": True, "model": "nova-2"}
    logger.info("Sending audio to Deepgram...")
    resp = await dg.transcription.prerecorded(source, options)
    return resp["results"]["channels"][0]["alternatives"][0]["transcript"]

def transcribe_audio(audio_base64_string: str) -> str | None:
    """
    Transcribes audio from a base64 encoded string using Deepgram.

    Args:
        audio_base64_string: The base64 encoded audio data (WAV format recommended).

    Returns:
        The transcript text if successful, None otherwise.
    """
    api_key = current_app.config.get('DEEPGRAM_API_KEY')
    if not api_key:
        logger.error("Deepgram API key not configured.")
        return None

    try:
        deepgram = DeepgramClient(api_key)
        audio_bytes = base64.b64decode(audio_base64_string)
        payload = {"buffer": audio_bytes}

        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True,
        )

        logger.info("Sending audio to Deepgram for transcription...")
        response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)
        
        transcript = response.results.channels[0].alternatives[0].transcript
        logger.info(f"Transcript received: {transcript[:50]}...")
        return transcript

    except Exception as e:
        logger.error(f"Error during Deepgram transcription: {e}")
        return None
