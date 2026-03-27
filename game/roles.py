from __future__ import annotations

from enum import Enum


class Team(str, Enum):
    GOOD = "good"
    WOLF = "wolf"


class Role(str, Enum):
    WEREWOLF = "werewolf"
    SEER = "seer"
    WITCH = "witch"
    HUNTER = "hunter"
    GUARD = "guard"
    VILLAGER = "villager"


ROLE_TEAM_MAP: dict[Role, Team] = {
    Role.WEREWOLF: Team.WOLF,
    Role.SEER: Team.GOOD,
    Role.WITCH: Team.GOOD,
    Role.HUNTER: Team.GOOD,
    Role.GUARD: Team.GOOD,
    Role.VILLAGER: Team.GOOD,
}
