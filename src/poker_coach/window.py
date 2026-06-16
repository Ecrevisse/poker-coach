"""Locate a target window (PokerTH) on the desktop.

Hyprland (Wayland) primary via `hyprctl clients -j`. Returns absolute monitor
coordinates so screen capture can crop the window region.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class WindowBounds:
    x: int
    y: int
    w: int
    h: int


class WindowNotFoundError(RuntimeError):
    pass


class WindowLocator:
    """Find a window by class or title substring (case-insensitive)."""

    def __init__(self, match: str = "pokerth") -> None:
        self.match = match.lower()

    def find(self) -> WindowBounds:
        if shutil.which("hyprctl"):
            return self._find_hyprland()
        raise WindowNotFoundError("No supported window manager tool (hyprctl) found")

    def _find_hyprland(self) -> WindowBounds:
        out = subprocess.run(
            ["hyprctl", "clients", "-j"], capture_output=True, text=True, check=True
        ).stdout
        clients = json.loads(out)
        for c in clients:
            haystack = f"{c.get('class', '')} {c.get('title', '')}".lower()
            if self.match in haystack:
                x, y = c["at"]
                w, h = c["size"]
                return WindowBounds(x=int(x), y=int(y), w=int(w), h=int(h))
        raise WindowNotFoundError(f"No window matching {self.match!r}")
