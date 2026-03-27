from __future__ import annotations

from collections import Counter

from game.roles import Role, Team, ROLE_TEAM_MAP
from game.state import DayRecord, GameState, NightResult
from players.reasoning import seer_check_target, wolf_night_target
from ui.cli import CLI


def run_night(game_state: GameState, cli: CLI, debug: bool = False) -> NightResult:
    game_state.phase = "night"
    result = NightResult()

    wolves = [p for p in game_state.alive_players() if p.role == Role.WEREWOLF]
    if wolves:
        targets = [wolf_night_target(w, game_state) for w in wolves]
        result.wolf_target = Counter(targets).most_common(1)[0][0]

    seers = [p for p in game_state.alive_players() if p.role == Role.SEER]
    for seer in seers:
        target = seer_check_target(seer, game_state)
        alignment = ROLE_TEAM_MAP[game_state.players[target].role]
        checks = seer.private_knowledge.setdefault("seer_checks", {})
        checks[target] = alignment.value
        if seer.is_human:
            cli.line(f"[预言家信息] 你查验了 {target}，其阵营是 {alignment.value}")

    witches = [p for p in game_state.alive_players() if p.role == Role.WITCH]
    for witch in witches:
        if game_state.witch.has_heal and result.wolf_target and witch.is_human:
            save = cli.prompt(f"今晚被刀目标可能是 {result.wolf_target}，你要救吗？(y/n): ").lower() == "y"
            if save:
                result.saved_by_witch = True
                game_state.witch.has_heal = False
        if game_state.witch.has_poison:
            poison_target = None
            if witch.is_human:
                opts = ["不使用"] + [n for n in game_state.alive_names() if n != witch.name]
                choice = cli.choose_from("你要使用毒药吗？", opts)
                poison_target = None if choice == "不使用" else choice
            else:
                # AI 女巫在高怀疑下概率毒人
                suspect = max(witch.suspicion_map, key=lambda n: witch.suspicion_map[n], default=None)
                if suspect and witch.suspicion_map.get(suspect, 0) > 0.75:
                    poison_target = suspect
            if poison_target:
                result.poisoned_target = poison_target
                game_state.witch.has_poison = False

    dead = set()
    if result.wolf_target and not result.saved_by_witch:
        dead.add(result.wolf_target)
    if result.poisoned_target:
        dead.add(result.poisoned_target)

    for name in dead:
        game_state.players[name].alive = False
    result.dead_players = sorted(dead)

    if debug:
        cli.line(
            f"[DEBUG] 夜晚结算: wolf_target={result.wolf_target}, saved={result.saved_by_witch}, poison={result.poisoned_target}"
        )
    return result


def run_day_discussion(game_state: GameState, name_to_controller: dict[str, object], cli: CLI) -> list[tuple[str, str]]:
    game_state.phase = "day"
    statements: list[tuple[str, str]] = []
    for name in game_state.alive_names():
        controller = name_to_controller[name]
        text = controller.speak(game_state)
        game_state.players[name].last_statement = text
        statements.append((name, text))
        cli.line(f"{name}：{text}")
    return statements


def run_vote(game_state: GameState, name_to_controller: dict[str, object], cli: CLI) -> tuple[dict[str, str], str | None]:
    game_state.phase = "vote"
    votes: dict[str, str] = {}
    for name in game_state.alive_names():
        controller = name_to_controller[name]
        target = controller.vote(game_state)
        votes[name] = target
        game_state.players[name].last_vote = target
        cli.line(f"{name} 的投票对象是：{target}")

    cnt = Counter(votes.values())
    if not cnt:
        return votes, None
    top_votes = cnt.most_common()
    highest = top_votes[0][1]
    tied = [n for n, v in top_votes if v == highest]
    executed = sorted(tied)[0]

    game_state.players[executed].alive = False
    cli.line(f"被放逐的玩家是：{executed}（{highest}票）")
    return votes, executed


def add_day_record(
    game_state: GameState,
    night_result: NightResult,
    statements: list[tuple[str, str]],
    votes: dict[str, str],
    executed: str | None,
) -> None:
    rec = DayRecord(
        day=game_state.day,
        night_result=night_result,
        statements=statements,
        votes=votes,
        executed=executed,
    )
    game_state.records.append(rec)
