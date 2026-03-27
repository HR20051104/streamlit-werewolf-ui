from __future__ import annotations

import argparse
import os
import sys

from game.config_models import GameConfig
from game.engine import GameEngine
from ui.cli import CLI, run_cli
from ui.io import IOBase
from utils.config import load_config
from utils.logger import setup_logger


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="单人狼人杀")
    parser.add_argument("--mode", choices=["cli", "ui"], default="cli", help="运行模式")
    parser.add_argument("--players", type=int, default=None, help="总人数(6~12)")
    parser.add_argument("--discussion-rounds", type=int, choices=[1, 2], default=None)
    parser.add_argument("--step-by-step", choices=["true", "false"], default=None)
    return parser


def _override(base: GameConfig, args: argparse.Namespace) -> GameConfig:
    if args.players is not None:
        base.total_players = args.players
    if args.discussion_rounds is not None:
        base.discussion_rounds = args.discussion_rounds
    if args.step_by_step is not None:
        base.step_by_step = args.step_by_step == "true"
    return base


def main() -> None:
    args = _build_parser().parse_args()
    config = _override(load_config(), args)
    setup_logger(config.debug)

    if args.mode == "ui":
        os.execvp(sys.executable, [sys.executable, "-m", "streamlit", "run", "ui/streamlit_app.py"])

    io: IOBase = CLI()
    engine = GameEngine(config, io)
    run_cli(engine)


if __name__ == "__main__":
    main()
