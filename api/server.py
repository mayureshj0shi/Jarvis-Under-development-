import asyncio
import base64
import json
import os

from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from core.config import load_config
from core.orchestrator import Orchestrator
from audio.stt import transcribe


load_config()
orch = Orchestrator(speak=False)

app = FastAPI(title="Jarvis API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Accept raw audio bytes (WAV recommended) and return transcribed text."""
    data = await audio.read()
    if not data:
        raise HTTPException(400, "Empty audio payload")
    try:
        text = transcribe(data)
    except Exception as e:
        raise HTTPException(500, f"STT failed: {e}")
    return {"text": text}


@app.post("/speak")
async def speak(payload: dict):
    """Body: {"text": "..."}. Returns MP3 audio bytes."""
    text = (payload or {}).get("text", "")
    if not text:
        raise HTTPException(400, "Missing 'text'")
    audio_bytes = await asyncio.to_thread(orch.tts.synthesize, text)
    if not audio_bytes:
        raise HTTPException(500, "TTS failed to produce audio")
    return Response(content=audio_bytes, media_type="audio/mpeg")


@app.get("/history")
def history():
    return {"messages": orch.messages}


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_running_loop()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                await websocket.send_json({"type": "error", "text": "Invalid JSON"})
                continue
            text = (msg or {}).get("text", "")
            if not text:
                continue

            queue: asyncio.Queue = asyncio.Queue()

            def on_token(t):
                loop.call_soon_threadsafe(queue.put_nowait, t)

            async def drain():
                while True:
                    t = await queue.get()
                    if t is None:
                        queue.task_done()
                        break
                    await websocket.send_json({"type": "token", "text": t})
                    queue.task_done()

            drain_task = asyncio.create_task(drain())
            try:
                reply = await asyncio.to_thread(orch.stream_text, text, on_token)
            except Exception as e:
                await websocket.send_json({"type": "error", "text": str(e)})
                await queue.put(None)
                await drain_task
                continue

            await queue.put(None)
            await drain_task

            audio_bytes = await asyncio.to_thread(orch.tts.synthesize, reply)
            await websocket.send_json(
                {
                    "type": "audio",
                    "data": base64.b64encode(audio_bytes).decode("ascii"),
                }
            )
            await websocket.send_json({"type": "done", "text": reply})
    except Exception:
        # Client disconnected or stream ended; clean up silently.
        try:
            await websocket.close()
        except Exception:
            pass
