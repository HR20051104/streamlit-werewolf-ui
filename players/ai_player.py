from __future__ import annotations

from dataclasses import dataclass
import random
import re

from game.state import GameState, PlayerState
from llm.prompts import last_words_prompt, statement_prompt
from llm.provider import LLMProvider
from players.base_player import BasePlayer
from players.memory import PlayerMemory
from players.personalities import Personality
from players.reasoning import top_suspect, update_suspicion, vote_target


@dataclass(slots=True)
class AIContext:
    personality: Personality
    memory: PlayerMemory


class AIPlayer(BasePlayer):
    def __init__(
        self,
        state: PlayerState,
        context: AIContext,
        llm: LLMProvider | None = None,
        statement_max_chars: int = 80,
        last_words_max_chars: int = 60,
    ):
        super().__init__(state)
        self.context = context
        self.llm = llm
        self.statement_max_chars = statement_max_chars
        self.last_words_max_chars = last_words_max_chars

    @staticmethod
    def _sanitize_output(text: str, max_chars: int | None, fallback: str) -> str:
        cleaned = " ".join((text or "").split())
        if not cleaned:
            cleaned = fallback
        if max_chars is None:
            return cleaned
        if len(cleaned) <= max_chars:
            return cleaned
        # Prefer cutting at sentence boundaries for natural output.
        cut = cleaned[:max_chars]
        last_stop = max(cut.rfind("。"), cut.rfind("！"), cut.rfind("？"), cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
        if last_stop >= max_chars // 2:
            return cut[: last_stop + 1]
        return cut

    @staticmethod
    def _mentions_unspoken_as_silent(text: str, unspoken_players: list[str]) -> bool:
        if not text or not unspoken_players:
            return False
        pattern = r"(沉默|不说话|没发言|没表态|不表态|回避发言|一直不说)"
        for name in unspoken_players:
            if name in text:
                window_pattern = rf"{re.escape(name)}[^。！？\n]{{0,14}}{pattern}|{pattern}[^。！？\n]{{0,14}}{re.escape(name)}"
                if re.search(window_pattern, text):
                    return True
        return False

    def _recent_context(self, game_state: GameState) -> str:
        if not game_state.records:
            return "暂无历史记录。"
        lines: list[str] = []
        for rec in game_state.records[-2:]:
            night_dead = ",".join(rec.night_result.dead_players) if rec.night_result and rec.night_result.dead_players else "无人"
            lines.append(f"第{rec.day}天夜晚死亡：{night_dead}；放逐：{rec.executed or '无人'}。")
            if rec.statements:
                sample = rec.statements[-3:]
                lines.append("最近发言摘录：" + " | ".join([f"{n}:{t}" for n, t in sample]))
            if rec.votes:
                vote_brief = ", ".join([f"{v}->{t}" for v, t in list(rec.votes.items())[-4:]])
                lines.append(f"最近投票：{vote_brief}")
        return "\n".join(lines)[:600]

    def _offline_statement(self, game_state: GameState, suspect: str) -> str:
        day = game_state.day
        voted_for = self.state.last_vote or "暂无"
        if game_state.records:
            last_record = game_state.records[-1]
            vote_cnt = sum(1 for target in last_record.votes.values() if target == suspect)
            executed = last_record.executed or "无人"
            options = [
                f"第{day}天我先给结论，{suspect}最值得盘，他昨天吃了{vote_cnt}票但解释不完整。",
                f"我重点怀疑{suspect}，他前后话术有跳变，和昨天被放逐的{executed}关系也需要再盘。",
                f"我这轮会继续压{suspect}，上一轮我投的是{voted_for}，但现在看{suspect}矛盾更多。",
                f"当前信息里{suspect}的问题最大，先让他把关键时间点和投票理由讲清楚。",
            ]
            return random.choice(options)
        options = [
            f"第{day}天我先点{suspect}，他的表态有点飘，建议先从他开始盘。",
            f"我现在优先怀疑{suspect}，他说法有保留，先听他补完整逻辑。",
            f"我会先看{suspect}，这轮他的站边和语气都比较可疑。",
            f"先给一个方向，{suspect}是我当前第一怀疑位，后续看他回应。",
        ]
        return random.choice(options)

    def speak(
        self,
        game_state: GameState,
        live_context_lines: list[str] | None = None,
        human_name: str | None = None,
        already_spoken: list[str] | None = None,
        not_yet_spoken: list[str] | None = None,
    ) -> str:
        update_suspicion(self.state, game_state)
        suspect = top_suspect(self.state, game_state)
        live_context = ""
        if live_context_lines:
            live_context = "\n".join(live_context_lines[-6:])

        if self.llm:
            prompt = statement_prompt(
                self.state,
                game_state,
                suspect,
                self.statement_max_chars,
                self.context.personality.speaking_style,
                self._recent_context(game_state) + (f"\n本轮最新发言：\n{live_context}" if live_context else ""),
                human_name or "你",
                already_spoken or [],
                not_yet_spoken or [],
            )
            text = self.llm.generate_statement(prompt)
            unspoken = not_yet_spoken or []
            if self._mentions_unspoken_as_silent(text, unspoken):
                retry_prompt = (
                    prompt
                    + "\n再次强调：尚未轮到发言的玩家不能被描述为沉默或回避发言。请重写一段合规发言。"
                )
                text = self.llm.generate_statement(retry_prompt)
                if self._mentions_unspoken_as_silent(text, unspoken):
                    for name in unspoken:
                        text = re.sub(
                            rf"{re.escape(name)}[^。！？\n]{{0,14}}(沉默|不说话|没发言|没表态|不表态|回避发言|一直不说)",
                            f"{name}还没轮到发言",
                            text,
                        )
                        text = re.sub(
                            rf"(沉默|不说话|没发言|没表态|不表态|回避发言|一直不说)[^。！？\n]{{0,14}}{re.escape(name)}",
                            f"{name}还没轮到发言",
                            text,
                        )
        else:
            text = self._offline_statement(game_state, suspect)

        max_chars = None if self.llm else self.statement_max_chars
        statement = self._sanitize_output(text, max_chars, f"我先重点关注{suspect}。")
        self.state.last_statement = statement
        self.context.memory.add(
            day=game_state.day,
            phase="day",
            event_type="statement",
            content={"text": statement, "suspect": suspect},
        )
        return statement

    def vote(self, game_state: GameState) -> str:
        update_suspicion(self.state, game_state)
        target = vote_target(self.state, game_state, self.context.personality.conformity_bias)
        self.state.last_vote = target
        self.context.memory.add(
            day=game_state.day,
            phase="vote",
            event_type="vote",
            content={"target": target},
        )
        return target

    def last_words(
        self,
        game_state: GameState,
        death_context: str = "出局原因未知。",
        strict_no_day_vote_refs: bool = False,
    ) -> str:
        if self.llm:
            prompt = last_words_prompt(
                self.state,
                game_state,
                self.last_words_max_chars,
                self.context.personality.speaking_style,
                self._recent_context(game_state),
                death_context,
                strict_no_day_vote_refs,
            )
            text = self.llm.generate_statement(prompt)
            if strict_no_day_vote_refs:
                forbidden = re.compile(r"(投票|放逐|上一轮|刚才.*票|白天.*票)")
                if forbidden.search(text):
                    retry_prompt = (
                        prompt
                        + "\n再次强调：禁止提及投票、放逐、上一轮等未发生事件，只能基于首夜出局场景说话。"
                    )
                    text = self.llm.generate_statement(retry_prompt)
        else:
            templates = [
                "我这边遗言就一句，别被表面情绪带走，重点看谁一直在顺势推票。",
                "我出局了，后面请把票型连起来看，真正的问题点会更明显。",
                "我希望你们多对比前后立场变化，能突然转向的人更值得警惕。",
                "我没有别的要补充，后面请把发言逻辑和投票结果一起看。",
            ]
            text = random.choice(templates)
        max_chars = None if self.llm else self.last_words_max_chars
        return self._sanitize_output(text, max_chars, "请继续结合票型判断。")
