from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import get_settings


class LLMClient(ABC):
    @abstractmethod
    async def enrich(self, prompt: str, fallback: str) -> str:
        raise NotImplementedError


class MockLLMClient(LLMClient):
    async def enrich(self, prompt: str, fallback: str) -> str:
        _ = prompt
        return fallback


class OpenAILLMClient(LLMClient):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.url = "https://api.openai.com/v1/chat/completions"

    async def enrich(self, prompt: str, fallback: str) -> str:
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 120,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(self.url, json=payload, headers=headers)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"].strip()
                return content or fallback
        except Exception:
            return fallback


def get_llm_client(enable_llm: bool) -> LLMClient:
    settings = get_settings()
    if enable_llm and settings.openai_api_key:
        return OpenAILLMClient(settings.openai_api_key)
    return MockLLMClient()


def _normalize_and_clip(text: str, max_len: int | None = None) -> str:
    normalized = " ".join((text or "").split())
    if not max_len or len(normalized) <= max_len:
        return normalized
    clipped = normalized[:max_len].rstrip()
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped or normalized[:max_len]


async def enrich_passenger_name(client: LLMClient, first_name: str, last_name: str) -> tuple[str, str]:
    prompt = (
        "Return a realistic airline customer name in 'First Last' format. "
        "Keep it concise and ASCII."
    )
    enriched = await client.enrich(prompt, f"{first_name} {last_name}")
    enriched = _normalize_and_clip(enriched, max_len=80)
    parts = enriched.split(" ", 1)
    if len(parts) == 2:
        return (
            _normalize_and_clip(parts[0].strip().title(), max_len=32),
            _normalize_and_clip(parts[1].strip().title(), max_len=32),
        )
    return first_name, last_name


async def enrich_text(
    client: LLMClient, base_text: str, context: dict[str, Any], max_len: int | None = None
) -> str:
    prompt = (
        "Rewrite airline customer communication to sound operationally realistic. "
        f"Context: {context}. Base: {base_text}."
    )
    enriched = await client.enrich(prompt, base_text)
    return _normalize_and_clip(enriched, max_len=max_len)
