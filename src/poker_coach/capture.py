"""Screen capture via mss."""

from __future__ import annotations

import numpy as np

from .calibration import ROI


class ScreenCapture:
    def __init__(self, monitor_idx: int = 1) -> None:
        import mss

        self._sct = mss.mss()
        if monitor_idx >= len(self._sct.monitors):
            raise ValueError(f"Monitor {monitor_idx} not found")
        self.monitor = self._sct.monitors[monitor_idx]

    def grab(self) -> np.ndarray:
        """Full monitor frame, BGR (H, W, 3)."""
        img = np.array(self._sct.grab(self.monitor))
        return img[:, :, :3]

    @staticmethod
    def crop(img: np.ndarray, roi: ROI) -> np.ndarray:
        return img[roi.y : roi.y + roi.h, roi.x : roi.x + roi.w]
