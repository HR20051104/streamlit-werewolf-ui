from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class InputRequest:
    kind: str
    prompt: str
    options: list[str] | None = None


class IOBase:
    def __init__(self) -> None:
        self.logs: list[str] = []

    def line(self, text: str = "") -> None:
        self.logs.append(text)

    def title(self, text: str) -> None:
        self.logs.append(f"\n=== {text} ===")
