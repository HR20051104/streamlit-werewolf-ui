from __future__ import annotations

from abc import ABC, abstractmethod
from game.state import GameState, PlayerState


class BasePlayer(ABC):
    def __init__(self, state: PlayerState):
        self.state = state

    @property
    def name(self) -> str:
        return self.state.name

    @property
    def alive(self) -> bool:
        return self.state.alive

    @abstractmethod
    def speak(self, game_state: GameState) -> str:
        raise NotImplementedError

    @abstractmethod
    def vote(self, game_state: GameState) -> str:
        raise NotImplementedError

    @abstractmethod
    def last_words(self, game_state: GameState) -> str:
        raise NotImplementedError
