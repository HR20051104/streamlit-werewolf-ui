from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import random

from game.config_models import TieBreakPolicy, VoteRuleConfig
from game.roles import Role


DEFAULT_ROLE_TABLE: dict[int, list[Role]] = {
    6: [Role.WEREWOLF, Role.WEREWOLF, Role.SEER, Role.WITCH, Role.VILLAGER, Role.VILLAGER],
    7: [Role.WEREWOLF, Role.WEREWOLF, Role.SEER, Role.WITCH, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER],
    8: [Role.WEREWOLF, Role.WEREWOLF, Role.SEER, Role.WITCH, Role.GUARD, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER],
    9: [Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF, Role.SEER, Role.WITCH, Role.GUARD, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER],
    10: [Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF, Role.SEER, Role.WITCH, Role.HUNTER, Role.GUARD, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER],
    11: [Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF, Role.SEER, Role.WITCH, Role.HUNTER, Role.GUARD, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER],
    12: [Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF, Role.SEER, Role.WITCH, Role.HUNTER, Role.GUARD, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER],
}


def build_role_pool(total_players: int, custom: dict[int, list[Role]] | None = None) -> list[Role]:
    table = custom or DEFAULT_ROLE_TABLE
    if total_players not in table:
        raise ValueError(f"Unsupported player count: {total_players}")
    return list(table[total_players])


@dataclass(slots=True)
class VoteResolution:
    eliminated: str | None
    tally: dict[str, int]
    tied_candidates: list[str]
    is_tie: bool


def tally_votes(votes: dict[str, str]) -> dict[str, int]:
    return dict(Counter(votes.values()))


def resolve_vote(votes: dict[str, str], rules: VoteRuleConfig) -> VoteResolution:
    tally = tally_votes(votes)
    if not tally:
        return VoteResolution(None, tally, [], False)

    highest = max(tally.values())
    tied = sorted([name for name, value in tally.items() if value == highest])
    if len(tied) == 1:
        return VoteResolution(tied[0], tally, [], False)

    eliminated: str | None = None
    if rules.final_tie_policy == TieBreakPolicy.RANDOM:
        eliminated = random.choice(tied)
    return VoteResolution(eliminated, tally, tied, True)
