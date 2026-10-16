import os
import io
import re
import json
import base64
import requests
import speech_recognition as sr

from core.config import get_config


def _gemini_key():
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key or key.startswith("PASTE_"):
        return None
    return key


def transcribe_groq(wav_bytes, model=None):
    cfg = get_config()["groq"]
    key = os.environ.get(cfg["api_key_env"])
    if not key:
        raise RuntimeError("Missing GROQ_API_KEY")
    model = model or cfg.get("stt_model", "whisper-large-v3")
    files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
    data = {"model": model, "response_format": "json"}
    resp = requests.post(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {key}"},
        files=files,
        data=data,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json().get("text", "").strip()


def transcribe_google(wav_bytes):
    r = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(wav_bytes)) as src:
        audio = r.record(src)
    return r.recognize_google(audio).strip()


def transcribe_gemini(wav_bytes, model=None):
    key = _gemini_key()
    if not key:
        raise RuntimeError("Missing or placeholder GEMINI_API_KEY")
    cfg = get_config()["stt"]
    model = model or cfg.get("gemini_model", "gemini-2.5-flash")
    b64 = base64.b64encode(wav_bytes).decode("ascii")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={key}"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Transcribe the following audio recording accurately. "
                            "Output only the transcribed speech as plain text, "
                            "with no commentary, no quotes, and no extra formatting."
                        )
                    },
                    {"inline_data": {"mime_type": "audio/wav", "data": b64}},
                ]
            }
        ]
    }
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(f"Unexpected Gemini STT response: {data}")
    return text.strip()


def _light_clean(text):
    """WhisperFlow-style light cleanup: capitalize + ensure terminal punctuation.
    Deliberately does NOT strip words, so command intent is preserved."""
    if not text:
        return text
    t = text.strip()
    t = t[0].upper() + t[1:] if t else t
    if t and t[-1] not in ".!?":
        t += "."
    return t


def transcribe(wav_bytes):
    cfg = get_config()["stt"]
    order = cfg.get("order", ["gemini", "google", "groq"])
    last_err = None
    for tier in order:
        try:
            if tier == "gemini":
                t = transcribe_gemini(wav_bytes)
            elif tier == "google":
                t = transcribe_google(wav_bytes)
            elif tier == "groq":
                t = transcribe_groq(wav_bytes)
            else:
                continue
            if t:
                if cfg.get("auto_clean"):
                    t = _light_clean(t)
                return t
        except Exception as e:
            last_err = e
    raise RuntimeError(f"STT failed: {last_err}")
