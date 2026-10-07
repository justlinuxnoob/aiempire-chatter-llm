"""Test c — background job (/run + /status), the way the Cloudflare Worker will call it."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import NO_THINKING, SAMPLING, chat_async  # noqa: E402


def run() -> dict:
    body = {
        "messages": [
            {"role": "system", "content": "You are a friendly, flirty influencer. Reply in one short text message."},
            {"role": "user", "content": "hey, just subscribed 👋"},
        ],
        "max_tokens": 80,
        **SAMPLING,
        **NO_THINKING,
    }
    completion, timing = chat_async(body)
    text = completion["choices"][0]["message"].get("content") or ""
    tokens = completion.get("usage", {}).get("completion_tokens", 0)
    return {
        "passed": bool(text.strip()) and "<think>" not in text,
        "seconds": timing["total_s"],
        "queue_s": timing["queue_s"],
        "run_s": timing["run_s"],
        "tokens_per_s": tokens / timing["run_s"] if timing["run_s"] else None,
        "sample": text.strip(),
    }


if __name__ == "__main__":
    print(run())
