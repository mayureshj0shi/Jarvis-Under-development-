from core.config import get_config


class WakeWordDetector:
    """Wake-word detection.

    Primary: openwakeword (onnxruntime) if it can load the configured model.
    Fallback: STT keyword detection, performed by the orchestrator using the
    main STT pipeline (no native build required).
    """

    def __init__(self):
        self.cfg = get_config().get("wake_word", {})
        self.model = None
        self._try_load()

    def _try_load(self):
        try:
            from openwakeword.model import Model

            name = self.cfg.get("model", "jarvis")
            self.model = Model(wake_words=[name])
            self.available = True
        except Exception as e:
            self.available = False
            self._load_error = str(e)

    def available(self):
        return self.model is not None

    def detect(self, pcm_frames):
        """pcm_frames: bytes of 16-bit mono audio at the model sample rate.
        Returns True if wake word detected."""
        if self.model is None:
            return False
        # openwakeword expects a dict of model->float; we just call predict.
        preds = self.model.predict(pcm_frames)
        return any(v > self.cfg.get("sensitivity", 0.5) for v in preds.values())
