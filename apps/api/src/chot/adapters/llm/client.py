"""Client LLM tối giản theo chuẩn OpenAI Chat Completions.

Dùng được với: OpenAI, Gemini (OpenAI-compatible endpoint), OpenRouter, Groq, và model tự host
qua vLLM / Ollama (Qwen, Gemma). Đổi nhà cung cấp = đổi LLM_BASE_URL + LLM_MODEL trong .env.
"""

from __future__ import annotations

import threading
from typing import Any, Protocol


class LLMClient(Protocol):
    def complete_json(self, prompt: str, schema: dict[str, Any] | None) -> str: ...


class OpenAICompatibleClient:
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.0,
        timeout: float = 120.0,
    ) -> None:
        from openai import OpenAI  # import trễ để test không cần SDK

        self.model = model
        self.temperature = temperature
        self._client = OpenAI(api_key=api_key or "not-needed", base_url=base_url, timeout=timeout)
        # cộng dồn để tính chi phí
        self.usage = dict.fromkeys(("calls", "prompt_tokens", "completion_tokens"), 0)
        self._lock = threading.Lock()

    def complete_json(self, prompt: str, schema: dict[str, Any] | None) -> str:
        if schema is not None:
            response_format: dict[str, Any] = {
                "type": "json_schema",
                "json_schema": {"name": "chot_output", "schema": schema, "strict": True},
            }
        else:
            response_format = {"type": "json_object"}
        resp = self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            response_format=response_format,
            messages=[{"role": "user", "content": prompt}],
        )
        with self._lock:  # các đoạn gọi song song (M3)
            self.usage["calls"] += 1
            if resp.usage:  # vài server tự host không trả usage
                self.usage["prompt_tokens"] += resp.usage.prompt_tokens
                self.usage["completion_tokens"] += resp.usage.completion_tokens
        return resp.choices[0].message.content or "{}"
