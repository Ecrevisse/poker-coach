"""Screen capture via grim (Wayland). Crops are in-memory."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

from .calibration import ROI
from .window import WindowBounds


class ScreenCapture:
    def __init__(self, scale: int = 1) -> None:
        self.scale = scale

    def grab_window(self, bounds: WindowBounds) -> np.ndarray:
        """Capture the given window region. Returns BGR (H, W, 3)."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            path = Path(tmp.name)
        try:
            subprocess.run(
                [
                    "grim",
                    "-s", str(self.scale),
                    "-g", f"{bounds.x},{bounds.y} {bounds.w}x{bounds.h}",
                    str(path),
                ],
                check=True,
                capture_output=True,
            )
            img = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if img is None:
                raise RuntimeError(f"grim wrote unreadable PNG: {path}")
            return img
        finally:
            path.unlink(missing_ok=True)

    @staticmethod
    def crop(img: np.ndarray, roi: ROI) -> np.ndarray:
        return img[roi.y : roi.y + roi.h, roi.x : roi.x + roi.w]
