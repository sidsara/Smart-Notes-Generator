import os

import torch
import whisper

_MODEL = None
_LOADED_SIZE = None

SUPPORTED_EXTENSIONS = {".flac", ".wav", ".mp3", ".m4a", ".ogg", ".mp4", ".webm"}


def _get_model(model_size: str = "base"):
    """Load and cache Whisper model to avoid reloading on every request."""
    global _MODEL, _LOADED_SIZE

    if _MODEL is None or _LOADED_SIZE != model_size:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[asr] loading whisper-{model_size} on {device}")
        _MODEL = whisper.load_model(model_size, device=device)
        _LOADED_SIZE = model_size

    return _MODEL


def transcribe(audio_path: str, model_size: str = "base") -> str:
    """Transcribe an audio file and return a plain string transcript."""
    if not os.path.exists(audio_path):
        return f"[ERROR] File not found: {audio_path}"

    ext = os.path.splitext(audio_path)[-1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return f"[ERROR] Unsupported format '{ext}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}"

    try:
        model = _get_model(model_size=model_size)
        result = model.transcribe(audio_path, fp16=torch.cuda.is_available())
        return result["text"].strip().lower()
    except Exception as exc:
        return f"[ERROR] Transcription failed: {exc}"