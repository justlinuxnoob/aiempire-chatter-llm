"""Test a — one plain chat message through the OpenAI-compatible route."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import NO_THINKING, SAMPLING, chat_openai  # noqa: E402


def run() -> dict:
    body = {
        "messages": [
            {"role": "system", "content": "You are a friendly, flirty influencer. Reply in one short text message."},
            {"role": "user", "content": "good morning gorgeous ☀️ what are you up to today?"},
        ],
        "max_tokens": 80,
        **SAMPLING,
        **NO_THINKING,
    }
    completion, seconds = chat_openai(body)
    text = completion["choices"][0]["message"].get("content") or ""
    tokens = completion.get("usage", {}).get("completion_tokens", 0)
    return {
        "passed": bool(text.strip()) and "<think>" not in text,
        "seconds": seconds,
        # Includes network time, so a little lower than the GPU's real speed.
        "tokens_per_s": tokens / seconds if seconds else None,
        "sample": text.strip(),
    }


if __name__ == "__main__":
    print(run())
