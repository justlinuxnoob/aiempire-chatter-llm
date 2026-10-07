"""Test d — can this endpoint look at a photo?

If yes, step 4 can use it to auto-describe vault images; if not, we need a
separate vision model. The image is sent inline (base64), which is also how
the app will send vault images.
"""

import base64
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import NO_THINKING, chat_openai  # noqa: E402

TEST_IMAGE = "https://picsum.photos/id/237/512/512"  # a black puppy


def run() -> dict:
    image = requests.get(TEST_IMAGE, timeout=60)
    image.raise_for_status()
    data_url = "data:image/jpeg;base64," + base64.b64encode(image.content).decode()
    body = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": "Describe this photo in one sentence."},
                ],
            }
        ],
        "max_tokens": 80,
        "temperature": 0.2,
        **NO_THINKING,
    }
    try:
        completion, seconds = chat_openai(body)
    except RuntimeError as e:
        return {"passed": False, "seconds": 0, "sample": f"Endpoint refused the image: {e}"}
    text = (completion["choices"][0]["message"].get("content") or "").strip()
    return {
        "passed": any(word in text.lower() for word in ("dog", "puppy")),
        "seconds": seconds,
        "sample": text,
    }


if __name__ == "__main__":
    print(run())
