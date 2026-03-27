from __future__ import annotations

from game.roles import Team, ROLE_TEAM_MAP
from game.state import GameState


def check_winner(game_state: GameState) -> Team | None:
    alive = game_state.alive_players()
    wolves = [p for p in alive if ROLE_TEAM_MAP[p.role] == Team.WOLF]
    goods = [p for p in alive if ROLE_TEAM_MAP[p.role] == Team.GOOD]
    if not wolves:
        return Team.GOOD
    if len(wolves) >= len(goods):
        return Team.WOLF
    return None
