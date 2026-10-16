import io
import numpy as np
import pyaudio
import wave

from core.config import get_config


class Recorder:
    def __init__(self):
        cfg = get_config()["audio"]
        self.rate = int(cfg.get("sample_rate", 16000))
        self.chunk = 1024
        self.silence_timeout = float(cfg.get("silence_timeout", 1.5))
        self.debug = bool(cfg.get("debug", False))
        self.pa = pyaudio.PyAudio()
        self.energy_threshold = 0.02
        self.input_device_index = self._select_device(cfg.get("input_device"))

    def _select_device(self, preferred):
        devices = []
        try:
            for i in range(self.pa.get_device_count()):
                info = self.pa.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) > 0:
                    devices.append((i, info["name"]))
        except Exception:
            devices = []

        chosen = None
        if preferred is not None:
            if isinstance(preferred, int):
                chosen = preferred
            else:
                for i, name in devices:
                    if preferred.lower() in name.lower():
                        chosen = i
                        break
        if chosen is None:
            # auto-pick a device whose name mentions "microphone"
            for i, name in devices:
                if "microphone" in name.lower():
                    chosen = i
                    break
        if chosen is None:
            try:
                chosen = self.pa.get_default_input_device_info()["index"]
            except Exception:
                chosen = None
        name = next((n for i, n in devices if i == chosen), "default")
        print(f"[audio] Using input device #{chosen}: {name}")
        return chosen

    def _rms(self, data):
        arr = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        if arr.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(arr ** 2)))

    def _calibrate(self, stream, seconds=0.4):
        n = max(1, int(self.rate / self.chunk * seconds))
        levels = []
        for _ in range(n):
            data = stream.read(self.chunk, exception_on_overflow=False)
            levels.append(self._rms(data))
        ambient = max(levels) if levels else 0.0
        self.energy_threshold = max(ambient * 1.6, 0.012)
        if self.debug:
            print(f"[vad] ambient={ambient:.4f} threshold={self.energy_threshold:.4f}")

    def _to_wav(self, frames):
        f = io.BytesIO()
        wf = wave.open(f, "wb")
        wf.setnchannels(1)
        wf.setsampwidth(self.pa.get_sample_size(pyaudio.paInt16))
        wf.setframerate(self.rate)
        wf.writeframes(b"".join(frames))
        wf.close()
        return f.getvalue()

    def record_until_silence(self, max_seconds=15, start_speaking_timeout=8.0):
        stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            input=True,
            input_device_index=self.input_device_index,
            frames_per_buffer=self.chunk,
        )
        self._calibrate(stream)
        frames = []
        spoke = False
        silent_chunks = 0
        silence_limit = int(self.silence_timeout * self.rate / self.chunk)
        start_chunks = int(self.rate / self.chunk * start_speaking_timeout)
        for i in range(int(self.rate / self.chunk * max_seconds)):
            data = stream.read(self.chunk, exception_on_overflow=False)
            frames.append(data)
            rms = self._rms(data)
            if self.debug:
                bar = "#" * int(min(rms / (self.energy_threshold + 1e-6), 10))
                print(f"[vad] {rms:.4f} {bar}", end="\r", flush=True)
            if rms > self.energy_threshold:
                spoke = True
                silent_chunks = 0
            elif spoke:
                silent_chunks += 1
                if silent_chunks > silence_limit:
                    break
            if not spoke and i > start_chunks:
                break
        if self.debug:
            print()
        stream.stop_stream()
        stream.close()
        return self._to_wav(frames)

    def close(self):
        self.pa.terminate()
