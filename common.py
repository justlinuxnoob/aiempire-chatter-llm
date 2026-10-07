"""Shared helpers: read .env / endpoint.env and talk to the RunPod endpoint.

The API key is only ever read from .env and sent in the Authorization header.
Nothing here prints it.
"""

import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
ENDPOINT_ENV_FILE = ROOT / "endpoint.env"

REST_API = "https://rest.runpod.io/v1"
JOB_API = "https://api.runpod.ai/v2"

# Qwen3.6 "thinks" before answering by default. For chat replies we turn that
# off: faster, cheaper, and the fan never sees it anyway.
NO_THINKING = {"chat_template_kwargs": {"enable_thinking": False}}
# Qwen's recommended sampling for non-thinking mode.
SAMPLING = {"temperature": 0.7, "top_p": 0.8, "top_k": 20}


def read_env_file(path: Path) -> dict:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def set_env_value(key: str, value: str) -> None:
    """Write KEY=value into .env, keeping every other line as it is."""
    lines = ENV_FILE.read_text().splitlines() if ENV_FILE.exists() else []
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n")


def fail(message: str) -> None:
    print(f"\n✗ {message}")
    sys.exit(1)


def api_key() -> str:
    key = read_env_file(ENV_FILE).get("RUNPOD_API_KEY", "")
    if not key:
        fail(f"No RunPod API key yet. Open {ENV_FILE} and paste it after RUNPOD_API_KEY=")
    return key


def endpoint_id() -> str:
    eid = read_env_file(ENV_FILE).get("RUNPOD_ENDPOINT_ID", "")
    if not eid:
        fail("No endpoint yet. Run: python3 scripts/create_endpoint.py")
    return eid


def headers() -> dict:
    return {"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"}


def chat_openai(body: dict, timeout: int = 900) -> tuple[dict, float]:
    """Synchronous call through RunPod's OpenAI-compatible route."""
    url = f"{JOB_API}/{endpoint_id()}/openai/v1/chat/completions"
    start = time.time()
    resp = requests.post(url, headers=headers(), json={"model": "chatter", **body}, timeout=timeout)
    seconds = time.time() - start
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:500]}")
    return resp.json(), seconds


def chat_async(body: dict, max_wait: int = 1800, quiet: bool = False) -> tuple[dict, dict]:
    """Submit a job with /run, then poll /status until it finishes.

    This is the path the Cloudflare Worker will use: a cold start can take
    minutes, longer than one web request should wait.
    Returns (chat completion, timing info).
    """
    eid = endpoint_id()
    job = {"input": {"openai_route": "/v1/chat/completions", "openai_input": {"model": "chatter", **body}}}
    start = time.time()
    resp = requests.post(f"{JOB_API}/{eid}/run", headers=headers(), json=job, timeout=60)
    resp.raise_for_status()
    job_id = resp.json()["id"]

    last_status = None
    while time.time() - start < max_wait:
        status = requests.get(f"{JOB_API}/{eid}/status/{job_id}", headers=headers(), timeout=60).json()
        state = status.get("status")
        if state != last_status and not quiet:
            print(f"    [{time.time() - start:6.0f}s] {state}")
            last_status = state
        if state == "COMPLETED":
            output = status.get("output")
            # The worker yields one item; RunPod wraps generator output in a list.
            if isinstance(output, list):
                output = output[0] if output else {}
            if isinstance(output, dict) and "error" in output:
                raise RuntimeError(f"Worker error: {output['error']}")
            timing = {
                "total_s": time.time() - start,
                "queue_s": status.get("delayTime", 0) / 1000,
                "run_s": status.get("executionTime", 0) / 1000,
            }
            return output, timing
        if state in ("FAILED", "CANCELLED", "TIMED_OUT"):
            raise RuntimeError(f"Job {state}: {str(status)[:500]}")
        time.sleep(3)

    requests.post(f"{JOB_API}/{eid}/cancel/{job_id}", headers=headers(), timeout=60)
    raise RuntimeError(f"Gave up after {max_wait}s (job cancelled)")
