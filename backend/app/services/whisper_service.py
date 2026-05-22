"""Whisper Large v3 via DeepInfra — supplier-call transcription.

Adapted from the audit-pipeline recipe (project_13_claimiq_ai) to project_30's
UPPERCASE settings.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import openai

from app.config import settings


class WhisperService:
    def __init__(self) -> None:
        env_mock = os.environ.get("MOCK_WHISPER", "").lower() in {"1", "true", "yes"}
        self.mock_mode = env_mock or bool(getattr(settings, "MOCK_WHISPER", False))

        if self.mock_mode:
            self.client: Optional[openai.AsyncOpenAI] = None
            self.model = "mock-whisper"
            self.provider = "mock"
        elif getattr(settings, "DEEPINFRA_API_KEY", ""):
            self.client = openai.AsyncOpenAI(
                api_key=settings.DEEPINFRA_API_KEY,
                base_url=getattr(settings, "DEEPINFRA_BASE_URL", "https://api.deepinfra.com/v1/openai"),
            )
            self.model = settings.WHISPER_MODEL or "openai/whisper-large-v3"
            self.provider = "deepinfra"
        elif getattr(settings, "OPENAI_API_KEY", ""):
            self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.WHISPER_MODEL or "whisper-1"
            self.provider = "openai"
        else:
            self.client = None
            self.model = "mock-whisper"
            self.provider = "mock"
            self.mock_mode = True

    async def transcribe_audio(self, audio_file_path: str) -> Dict[str, Any]:
        if self.mock_mode or self.client is None:
            return _mock_transcript(audio_file_path)
        try:
            with open(audio_file_path, "rb") as f:
                resp = await self.client.audio.transcriptions.create(
                    model=self.model,
                    file=f,
                    language="en",
                    temperature=0.0,
                )
        except FileNotFoundError:
            return {"error": f"Audio file not found: {audio_file_path}"}
        except Exception as e:
            return {"error": f"Transcription failed ({self.provider}): {e}"}
        return {
            "transcript": getattr(resp, "text", "") or "",
            "language": "en",
            "status": "completed",
            "provider": self.provider,
            "model": self.model,
        }


def _mock_transcript(audio_file_path: str) -> Dict[str, Any]:
    """Domain-flavoured canned transcript — supplier review call."""
    name = os.path.basename(audio_file_path) or "review.wav"
    transcript = (
        "Thanks for joining today's review. We're committed to maintaining the ISO 9001 "
        "certification through Q4. We acknowledge the Q2 quality incident and have "
        "implemented corrective actions. Expect on-time delivery to return to 95% by month-end."
    )
    return {
        "transcript": transcript,
        "language": "en",
        "status": "completed",
        "provider": "mock",
        "model": "mock-whisper",
        "source_file": name,
    }
