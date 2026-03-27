from __future__ import annotations

from collections import Counter
import random

from game.roles import Role, Team
from game.state import GameState, PlayerState


def init_suspicion(player: PlayerState, game_state: GameState) -> None:
    for name, other in game_state.players.items():
        if name == player.name:
            continue
        base = 0.5
        if player.role == Role.WEREWOLF and other.role == Role.WEREWOLF:
            base = 0.0
        player.suspicion_map[name] = base


def _adjust(player: PlayerState, target: str, delta: float) -> None:
    if target not in player.suspicion_map:
        return
    player.suspicion_map[target] = max(0.0, min(1.0, player.suspicion_map[target] + delta))


def update_suspicion(player: PlayerState, game_state: GameState) -> None:
    if not player.alive:
        return
    alive = set(game_state.alive_names())
    for name in list(player.suspicion_map):
        if name not in alive:
            player.suspicion_map[name] *= 0.8

    if game_state.records:
        last = game_state.records[-1]
        vote_counter = Counter(last.votes.values())
        for voter, target in last.votes.items():
            if voter == player.name or target not in player.suspicion_map:
                continue
            alignment = player.suspicion_map.get(target, 0.5)
            _adjust(player, voter, -0.08 * alignment)
            if vote_counter[target] >= 2:
                _adjust(player, target, 0.06)

    if player.role == Role.SEER:
        for name, result in player.private_knowledge.get("seer_checks", {}).items():
            if result == Team.WOLF.value:
                player.suspicion_map[name] = 1.0
            else:
                player.suspicion_map[name] = min(player.suspicion_map.get(name, 0.5), 0.2)

    if player.role == Role.WEREWOLF:
        teammates = set(player.private_knowledge.get("wolf_teammates", []))
        for mate in teammates:
            if mate in player.suspicion_map:
                player.suspicion_map[mate] = 0.0

    for name in player.suspicion_map:
        _adjust(player, name, random.uniform(-0.03, 0.03))


def top_suspect(player: PlayerState, game_state: GameState) -> str:
    candidates = [n for n in game_state.alive_names() if n != player.name]
    candidates.sort(key=lambda n: player.suspicion_map.get(n, 0.5), reverse=True)
    return candidates[0]


def vote_target(player: PlayerState, game_state: GameState, conformity: float = 1.0) -> str:
    candidates = [n for n in game_state.alive_names() if n != player.name]
    if player.role == Role.WEREWOLF:
        teammates = set(player.private_knowledge.get("wolf_teammates", []))
        non_mates = [c for c in candidates if c not in teammates]
        if non_mates:
            candidates = non_mates

    leader: str | None = None
    if game_state.records and game_state.records[-1].votes:
        cnt = Counter(game_state.records[-1].votes.values())
        leader = cnt.most_common(1)[0][0]

    if leader and leader in candidates and random.random() < max(0.0, conformity - 0.9):
        return leader

    return max(candidates, key=lambda n: player.suspicion_map.get(n, 0.5))


def wolf_night_target(wolf: PlayerState, game_state: GameState) -> str:
    candidates = [n for n in game_state.alive_names() if n != wolf.name]
    teammates = set(wolf.private_knowledge.get("wolf_teammates", []))
    candidates = [c for c in candidates if c not in teammates]

    # Use only public information (no real-role peeking):
    # - personal suspicion
    # - recent vote pressure (high-profile targets are often influential)
    vote_counter = Counter()
    if game_state.records:
        vote_counter = Counter(game_state.records[-1].votes.values())

    def weight(name: str) -> float:
        suspicion_score = wolf.suspicion_map.get(name, 0.5)
        public_pressure_score = 0.08 * vote_counter.get(name, 0)
        return suspicion_score + public_pressure_score

    # Avoid deterministic "first-name always targeted" when scores tie,
    # especially in night-1 where information is sparse.
    if not candidates:
        return wolf.name
    scores = {name: weight(name) for name in candidates}
    best = max(scores.values())
    top = [name for name, sc in scores.items() if abs(sc - best) < 1e-9]
    return random.choice(top)


def seer_check_target(seer: PlayerState, game_state: GameState) -> str:
    checked = set(seer.private_knowledge.get("seer_checks", {}).keys())
    candidates = [n for n in game_state.alive_names() if n != seer.name and n not in checked]
    if not candidates:
        candidates = [n for n in game_state.alive_names() if n != seer.name]
    return max(candidates, key=lambda n: seer.suspicion_map.get(n, 0.5))


def guard_protect_target(guard: PlayerState, game_state: GameState) -> str:
    candidates = [n for n in game_state.alive_names() if n != guard.name]
    if game_state.guard.last_protected in candidates and len(candidates) > 1:
        candidates = [n for n in candidates if n != game_state.guard.last_protected]
    return min(candidates, key=lambda n: guard.suspicion_map.get(n, 0.5))
