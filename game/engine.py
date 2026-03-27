from __future__ import annotations

from collections import Counter
from collections.abc import Generator
import random

from game.config_models import GameConfig
from game.narrator import Narrator
from game.roles import ROLE_TEAM_MAP, Role, Team
from game.rules import VoteResolution, build_role_pool, resolve_vote
from game.state import DayRecord, GameState, NightResult, PlayerState
from game.win_check import check_winner
from llm.mock_provider import MockProvider
from llm.provider import LLMProvider
from players.ai_player import AIContext, AIPlayer
from players.base_player import BasePlayer
from players.memory import PlayerMemory
from players.personalities import random_personality
from players.reasoning import (
    guard_protect_target,
    init_suspicion,
    seer_check_target,
    wolf_night_target,
)
from ui.io import IOBase, InputRequest

AI_NAMES = ["阿北", "小Q", "林克", "橙子", "白夜", "K", "乌鸦", "南风", "弧光", "Echo", "Milo"]


class GameEngine:
    def __init__(self, config: GameConfig, io: IOBase):
        config.validate()
        self.config = config
        self.io = io
        self.narrator = Narrator(io, config.narration_style)
        self.game_state = GameState()
        self.controllers: dict[str, BasePlayer] = {}
        self.human_name: str = "你"
        self.llm: LLMProvider | None = self._build_llm_provider(config)

    def _build_llm_provider(self, config: GameConfig) -> LLMProvider | None:
        if not config.use_llm:
            return None
        if config.provider == "deepseek" and config.deepseek_api_key:
            from llm.deepseek_provider import DeepSeekProvider

            return DeepSeekProvider(
                api_key=config.deepseek_api_key,
                model=config.deepseek_model,
                base_url=config.deepseek_base_url or "https://api.deepseek.com",
            )
        return MockProvider()

    def setup(self, human_name: str) -> None:
        self.human_name = human_name.strip() or "你"
        role_pool = build_role_pool(self.config.total_players)
        if not self.config.enable_guard:
            role_pool = [Role.VILLAGER if role == Role.GUARD else role for role in role_pool]
        random.shuffle(role_pool)
        names = [self.human_name] + AI_NAMES[: self.config.total_players - 1]

        forced_role_applied = False
        if self.config.human_role != "random":
            target_role = Role(self.config.human_role)
            if target_role in role_pool and role_pool[0] != target_role:
                role_idx = role_pool.index(target_role)
                role_pool[0], role_pool[role_idx] = role_pool[role_idx], role_pool[0]
                forced_role_applied = True
            elif target_role in role_pool and role_pool[0] == target_role:
                forced_role_applied = True
            elif target_role not in role_pool:
                self.io.line(
                    f"[提示] 本局人数配置下没有角色 {self.config.human_role}，已回退为随机身份。"
                )

        if self.config.force_human_werewolf and Role.WEREWOLF in role_pool and role_pool[0] != Role.WEREWOLF:
            wolf_idx = role_pool.index(Role.WEREWOLF)
            role_pool[0], role_pool[wolf_idx] = role_pool[wolf_idx], role_pool[0]

        for idx, name in enumerate(names):
            role = role_pool[idx]
            self.game_state.players[name] = PlayerState(name=name, role=role, is_human=(idx == 0))

        wolves = [p.name for p in self.game_state.players.values() if p.role == Role.WEREWOLF]
        for p in self.game_state.players.values():
            if p.role == Role.WEREWOLF:
                p.private_knowledge["wolf_teammates"] = [n for n in wolves if n != p.name]
            init_suspicion(p, self.game_state)
            if not p.is_human:
                self.controllers[p.name] = AIPlayer(
                    p,
                    AIContext(personality=random_personality(), memory=PlayerMemory()),
                    self.llm,
                    statement_max_chars=self.config.ai_statement_max_chars,
                    last_words_max_chars=self.config.ai_last_words_max_chars,
                )

        self.narrator.announce_game_start(self.config.total_players)
        self.io.line(f"你的身份是：{self.game_state.players[self.human_name].role.value}")
        if self.config.human_role != "random" and forced_role_applied:
            self.io.line(f"[调试] 已按配置固定你的身份为：{self.config.human_role}")

    def _input_text(self, prompt: str) -> Generator[InputRequest, str, str]:
        response = yield InputRequest(kind="text", prompt=prompt)
        return response.strip()

    def _input_choice(self, prompt: str, options: list[str]) -> Generator[InputRequest, str, str]:
        response = yield InputRequest(kind="choice", prompt=prompt, options=options)
        if response in options:
            return response
        if response.isdigit() and 1 <= int(response) <= len(options):
            return options[int(response) - 1]
        return options[0]

    def _pause(self, checkpoint: str) -> Generator[InputRequest, str, None]:
        if self.config.step_by_step:
            _ = yield InputRequest(kind="continue", prompt=f"{checkpoint}（下一步）")

    def _clean_llm_text(self, text: str, fallback: str, max_chars: int | None = 80) -> str:
        cleaned = " ".join((text or "").split())
        if not cleaned:
            cleaned = fallback
        if max_chars is None:
            return cleaned
        return cleaned[:max_chars]

    def _wolf_chat_reply(self, wolf_name: str, user_msg: str) -> str:
        fallback = random.choice(
            [
                "收到，我会配合你的节奏，先看白天票型再决定发言力度。",
                "明白，今晚按这个方向走，白天我会尽量帮你拉票。",
                "可以，我会控一下发言强度，避免太早暴露狼人视角。",
            ]
        )
        if not self.llm:
            return fallback
        prompt = (
            f"你是狼人队友（{wolf_name}的同伴）。\n"
            f"队友消息：{user_msg or '（无）'}\n"
            "请像真实队友一样自然回复，可以简短，也可以稍微展开，重点是对当前局势有帮助。"
        )
        text = self.llm.generate_statement(prompt)
        return self._clean_llm_text(text, fallback, max_chars=None)

    def _run_night(self) -> Generator[InputRequest, str, NightResult]:
        self.game_state.phase = "night"
        result = NightResult()
        self.narrator.announce_night_start(self.game_state.day)
        yield from self._pause("夜晚开始")

        self.io.line("守卫请行动，选择一名守护目标。")
        guards = [p for p in self.game_state.alive_players() if p.role == Role.GUARD]
        for guard in guards:
            choices = [n for n in self.game_state.alive_names() if n != guard.name]
            last = self.game_state.guard.last_protected
            if last in choices and len(choices) > 1:
                choices = [n for n in choices if n != last]
            if guard.is_human:
                protected = yield from self._input_choice("你要守护谁？", choices)
            else:
                protected = guard_protect_target(guard, self.game_state)
                if protected not in choices:
                    protected = random.choice(choices)
            result.protected_target = protected
            self.game_state.guard.last_protected = protected
            guard.private_knowledge[f"night_{self.game_state.day}_guard"] = protected

        self.narrator.announce_werewolf_phase()
        wolves = [p for p in self.game_state.alive_players() if p.role == Role.WEREWOLF]
        if wolves:
            human_wolf = next((w for w in wolves if w.is_human), None)
            if human_wolf:
                teammates = human_wolf.private_knowledge.get("wolf_teammates", [])
                self.io.line(f"【狼人频道】你的队友：{', '.join(teammates) if teammates else '无（独狼）'}")
                msg = yield from self._input_text("【狼人频道】发送一条密聊（可留空）")
                if msg:
                    result.wolf_chat.append((human_wolf.name, msg))
                    self.io.line(f"【狼人频道】你：{msg}")
                reply = self._wolf_chat_reply(human_wolf.name, msg)
                result.wolf_ai_reply = reply
                result.wolf_chat.append(("AI队友", reply))
                self.io.line(f"【狼人频道】AI队友：{reply}")
                yield from self._pause("狼人队友已回复")
                target_options = [n for n in self.game_state.alive_names() if n != human_wolf.name and n not in teammates]
                if target_options:
                    result.wolf_target = yield from self._input_choice("【狼人频道】选择当夜刀人目标", target_options)
            if result.wolf_target is None:
                targets = [wolf_night_target(w, self.game_state) for w in wolves]
                result.wolf_target = Counter(targets).most_common(1)[0][0]

            # Debug-friendly safeguard: when user explicitly selected a role, avoid
            # immediate first-night elimination of the human player.
            if (
                self.config.human_role != "random"
                and self.game_state.day == 1
                and result.wolf_target == self.human_name
            ):
                wolf_names = {w.name for w in wolves}
                alternatives = [
                    n for n in self.game_state.alive_names() if n != self.human_name and n not in wolf_names
                ]
                if alternatives:
                    result.wolf_target = random.choice(alternatives)
                    self.io.line("[调试] 首夜保护已触发：你不会在第1夜被狼人直接刀死。")

        yield from self._pause("狼人阶段结束")

        self.narrator.announce_seer_phase()
        seers = [p for p in self.game_state.alive_players() if p.role == Role.SEER]
        for seer in seers:
            if seer.is_human:
                checked = set(seer.private_knowledge.get("seer_checks", {}).keys())
                options = [n for n in self.game_state.alive_names() if n != seer.name and n not in checked]
                if not options:
                    options = [n for n in self.game_state.alive_names() if n != seer.name]
                target = yield from self._input_choice("你要查验谁？", options)
            else:
                target = seer_check_target(seer, self.game_state)
            alignment = ROLE_TEAM_MAP[self.game_state.players[target].role]
            checks = seer.private_knowledge.setdefault("seer_checks", {})
            checks[target] = alignment.value
            if seer.is_human:
                self.io.line(f"【查验结果（私密）】{target} 的阵营是 {alignment.value}。")

        yield from self._pause("预言家阶段结束")

        self.narrator.announce_witch_phase()
        witches = [p for p in self.game_state.alive_players() if p.role == Role.WITCH]
        for witch in witches:
            if witch.is_human and self.game_state.witch.has_heal and result.wolf_target:
                save = yield from self._input_choice(
                    f"今晚刀口是 {result.wolf_target}，是否使用解药？", ["否", "是"]
                )
                if save == "是":
                    result.saved_by_witch = True
                    self.game_state.witch.has_heal = False

            if self.game_state.witch.has_poison:
                poison_target = None
                if witch.is_human:
                    opts = ["不使用"] + [n for n in self.game_state.alive_names() if n != witch.name]
                    choice = yield from self._input_choice("你是否使用毒药？", opts)
                    poison_target = None if choice == "不使用" else choice
                else:
                    alive_candidates = [n for n in self.game_state.alive_names() if n != witch.name]
                    suspect = (
                        max(alive_candidates, key=lambda n: witch.suspicion_map.get(n, 0.5))
                        if alive_candidates
                        else None
                    )
                    if suspect and witch.suspicion_map.get(suspect, 0.0) > 0.75:
                        poison_target = suspect
                if poison_target:
                    result.poisoned_target = poison_target
                    self.game_state.witch.has_poison = False

        yield from self._pause("女巫阶段结束")

        result.blocked_by_guard = bool(
            result.wolf_target and result.protected_target and result.wolf_target == result.protected_target
        )
        dead = set()
        if (
            result.wolf_target
            and self.game_state.players.get(result.wolf_target)
            and self.game_state.players[result.wolf_target].alive
            and not result.saved_by_witch
            and not result.blocked_by_guard
        ):
            dead.add(result.wolf_target)
        if (
            result.poisoned_target
            and self.game_state.players.get(result.poisoned_target)
            and self.game_state.players[result.poisoned_target].alive
        ):
            dead.add(result.poisoned_target)
        for name in dead:
            self.game_state.players[name].alive = False
        result.dead_players = sorted(dead)

        if result.blocked_by_guard:
            self.io.line(f"夜晚结算：{result.wolf_target} 被守卫守护，狼人刀口未生效。")
        if result.saved_by_witch and result.wolf_target:
            self.io.line(f"夜晚结算：女巫对 {result.wolf_target} 使用了解药。")
        if result.poisoned_target:
            self.io.line(f"夜晚结算：女巫毒杀了 {result.poisoned_target}。")

        yield from self._pause("夜晚结算")
        return result

    def _run_discussion(
        self, rounds: int, only_candidates: list[str] | None = None
    ) -> Generator[InputRequest, str, list[tuple[str, str]]]:
        base_order = [n for n in self.game_state.alive_names() if only_candidates is None or n in only_candidates]
        all_statements: list[tuple[str, str]] = []
        for r in range(1, rounds + 1):
            if not base_order:
                break
            # Rotate start speaker each round/day to avoid always human-first.
            offset = (self.game_state.day + r - 2) % len(base_order)
            order = base_order[offset:] + base_order[:offset]
            self.narrator.announce_discussion_order(order, r)
            for name in order:
                self.narrator.announce_player_speaking(name)
                if name == self.human_name:
                    text = yield from self._input_text(f"{name}，请发言")
                    text = text or "我先听大家发言。"
                else:
                    live_context_lines = [f"{speaker}：{content}" for speaker, content in all_statements]
                    already_spoken = [speaker for speaker, _ in all_statements]
                    not_yet_spoken = [n for n in order if n != name and n not in already_spoken]
                    text = self.controllers[name].speak(
                        self.game_state,
                        live_context_lines=live_context_lines,
                        human_name=self.human_name,
                        already_spoken=already_spoken,
                        not_yet_spoken=not_yet_spoken,
                    )
                self.game_state.players[name].last_statement = text
                all_statements.append((name, text))
                self.io.line(f"{name}：{text}")
                yield from self._pause(f"{name} 发言后")
        return all_statements

    def _collect_votes(self, candidates: list[str] | None = None) -> Generator[InputRequest, str, dict[str, str]]:
        votes: dict[str, str] = {}
        alive = self.game_state.alive_names()
        for name in alive:
            options = [n for n in alive if n != name]
            if candidates is not None:
                options = [o for o in options if o in candidates]
            if name == self.human_name:
                target = yield from self._input_choice(f"{name}，请选择投票对象", options)
            else:
                target = self.controllers[name].vote(self.game_state)
                if target not in options:
                    target = random.choice(options)
            votes[name] = target
            self.game_state.players[name].last_vote = target
            self.io.line(f"投票：{name} -> {target}")
            yield from self._pause(f"{name} 投票后")
        return votes

    def _run_vote(self) -> Generator[InputRequest, str, tuple[VoteResolution, dict[str, str]]]:
        self.narrator.announce_vote_start()
        votes = yield from self._collect_votes()
        resolution = resolve_vote(votes, self.config.vote_rules)
        if resolution.is_tie and self.config.vote_rules.revote_on_tie:
            self.narrator.announce_tie_and_revote(resolution.tied_candidates)
            _ = yield from self._run_discussion(self.config.vote_rules.revote_discussion_rounds, resolution.tied_candidates)
            votes = yield from self._collect_votes(candidates=resolution.tied_candidates)
            resolution = resolve_vote(votes, self.config.vote_rules)
        self.narrator.announce_vote_result(votes, resolution.tally, resolution.eliminated)
        yield from self._pause("放逐结算后")
        return resolution, votes

    def _run_last_words(self, players: list[str], death_contexts: dict[str, str] | None = None) -> Generator[InputRequest, str, None]:
        death_contexts = death_contexts or {}
        for name in players:
            if name in self.game_state.players:
                role_value = self.game_state.players[name].role.value
                self.io.line(f"【身份公开】{name} 的身份是：{role_value}")
            self.narrator.announce_last_words(name)
            if name == self.human_name:
                words = yield from self._input_text(f"{name}，请输入遗言")
                words = words or "请继续观察票型与发言。"
            else:
                context = death_contexts.get(name, "出局原因未知。")
                strict = self.game_state.day == 1 and "夜晚" in context
                words = self.controllers[name].last_words(
                    self.game_state,
                    death_context=context,
                    strict_no_day_vote_refs=strict,
                )
            self.io.line(f"{name} 的遗言：{words}")
            yield from self._pause("遗言后")

    def _build_recap(self) -> list[str]:
        recap: list[str] = []
        for record in self.game_state.records:
            night_dead = record.night_result.dead_players if record.night_result else []
            recap.append(f"第{record.day}天：夜晚死亡 {','.join(night_dead) if night_dead else '无人'}")
            if record.tie_candidates:
                recap.append(f"第{record.day}天：平票候选 {', '.join(record.tie_candidates)}")
            recap.append(f"第{record.day}天：放逐 {record.executed or '无人'}")
            if record.vote_tally:
                high = max(record.vote_tally.items(), key=lambda x: x[1])
                recap.append(f"第{record.day}天：高票 {high[0]}({high[1]}票)")
        return recap

    def get_human_private_view(self) -> list[str]:
        human = self.game_state.players.get(self.human_name)
        if not human:
            return []
        lines = [f"你的身份：{human.role.value}"]
        if human.role == Role.WEREWOLF:
            mates = human.private_knowledge.get("wolf_teammates", [])
            lines.append(f"狼人队友：{', '.join(mates) if mates else '无（独狼）'}")
            if self.game_state.records and self.game_state.records[-1].night_result:
                nr = self.game_state.records[-1].night_result
                if nr.wolf_chat:
                    lines.append("最近狼人夜聊：")
                    lines.extend([f"- {speaker}: {msg}" for speaker, msg in nr.wolf_chat])
        if human.role == Role.SEER:
            checks = human.private_knowledge.get("seer_checks", {})
            if checks:
                lines.append("查验结果（私密）：")
                lines.extend([f"- {name}: {team}" for name, team in checks.items()])
        if human.role == Role.GUARD:
            protected = human.private_knowledge.get(f"night_{self.game_state.day}_guard")
            if protected:
                lines.append(f"今晚守护目标（私密）：{protected}")
        if human.role == Role.WITCH:
            lines.append(f"药剂状态：解药={'有' if self.game_state.witch.has_heal else '无'}，毒药={'有' if self.game_state.witch.has_poison else '无'}")
        return lines

    def run(self) -> Generator[InputRequest, str, Team]:
        while self.game_state.day <= self.config.max_rounds:
            night_result = yield from self._run_night()
            self.narrator.announce_day_start(self.game_state.day)
            self.narrator.announce_deaths(night_result.dead_players)
            night_death_contexts: dict[str, str] = {}
            for name in night_result.dead_players:
                if name == night_result.wolf_target and name == night_result.poisoned_target:
                    night_death_contexts[name] = f"第{self.game_state.day}天夜晚出局（狼人刀口+女巫毒药）。"
                elif name == night_result.wolf_target:
                    night_death_contexts[name] = f"第{self.game_state.day}天夜晚出局（狼人刀口）。"
                elif name == night_result.poisoned_target:
                    night_death_contexts[name] = f"第{self.game_state.day}天夜晚出局（女巫毒药）。"
                else:
                    night_death_contexts[name] = f"第{self.game_state.day}天夜晚出局。"
            yield from self._run_last_words(night_result.dead_players, death_contexts=night_death_contexts)

            winner = check_winner(self.game_state)
            if winner:
                return winner

            self.game_state.phase = "day"
            statements = yield from self._run_discussion(self.config.discussion_rounds)
            self.game_state.phase = "vote"
            resolution, votes = yield from self._run_vote()

            if resolution.eliminated:
                self.game_state.players[resolution.eliminated].alive = False
                yield from self._run_last_words(
                    [resolution.eliminated],
                    death_contexts={resolution.eliminated: f"第{self.game_state.day}天白天被放逐出局。"},
                )

            self.game_state.records.append(
                DayRecord(
                    day=self.game_state.day,
                    night_result=night_result,
                    statements=statements,
                    votes=votes,
                    vote_tally=resolution.tally,
                    tie_candidates=resolution.tied_candidates,
                    executed=resolution.eliminated,
                )
            )

            winner = check_winner(self.game_state)
            if winner:
                return winner
            self.game_state.day += 1

        return Team.WOLF

    def print_final_result(self, winner: Team) -> None:
        all_roles = {p.name: p.role for p in self.game_state.players.values()}
        self.narrator.announce_game_over(winner, all_roles, self._build_recap())
