from __future__ import annotations

from game.state import GameState, PlayerState


def statement_prompt(
    player: PlayerState,
    game_state: GameState,
    suspect: str,
    max_chars: int,
    speaking_style: str,
    recent_context: str,
    human_name: str,
    already_spoken: list[str],
    not_yet_spoken: list[str],
) -> str:
    alive = ",".join(game_state.alive_names())
    spoken_text = "、".join(already_spoken) if already_spoken else "（暂无）"
    not_yet_text = "、".join(not_yet_spoken) if not_yet_spoken else "（无）"
    return (
        f"你是{player.name}，身份{player.role.value}。\n"
        f"人类玩家名字是：{human_name}。\n"
        f"你的发言风格：{speaking_style}\n"
        f"今天是第{game_state.day}天白天讨论环节，存活玩家：{alive}。\n"
        f"你当前最怀疑：{suspect}。\n"
        f"本轮已发言玩家：{spoken_text}\n"
        f"本轮尚未发言玩家：{not_yet_text}\n"
        f"最近对局信息（可参考）：\n{recent_context}\n"
        "请像真人玩家一样自然说话，允许自由发挥，不要套模板。\n"
        "“本轮最新发言”里每行格式是“名字：内容”，请按名字准确引用，不要把玩家说话归给别人。\n"
        "严禁把“本轮尚未发言玩家”说成沉默寡言、回避发言或不表态，他们只是还没轮到。\n"
        "可以引用上文信息、票型、他人发言进行回应，尤其要回应人类玩家刚刚的关键观点。\n"
        "不要使用分点标题、不要出现程序术语。"
    )


def last_words_prompt(
    player: PlayerState,
    game_state: GameState,
    max_chars: int,
    speaking_style: str,
    recent_context: str,
    death_context: str,
    strict_no_day_vote_refs: bool,
) -> str:
    alive = ",".join(game_state.alive_names())
    extra_rule = ""
    if strict_no_day_vote_refs:
        extra_rule = "你是首夜出局，禁止提及“白天投票”“刚才放逐”“上一轮投票”等未发生事件。"
    return (
        f"你是{player.name}，身份{player.role.value}，已经出局，需要发表遗言。\n"
        f"你的发言风格：{speaking_style}\n"
        f"出局背景：{death_context}\n"
        f"当前仍存活玩家：{alive}。\n"
        f"最近对局信息（可参考）：\n{recent_context}\n"
        "请像真人临场说遗言一样自然表达，可以给出提醒、怀疑和站边。\n"
        "允许自由发挥，不要套模板，不要出现程序术语，不要分点。\n"
        f"{extra_rule}"
    )
