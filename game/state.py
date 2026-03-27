from __future__ import annotations

from dataclasses import dataclass, field
from collections import Counter
from typing import Any

from game.roles import Role


@dataclass(slots=True)
class WitchState:
    has_heal: bool = True
    has_poison: bool = True


@dataclass(slots=True)
class GuardState:
    last_protected: str | None = None


@dataclass(slots=True)
class PlayerState:
    name: str
    role: Role
    is_human: bool
    alive: bool = True
    suspicion_map: dict[str, float] = field(default_factory=dict)
    private_knowledge: dict[str, Any] = field(default_factory=dict)
    last_action: str | None = None
    last_vote: str | None = None
    last_statement: str | None = None


@dataclass(slots=True)
class NightResult:
    protected_target: str | None = None
    wolf_target: str | None = None
    saved_by_witch: bool = False
    poisoned_target: str | None = None
    blocked_by_guard: bool = False
    wolf_chat: list[tuple[str, str]] = field(default_factory=list)
    wolf_ai_reply: str | None = None
    dead_players: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DayRecord:
    day: int
    statements: list[tuple[str, str]] = field(default_factory=list)
    votes: dict[str, str] = field(default_factory=dict)
    vote_tally: dict[str, int] = field(default_factory=dict)
    tie_candidates: list[str] = field(default_factory=list)
    executed: str | None = None
    night_result: NightResult | None = None


@dataclass(slots=True)
class GameState:
    day: int = 1
    phase: str = "init"
    players: dict[str, PlayerState] = field(default_factory=dict)
    records: list[DayRecord] = field(default_factory=list)
    witch: WitchState = field(default_factory=WitchState)
    guard: GuardState = field(default_factory=GuardState)

    def alive_players(self) -> list[PlayerState]:
        return [p for p in self.players.values() if p.alive]

    def alive_names(self) -> list[str]:
        return [p.name for p in self.alive_players()]

    def role_of(self, name: str) -> Role:
        return self.players[name].role

    def count_alive_votes(self, votes: dict[str, str]) -> Counter[str]:
        return Counter(votes.values())
