from __future__ import annotations

from game.config_models import NarrationStyle
from game.roles import Role, Team
from ui.io import IOBase


ROLE_NAME_MAP: dict[Role, str] = {
    Role.WEREWOLF: "狼人",
    Role.SEER: "预言家",
    Role.WITCH: "女巫",
    Role.HUNTER: "猎人",
    Role.GUARD: "守卫",
    Role.VILLAGER: "平民",
}


class Narrator:
    def __init__(self, io: IOBase, style: NarrationStyle = NarrationStyle.STANDARD):
        self.io = io
        self.style = style

    def _s(self, concise: str, standard: str, immersive: str) -> str:
        if self.style == NarrationStyle.CONCISE:
            return concise
        if self.style == NarrationStyle.IMMERSIVE:
            return immersive
        return standard

    def announce_game_start(self, players_count: int) -> None:
        self.io.title("天黑请闭眼")
        self.io.line(self._s(
            "欢迎入局。",
            f"欢迎来到单人狼人杀，本局共 {players_count} 人。",
            f"夜色将至，欢迎各位来到这场 {players_count} 人的推理对决。",
        ))

    def announce_night_start(self, round_no: int) -> None:
        self.io.title(f"第 {round_no} 夜")
        self.io.line(self._s("入夜。", "夜幕降临，所有玩家请闭眼。", "夜幕笼罩村庄，所有玩家请闭眼，保持安静。"))

    def announce_werewolf_phase(self) -> None:
        self.io.line(self._s("狼人行动。", "狼人请睁眼并选择目标。", "狼人请悄然睁眼，确认今夜袭击目标。"))

    def announce_seer_phase(self) -> None:
        self.io.line(self._s("预言家行动。", "预言家请睁眼并查验。", "预言家请睁眼，命运之书将告诉你一人的阵营。"))

    def announce_witch_phase(self) -> None:
        self.io.line(self._s("女巫行动。", "女巫请睁眼，决定是否用药。", "女巫请睁眼，今夜你可选择救赎或审判。"))

    def announce_day_start(self, round_no: int) -> None:
        self.io.title(f"第 {round_no} 天")
        self.io.line(self._s("天亮。", "天亮了，请各位整理信息。", "晨光降临，昨夜的真相即将揭晓。"))

    def announce_deaths(self, dead_players: list[str]) -> None:
        if dead_players:
            self.io.line(self._s(
                f"昨夜死亡：{', '.join(dead_players)}。",
                f"昨夜离场的玩家是：{', '.join(dead_players)}。",
                f"法官宣读昨夜结果：{', '.join(dead_players)} 已倒在夜色中。",
            ))
        else:
            self.io.line(self._s("平安夜。", "昨夜是平安夜，无人死亡。", "昨夜风平浪静，村庄无人离场。"))

    def announce_discussion_order(self, order: list[str], round_no: int) -> None:
        self.io.line(self._s(
            f"第{round_no}轮发言顺序：{' -> '.join(order)}。",
            f"白天第 {round_no} 轮发言开始，顺序为：{' -> '.join(order)}。",
            f"请进入第 {round_no} 轮陈述，发言顺序为：{' -> '.join(order)}。",
        ))

    def announce_player_speaking(self, player_name: str) -> None:
        self.io.line(self._s(f"{player_name} 发言。", f"请 {player_name} 发言。", f"请 {player_name} 正式发言。"))

    def announce_vote_start(self) -> None:
        self.io.line(self._s("开始投票。", "发言结束，现在开始投票。", "讨论阶段结束，请所有存活玩家依次投票。"))

    def announce_tie_and_revote(self, tied: list[str]) -> None:
        self.io.line(self._s(
            f"平票：{', '.join(tied)}。进入补充发言后复投。",
            f"出现平票：{', '.join(tied)}。将进行补充发言并进入复投。",
            f"票型僵持在 {', '.join(tied)}，请补充发言后进行第二次投票。",
        ))

    def announce_vote_result(self, vote_map: dict[str, str], tally: dict[str, int], eliminated: str | None) -> None:
        self.io.line("现在公布投票结果。")
        for voter, target in vote_map.items():
            self.io.line(f"- {voter} 投给了 {target}")
        self.io.line("票数统计：" + "，".join(f"{k}:{v}" for k, v in sorted(tally.items())))
        if eliminated:
            self.io.line(f"被放逐的玩家是：{eliminated}。")
        else:
            self.io.line("本轮无人被放逐。")

    def announce_last_words(self, player_name: str) -> None:
        self.io.line(self._s(f"{player_name} 遗言。", f"请 {player_name} 发表遗言。", f"请 {player_name} 留下最后发言。"))

    def announce_game_over(self, winner: Team, all_roles: dict[str, Role], recap: list[str]) -> None:
        team_name = "好人阵营" if winner == Team.GOOD else "狼人阵营"
        self.io.title("游戏结束")
        self.io.line(f"本局胜利阵营为：{team_name}。")
        self.io.line("全员身份如下：")
        for name, role in all_roles.items():
            self.io.line(f"- {name}：{ROLE_NAME_MAP[role]}")
        self.io.line("关键事件回顾：")
        for item in recap:
            self.io.line(f"- {item}")
