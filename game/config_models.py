from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class NarrationStyle(str, Enum):
    CONCISE = "concise"
    STANDARD = "standard"
    IMMERSIVE = "immersive"


class TieBreakPolicy(str, Enum):
    RANDOM = "random"
    NO_ELIMINATION = "no_elimination"


@dataclass(slots=True)
class VoteRuleConfig:
    revote_on_tie: bool = True
    revote_discussion_rounds: int = 1
    final_tie_policy: TieBreakPolicy = TieBreakPolicy.NO_ELIMINATION


@dataclass(slots=True)
class GameConfig:
    total_players: int = 7
    human_players: int = 1
    use_llm: bool = False
    provider: str = "mock"
    deepseek_api_key: str | None = None
    deepseek_base_url: str | None = None
    deepseek_model: str = "deepseek-chat"
    max_rounds: int = 20
    discussion_rounds: int = 1
    narration_style: NarrationStyle = NarrationStyle.STANDARD
    vote_rules: VoteRuleConfig = field(default_factory=VoteRuleConfig)
    ai_statement_max_chars: int = 160
    ai_last_words_max_chars: int = 120
    step_by_step: bool = True
    force_human_werewolf: bool = False
    human_role: str = "random"
    enable_guard: bool = True
    debug: bool = False

    def validate(self) -> None:
        if not 6 <= self.total_players <= 12:
            raise ValueError("total_players must be in [6, 12]")
        if self.human_players != 1:
            raise ValueError("Current version supports exactly 1 human player")
        if self.discussion_rounds not in (1, 2):
            raise ValueError("discussion_rounds must be 1 or 2")
        if self.ai_statement_max_chars < 20:
            raise ValueError("ai_statement_max_chars must be >= 20")
        if self.ai_last_words_max_chars < 20:
            raise ValueError("ai_last_words_max_chars must be >= 20")
        allowed_human_roles = {"random", "werewolf", "seer", "witch", "guard", "hunter", "villager"}
        if self.human_role not in allowed_human_roles:
            raise ValueError(f"human_role must be one of {sorted(allowed_human_roles)}")
