from __future__ import annotations

from llm.provider import LLMProvider


class DeepSeekProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, base_url: str):
        try:
            from openai import OpenAI  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError("启用 DeepSeek 模式需要先安装 openai 包") from exc

        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate_statement(self, prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0.9,
            messages=[
                {"role": "system", "content": "你是狼人杀玩家，请自然对话，语气真实，忠于身份目标。"},
                {"role": "user", "content": prompt},
            ],
        )
        return (resp.choices[0].message.content or "").strip()
