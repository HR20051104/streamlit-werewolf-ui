from __future__ import annotations

import re
import random

from llm.provider import LLMProvider


class MockProvider(LLMProvider):
    _TEMPLATES = [
        "我先点名{suspect}，他这轮的发言和投票方向不太一致，我建议今天重点看他。",
        "我现在主要怀疑{suspect}，尤其在关键问题上有回避倾向，先从他这里盘。",
        "我的票会优先考虑{suspect}，因为他前后立场变化明显，需要给出更完整解释。",
        "目前信息量不算大，但{suspect}的行为最可疑，先把他的逻辑链对齐。",
    ]

    @staticmethod
    def _extract_suspect(prompt: str) -> str:
        match = re.search(r"你当前最怀疑：([^\n。,.，]+)", prompt)
        if match:
            return match.group(1).strip()
        return "该玩家"

    def generate_statement(self, prompt: str) -> str:
        suspect = self._extract_suspect(prompt)
        return random.choice(self._TEMPLATES).format(suspect=suspect)
