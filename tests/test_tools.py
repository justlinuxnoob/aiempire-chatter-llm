"""Test b — does the model use the chatter's tools correctly?

A fan asks for "something special". We play the app: when the model calls
get_fan_profile or list_catalog we hand back fake data, and keep going until
it calls send_ppv. PASS = every tool call is valid JSON with the right fields,
and send_ppv uses an ID that really is in the catalog, with a price.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import NO_THINKING, SAMPLING, chat_openai  # noqa: E402

PERSONA = (
    "You are Mia, a 25-year-old AI-generated influencer chatting with a fan on Fanvue. "
    "You are flirty, playful and warm, and you text like a real person: short messages, casual, a few emojis. "
    "Talk to the fan only through the reply and send_ppv tools. "
    "Before selling, check who the fan is with get_fan_profile and what you have with list_catalog. "
    "Only sell items that are in your catalog."
)


def tool(name: str, description: str, properties: dict, required: list) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


TOOLS = [
    tool("reply", "Send a normal chat message to the fan.", {"text": {"type": "string"}}, ["text"]),
    tool("list_catalog", "List your pay-to-view images: ID, description, suggested price in USD.", {}, []),
    tool(
        "send_ppv",
        "Send one or more catalog images locked behind a price, with a short teasing caption.",
        {
            "media_ids": {"type": "array", "items": {"type": "string"}},
            "price": {"type": "number", "description": "Price in USD"},
            "caption": {"type": "string"},
        },
        ["media_ids", "price", "caption"],
    ),
    tool("generate_image", "Create a brand-new photo of yourself from a description.", {"prompt": {"type": "string"}}, ["prompt"]),
    tool("get_fan_profile", "What you know about this fan: name, preferences, purchases, total spent.", {}, []),
]
REQUIRED = {t["function"]["name"]: t["function"]["parameters"]["required"] for t in TOOLS}

CATALOG = [
    {"id": "m_101", "description": "red lace lingerie, mirror selfie in the bedroom", "suggested_price": 12},
    {"id": "m_102", "description": "white bikini on the beach at sunset", "suggested_price": 8},
    {"id": "m_103", "description": "steamy shower photo, wet hair, topless from behind", "suggested_price": 20},
]
FAN = {"name": "Jake", "preferences": [], "purchases": [], "total_spent_usd": 0, "notes": "subscribed 2 days ago"}
FAKE_RESULTS = {
    "get_fan_profile": FAN,
    "list_catalog": CATALOG,
    "reply": {"status": "sent"},
    "generate_image": {"status": "queued"},
}


def check_call(name: str, raw_args: str) -> tuple[dict | None, str | None]:
    if name not in REQUIRED:
        return None, f"unknown tool {name!r}"
    try:
        args = json.loads(raw_args or "{}")
    except json.JSONDecodeError:
        return None, f"{name}: arguments are not valid JSON: {raw_args[:120]}"
    missing = [k for k in REQUIRED[name] if k not in args]
    if missing:
        return None, f"{name}: missing {missing}"
    if name == "send_ppv":
        ids = args["media_ids"]
        if not isinstance(ids, list) or not ids:
            return None, "send_ppv: media_ids is not a list of IDs"
        unknown = [i for i in ids if i not in {c["id"] for c in CATALOG}]
        if unknown:
            return None, f"send_ppv: made-up media IDs {unknown}"
        if not isinstance(args["price"], (int, float)) or args["price"] <= 0:
            return None, f"send_ppv: bad price {args['price']!r}"
    return args, None


def run(max_turns: int = 6) -> dict:
    messages = [
        {"role": "system", "content": PERSONA},
        {"role": "user", "content": "hey babe, can you show me something special? 😏"},
    ]
    steps, errors, plain_text_turns, seconds = [], [], 0, 0.0
    sold = None

    for _ in range(max_turns):
        completion, took = chat_openai(
            {"messages": messages, "tools": TOOLS, "tool_choice": "auto", "max_tokens": 400, **SAMPLING, **NO_THINKING}
        )
        seconds += took
        message = completion["choices"][0]["message"]
        calls = message.get("tool_calls") or []
        if not calls:
            # Talked without a tool. Not fatal, but the app wants tools every time.
            plain_text_turns += 1
            steps.append(f"(plain text) {(message.get('content') or '').strip()[:80]}")
            messages.append({"role": "assistant", "content": message.get("content") or ""})
            messages.append({"role": "user", "content": "so? 👀"})
            continue

        messages.append({"role": "assistant", "content": message.get("content"), "tool_calls": calls})
        for call in calls:
            name = call["function"]["name"]
            args, error = check_call(name, call["function"].get("arguments", ""))
            if error:
                errors.append(error)
                steps.append(f"✗ {error}")
                result = {"error": error}
            else:
                steps.append(f"{name}({json.dumps(args, ensure_ascii=False)})")
                result = FAKE_RESULTS.get(name, {"status": "sent"})
                if name == "send_ppv":
                    sold = args
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})
        if sold:
            break

    return {
        "passed": bool(sold) and not errors,
        "seconds": seconds,
        "steps": steps,
        "errors": errors,
        "plain_text_turns": plain_text_turns,
        "sold": sold,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
