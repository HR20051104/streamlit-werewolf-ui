from __future__ import annotations

import streamlit as st

from game.config_models import GameConfig, NarrationStyle, TieBreakPolicy, VoteRuleConfig
from game.engine import GameEngine
from game.roles import Role
from ui.io import IOBase, InputRequest
from utils.config import load_config


st.set_page_config(page_title="单人狼人杀", layout="wide")


class StreamlitIO(IOBase):
    pass


def _render_player_roster(engine: GameEngine) -> None:
    alive = [p.name for p in engine.game_state.alive_players()]
    all_names = list(engine.game_state.players.keys())
    dead = [name for name in all_names if name not in alive]
    st.subheader("玩家列表")
    st.write(f"存活（{len(alive)}）：" + ("、".join(alive) if alive else "无"))
    st.write(f"出局（{len(dead)}）：" + ("、".join(dead) if dead else "无"))


def _build_config() -> tuple[GameConfig, bool, str]:
    base = load_config()
    base_human_role = getattr(base, "human_role", "random")
    with st.sidebar:
        st.header("开局配置")
        human_name = st.text_input("你的名字", value="你")
        total_players = st.slider("TOTAL_PLAYERS", 6, 12, base.total_players)
        use_llm = st.toggle("USE_LLM", value=base.use_llm)
        provider = st.selectbox("LLM_PROVIDER", ["deepseek", "mock"], index=0 if base.provider == "deepseek" else 1)
        deepseek_model = st.text_input("DEEPSEEK_MODEL", value=base.deepseek_model)
        style = st.selectbox(
            "NARRATION_STYLE",
            ["concise", "standard", "immersive"],
            index=["concise", "standard", "immersive"].index(base.narration_style.value),
        )
        discussion_rounds = st.selectbox("DISCUSSION_ROUNDS", [1, 2], index=0 if base.discussion_rounds == 1 else 1)
        human_role = st.selectbox(
            "HUMAN_ROLE",
            ["random", "seer", "werewolf", "witch", "guard", "hunter", "villager"],
            index=["random", "seer", "werewolf", "witch", "guard", "hunter", "villager"].index(base_human_role),
            help="调试用：指定你本局身份。random 为随机。",
        )
        ai_statement_max_chars = st.slider("AI_STATEMENT_MAX_CHARS", 20, 400, base.ai_statement_max_chars)
        ai_last_words_max_chars = st.slider("AI_LAST_WORDS_MAX_CHARS", 20, 300, base.ai_last_words_max_chars)
        step_by_step = st.toggle("STEP_BY_STEP", value=base.step_by_step)
        tie_policy = st.selectbox(
            "FINAL_TIE_POLICY",
            ["no_elimination", "random"],
            index=0 if base.vote_rules.final_tie_policy.value == "no_elimination" else 1,
        )
        start = st.button("开始新对局")
    config_kwargs = dict(
        total_players=total_players,
        human_players=base.human_players,
        use_llm=use_llm,
        provider=provider,
        deepseek_api_key=base.deepseek_api_key,
        deepseek_base_url=base.deepseek_base_url,
        deepseek_model=deepseek_model,
        max_rounds=base.max_rounds,
        discussion_rounds=discussion_rounds,
        narration_style=NarrationStyle(style),
        vote_rules=VoteRuleConfig(
            revote_on_tie=base.vote_rules.revote_on_tie,
            revote_discussion_rounds=base.vote_rules.revote_discussion_rounds,
            final_tie_policy=TieBreakPolicy(tie_policy),
        ),
        ai_statement_max_chars=ai_statement_max_chars,
        ai_last_words_max_chars=ai_last_words_max_chars,
        step_by_step=step_by_step,
        force_human_werewolf=base.force_human_werewolf,
        enable_guard=base.enable_guard,
        debug=base.debug,
    )
    if hasattr(base, "human_role"):
        config_kwargs["human_role"] = human_role
    config = GameConfig(**config_kwargs)
    return config, start, human_name or "你"


def _init_session() -> None:
    for key, value in {
        "engine": None,
        "game_gen": None,
        "pending": None,
        "winner": None,
        "started": False,
    }.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _advance(response: str | None = None) -> None:
    gen = st.session_state["game_gen"]
    pending = st.session_state["pending"]
    while True:
        try:
            if pending is None:
                req = next(gen)
            else:
                if response is None:
                    return
                req = gen.send(response)
                response = None
            st.session_state["pending"] = req
            return
        except StopIteration as end:
            st.session_state["winner"] = end.value
            st.session_state["pending"] = None
            return


def _render_pending(pending: InputRequest) -> None:
    if pending.kind == "continue":
        st.info(pending.prompt)
        if st.button("下一步"):
            _advance("")
            st.rerun()
        return

    st.write(pending.prompt)
    if pending.kind == "text":
        text = st.text_area("输入", key=f"pending_text_{pending.prompt}")
        if st.button("提交输入"):
            _advance(text)
            st.rerun()
        return

    choice = st.selectbox("请选择", pending.options or [], key=f"pending_choice_{pending.prompt}")
    if st.button("提交选择"):
        _advance(choice)
        st.rerun()


def main() -> None:
    st.title("单人狼人杀 Web UI")
    _init_session()
    config, start, human_name = _build_config()

    if start:
        io = StreamlitIO()
        engine = GameEngine(config, io)
        engine.setup(human_name)
        st.session_state["engine"] = engine
        st.session_state["game_gen"] = engine.run()
        st.session_state["pending"] = None
        st.session_state["winner"] = None
        st.session_state["started"] = True
        _advance()

    engine: GameEngine | None = st.session_state["engine"]
    if not st.session_state["started"] or engine is None:
        st.info("请在左侧完成配置后点击“开始新对局”。")
        return

    left, mid, right = st.columns([2.2, 1.3, 1.5])

    with left:
        st.subheader("对局日志区")
        with st.container(height=560, border=True):
            for line in engine.io.logs:
                st.markdown(line)

    pending: InputRequest | None = st.session_state["pending"]
    human = engine.game_state.players.get(engine.human_name)

    with mid:
        st.subheader("当前交互区")
        if st.session_state["winner"] is None and pending is not None:
            _render_pending(pending)
        elif st.session_state["winner"] is not None:
            st.success("对局已结束。")

    with right:
        _render_player_roster(engine)
        st.markdown("---")
        st.subheader("私密信息区")
        for item in engine.get_human_private_view():
            st.write(item)

        if (
            human
            and human.role == Role.WEREWOLF
            and human.alive
            and engine.game_state.phase == "night"
        ):
            st.markdown("---")
            st.caption("狼人频道（仅狼人可见）")
            teammates = human.private_knowledge.get("wolf_teammates", [])
            st.write("队友名单：" + (", ".join(teammates) if teammates else "无（独狼）"))
            if pending and "狼人频道" in pending.prompt:
                st.warning("请在“当前交互区”完成狼人密聊与刀人操作。")

    if st.session_state["winner"] is not None:
        engine.print_final_result(st.session_state["winner"])
        st.subheader("结算")
        st.write(f"胜负：{st.session_state['winner'].value}")
        st.write("全员身份：")
        for name, player in engine.game_state.players.items():
            st.write(f"- {name}: {player.role.value}")
        st.write("每日简要回顾：")
        for line in engine._build_recap():
            st.write(f"- {line}")


if __name__ == "__main__":
    main()
