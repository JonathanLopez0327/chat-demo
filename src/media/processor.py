"""Multimedia processing: Whisper transcription, GPT-4o Vision, file storage."""
from __future__ import annotations

import base64
import io
import logging
from pathlib import Path

from openai import AsyncOpenAI

from src.config import MEDIA_DIR, OPENAI_API_KEY, VISION_MODEL, WHISPER_MODEL

logger = logging.getLogger(__name__)

_openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Map WhatsApp MIME types to file extensions
_MIME_TO_EXT: dict[str, str] = {
    "audio/ogg": ".ogg",
    "audio/ogg; codecs=opus": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


async def transcribe_audio(audio_bytes: bytes, mime_type: str) -> str:
    """Transcribe audio using OpenAI Whisper API.

    Supports ogg/opus (WhatsApp voice notes native format).
    """
    ext = _MIME_TO_EXT.get(mime_type, ".ogg")
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = f"audio{ext}"

    transcription = await _openai_client.audio.transcriptions.create(
        model=WHISPER_MODEL,
        file=audio_file,
        language="es",
    )
    return transcription.text


async def analyze_image(image_bytes: bytes, context: str = "") -> str:
    """Analyze an image using GPT-4o Vision.

    Returns a textual description of the image in the context of
    industrial incident reporting.
    """
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    prompt = (
        "Describe lo que ves en esta imagen en el contexto de un reporte "
        "de incidente industrial en una fábrica de huevos. "
        "Identifica daños, equipos, condiciones de seguridad o cualquier "
        "detalle relevante para el reporte."
    )
    if context:
        prompt += f"\n\nContexto adicional del usuario: {context}"

    response = await _openai_client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_image}",
                        },
                    },
                ],
            }
        ],
        max_tokens=500,
    )
    return response.choices[0].message.content or ""


def save_media_file(
    file_bytes: bytes, incident_id: int, filename: str
) -> str:
    """Save media file to data/media/{incident_id}/{filename}.

    Returns the relative path from MEDIA_DIR.
    """
    dest_dir = MEDIA_DIR / str(incident_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename
    dest_path.write_bytes(file_bytes)
    return str(Path(str(incident_id)) / filename)
