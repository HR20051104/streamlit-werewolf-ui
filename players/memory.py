from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MemoryEvent:
    day: int
    phase: str
    event_type: str
    content: dict[str, Any]


@dataclass(slots=True)
class PlayerMemory:
    events: list[MemoryEvent] = field(default_factory=list)

    def add(self, day: int, phase: str, event_type: str, content: dict[str, Any]) -> None:
        self.events.append(MemoryEvent(day, phase, event_type, content))

    def recent(self, limit: int = 12) -> list[MemoryEvent]:
        return self.events[-limit:]
