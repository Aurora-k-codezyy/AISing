from __future__ import annotations

import numpy as np
import sounddevice as sd


class MicrophoneMeter:
    def __init__(self) -> None:
        self.level: float = 0.0
        self.stream: sd.InputStream | None = None

    def start(self) -> None:
        if self.stream is not None:
            return
        try:
            self.stream = sd.InputStream(channels=1, callback=self._callback)
            self.stream.start()
        except Exception:
            self.stream = None

    def stop(self) -> None:
        if self.stream is None:
            return
        try:
            self.stream.stop()
            self.stream.close()
        except Exception:
            pass
        finally:
            self.stream = None

    def _callback(self, indata, frames, time, status) -> None:
        if indata is not None and len(indata):
            self.level = float(np.sqrt(np.mean(np.square(indata))))
