from __future__ import annotations

from game.state import GameState, PlayerState
from players.base_player import BasePlayer
from ui.cli import CLI


class HumanPlayer(BasePlayer):
    def __init__(self, state: PlayerState, cli: CLI):
        super().__init__(state)
        self.cli = cli

    def speak(self, game_state: GameState) -> str:
        return self.cli.prompt(f"{self.name}，请发表你的观点：").strip() or "我先保留意见，继续听后续发言。"

    def vote(self, game_state: GameState) -> str:
        options = [n for n in game_state.alive_names() if n != self.name]
        return self.cli.choose_from(f"{self.name}，请选择你要投票放逐的玩家：", options)

    def last_words(self, game_state: GameState) -> str:
        return self.cli.prompt(f"{self.name}，请输入你的遗言：").strip() or "我没有更多要说的了。"
