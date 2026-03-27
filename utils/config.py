from __future__ import annotations

import os
from pathlib import Path

from game.config_models import GameConfig, NarrationStyle, TieBreakPolicy, VoteRuleConfig


def _load_dotenv_if_exists(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        striped = line.strip()
        if not striped or striped.startswith("#") or "=" not in striped:
            continue
        key, value = striped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def load_config() -> GameConfig:
    _load_dotenv_if_exists()
    total_players_raw = os.getenv("TOTAL_PLAYERS")
    if total_players_raw is not None:
        total_players = int(total_players_raw)
    else:
        # Backward compatibility: old config used AI_COUNT (AI number only)
        total_players = int(os.getenv("AI_COUNT", "6")) + 1
    return GameConfig(
        total_players=total_players,
        human_players=int(os.getenv("HUMAN_PLAYERS", "1")),
        use_llm=os.getenv("USE_LLM", "false").lower() == "true",
        provider=os.getenv("LLM_PROVIDER", "mock"),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        max_rounds=int(os.getenv("MAX_ROUNDS", "20")),
        discussion_rounds=int(os.getenv("DISCUSSION_ROUNDS", "1")),
        ai_statement_max_chars=int(os.getenv("AI_STATEMENT_MAX_CHARS", "160")),
        ai_last_words_max_chars=int(os.getenv("AI_LAST_WORDS_MAX_CHARS", "120")),
        step_by_step=os.getenv("STEP_BY_STEP", "true").lower() == "true",
        force_human_werewolf=os.getenv("FORCE_HUMAN_WEREWOLF", "false").lower() == "true",
        human_role=os.getenv("HUMAN_ROLE", "random"),
        enable_guard=os.getenv("ENABLE_GUARD", "true").lower() == "true",
        narration_style=NarrationStyle(os.getenv("NARRATION_STYLE", "standard")),
        vote_rules=VoteRuleConfig(
            revote_on_tie=os.getenv("REVOTE_ON_TIE", "true").lower() == "true",
            revote_discussion_rounds=int(os.getenv("REVOTE_DISCUSSION_ROUNDS", "1")),
            final_tie_policy=TieBreakPolicy(os.getenv("FINAL_TIE_POLICY", "no_elimination")),
        ),
        debug=os.getenv("DEBUG", "false").lower() == "true",
    )
