from __future__ import annotations

from game.engine import GameEngine
from game.roles import Team
from ui.io import IOBase, InputRequest


class CLI(IOBase):
    def prompt(self, text: str) -> str:
        return input(text)

    def choose_from(self, text: str, options: list[str]) -> str:
        while True:
            print(text)
            for idx, opt in enumerate(options, start=1):
                print(f"  {idx}. {opt}")
            raw = input("> ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(options):
                return options[int(raw) - 1]
            if raw in options:
                return raw
            print("输入无效，请重试。")


def run_cli(engine: GameEngine) -> Team:
    human_name = input("输入你的玩家名称（默认你）: ").strip() or "你"
    engine.setup(human_name)
    gen = engine.run()
    pending: InputRequest | None = None
    send_value = ""

    while True:
        try:
            if pending is None:
                pending = next(gen)
            else:
                pending = gen.send(send_value)

            for line in engine.io.logs:
                print(line)
            engine.io.logs.clear()

            if pending.kind == "text":
                send_value = input(f"{pending.prompt}: ").strip()
            elif pending.kind == "continue":
                input(f"{pending.prompt}，按回车继续...")
                send_value = ""
            else:
                assert pending.options is not None
                send_value = CLI().choose_from(pending.prompt, pending.options)
        except StopIteration as end:
            for line in engine.io.logs:
                print(line)
            engine.io.logs.clear()
            winner = end.value
            engine.print_final_result(winner)
            for line in engine.io.logs:
                print(line)
            engine.io.logs.clear()
            return winner
