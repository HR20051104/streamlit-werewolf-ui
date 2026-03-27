from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass(frozen=True, slots=True)
class Personality:
    name: str
    speaking_style: str
    min_words: int
    max_words: int
    accusation_bias: float
    conformity_bias: float


PERSONALITIES: list[Personality] = [
    Personality("激进型", "语气直接，常主动点名。", 20, 40, 1.25, 0.6),
    Personality("谨慎型", "表达克制，强调观察。", 12, 28, 0.8, 0.9),
    Personality("话多型", "信息量大，爱复盘。", 35, 60, 1.0, 0.8),
    Personality("逻辑型", "偏推理链条，引用投票记录。", 25, 48, 1.1, 0.7),
    Personality("跟风型", "易受多数意见影响。", 10, 24, 0.75, 1.3),
    Personality("伪装型", "发言看似中庸，偶尔转移话题。", 15, 30, 0.9, 1.0),
]


def random_personality() -> Personality:
    return random.choice(PERSONALITIES)
