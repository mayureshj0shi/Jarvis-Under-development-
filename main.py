import sys

from core.config import load_config
from core.orchestrator import Orchestrator


def _check():
    load_config()
    import pyaudio
    import time

    pa = pyaudio.PyAudio()
    print("Input devices:")
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info.get("maxInputChannels", 0) > 0:
            print(f"  [{i}] {info['name']}")
    pa.terminate()

    print("\nRecording 3s test (speak now)... ")
    orch = Orchestrator(speak=False)
    orch.recorder.debug = True
    wav = orch.recorder.record_until_silence(max_seconds=3, start_speaking_timeout=3)
    print(f"Captured {len(wav)} bytes of audio.")


def main():
    load_config()
    mode = sys.argv[1] if len(sys.argv) > 1 else "voice"
    if mode == "--check":
        _check()
        return
    speak = mode not in ("--text", "text")
    orch = Orchestrator(speak=speak)
    if speak:
        orch.run_voice()
    else:
        orch.run_text()


if __name__ == "__main__":
    main()
