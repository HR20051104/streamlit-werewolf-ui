# 单人狼人杀 AI（Python + Streamlit）

这是一个「1 名人类 + N 名 AI」的单人狼人杀项目，支持 **CLI** 与 **Streamlit UI** 双入口。当前版本重点增强了可玩性：夜晚信息更可控、关键节点可分步推进、神职可交互、日志与私密信息展示更清晰。

## 功能清单（本版本）

- 6~12 人对局，人数自动匹配角色池。
- 新增并启用守卫（可通过配置开关关闭）。
- 夜晚完整流程：守卫 → 狼人 → 预言家 → 女巫 → 结算。
- 人类狼人夜间可用“狼人频道”：
  - 查看狼队友
  - 发送密聊（可留空）
  - 接收 AI 队友简短回复
  - 选择刀人目标
- 人类预言家可手动选择查验目标，结果仅私密显示。
- 人类女巫可交互决定救/毒；解药与毒药全局一次性。
- 分步推进（默认开启）：
  - 夜晚开始、各神职阶段结束、夜晚结算
  - 每个玩家发言后
  - 每个玩家投票后
  - 放逐结算后、遗言后
- 平票体验优化：平票候选展示、补充讨论、限定候选复投、最终策略可配置（随机放逐/无人出局）。
- AI 输出治理：
  - 离线 mock 不再回显 prompt
  - LLM 输出统一清洗（去空白、长度限制、空文本兜底）
- 对局结束展示：胜负、全员身份、每日简要回顾（夜死/放逐/高票）。

## 目录结构

```text
.
├── main.py
├── game/
│   ├── config_models.py
│   ├── engine.py
│   ├── narrator.py
│   ├── roles.py
│   ├── rules.py
│   ├── state.py
│   └── win_check.py
├── players/
├── ui/
│   ├── cli.py
│   ├── io.py
│   └── streamlit_app.py
├── utils/
│   └── config.py
└── .env.example
```

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install streamlit
```

## 运行方式

### CLI

```bash
python main.py --mode cli --players 8 --discussion-rounds 2 --step-by-step true
```

### UI（Streamlit）

```bash
python main.py --mode ui
# 或
streamlit run ui/streamlit_app.py
```

## 配置说明（`.env`）

核心字段（统一命名）：

- `TOTAL_PLAYERS`：总人数（6~12）
- `DISCUSSION_ROUNDS`：白天发言轮次（1~2）
- `AI_STATEMENT_MAX_CHARS`：AI 普通发言最大长度
- `AI_LAST_WORDS_MAX_CHARS`：AI 遗言最大长度
- `STEP_BY_STEP`：是否分步推进（默认 `true`）
- `FORCE_HUMAN_WEREWOLF`：强制人类为狼人（测试用）
- `ENABLE_GUARD`：是否启用守卫角色
- `FINAL_TIE_POLICY`：平票最终策略（`no_elimination` / `random`）
- `USE_LLM`、`LLM_PROVIDER`、`DEEPSEEK_*`：模型调用配置

请参考 `.env.example`，不要提交真实 API Key。

## 角色与规则说明（简版）

- **狼人**：夜晚共识刀人；人类狼人可使用狼人频道。
- **预言家**：夜晚查验一人阵营，结果仅自己可见。
- **女巫**：
  - 解药 1 瓶（可在得知刀口后决定是否救）
  - 毒药 1 瓶（可选择是否毒及目标）
  - 两瓶药均为全局一次性
- **守卫**：夜晚守护 1 人，被守护者若被狼人刀则免死。
- **平票**：先补充讨论+复投（限定候选）；最终仍平票按配置处理。

## 最小手工验收清单

1. 随机/强制为狼人时，夜晚能看到狼人频道并可刀人。
2. 人类预言家可手选查验，私密区可见查验结果。
3. 人类女巫可救/毒，且药剂使用后不可重复。
4. 守卫守中刀口时，被刀目标存活且日志可追踪。
5. 开启 `STEP_BY_STEP=true` 时，不会一次性刷完整局。

## 已知限制

- 仍为单人 + AI 的本地对局，不包含联网房间与多真人联机。
- 狼人频道当前为人类狼人单向交互，不是多智能体完整协商。
- 回放为文本摘要，尚未提供结构化回放文件。
