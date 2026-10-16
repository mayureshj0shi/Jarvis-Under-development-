import asyncio

import sounddevice as sd
import miniaudio

import edge_tts

from core.config import get_config


class TTS:
    def __init__(self):
        cfg = get_config()["tts"]
        self.engine = cfg.get("engine", "edge")
        self.voice = cfg.get("edge_voice", "en-US-AndrewNeural")
        self.rate = cfg.get("rate", 0)
        self._pyttsx = None

    async def _edge_stream(self, text):
        rate = f"{self.rate:+d}%" if self.rate else "+0%"
        comm = edge_tts.Communicate(text, self.voice, rate=rate)
        async for chunk in comm.stream():
            yield chunk

    async def _edge_synthesize(self, text):
        data = b""
        async for chunk in self._edge_stream(text):
            if chunk["type"] == "audio":
                data += chunk["data"]
        return data

    async def _edge_speak(self, text):
        data = await self._edge_synthesize(text)
        if not data:
            return False
        pcm = miniaudio.decode(
            data,
            output_format=miniaudio.SampleFormat.FLOAT32,
            nchannels=1,
            sample_rate=24000,
        )
        try:
            sd.play(pcm.samples, pcm.sample_rate)
            sd.wait()
        except Exception as e:
            print(f"[tts] playback failed (no output device?): {e}")
            return False
        return True

    def synthesize(self, text):
        """Return MP3 audio bytes for `text` (edge-tts), or b'' on failure.
        Used by the external API so the client can play audio itself."""
        if not text:
            return b""
        if self.engine == "edge":
            try:
                return asyncio.run(self._edge_synthesize(text))
            except Exception as e:
                print(f"[edge-tts synthesize failed] {e}")
        return b""

    def _pyttsx3_speak(self, text):
        import pyttsx3

        if self._pyttsx is None:
            self._pyttsx = pyttsx3.init()
        self._pyttsx.say(text)
        self._pyttsx.runAndWait()

    def speak(self, text):
        if not text:
            return
        if self.engine == "edge":
            try:
                ok = asyncio.run(self._edge_speak(text))
                if ok:
                    return
            except Exception as e:
                print(f"[edge-tts failed, using pyttsx3] {e}")
        self._pyttsx3_speak(text)
