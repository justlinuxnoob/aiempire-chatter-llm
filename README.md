# aiempire-chatter-llm

The "brain" of the AI chatter: an uncensored LLM on RunPod Serverless, with an
OpenAI-compatible API and tool calling. The chatter app (`aiempire-chatter`, a
Cloudflare Worker) sends it the conversation and gets back either a message or
a tool call (reply, list_catalog, send_ppv, generate_image, get_fan_profile).

It scales to zero: you pay only while a worker is running. The first message
after a quiet spell waits for a cold start (worker boots and loads the model).

## What runs

| | |
|---|---|
| Model | [`shawnw3i/Huihui-Qwen3.6-27B-abliterated-AWQ-MTP`](https://huggingface.co/shawnw3i/Huihui-Qwen3.6-27B-abliterated-AWQ-MTP): Qwen3.6-27B, uncensored ("abliterated"), 4-bit AWQ, 19.5 GB |
| Licence | Apache 2.0 (base model [Qwen/Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B) too): commercial use OK |
| Image | `runpod/worker-v1-vllm:v2.28.0` (vLLM 0.30.0), RunPod's stock worker. No custom Docker image |
| GPU | 48 GB: L40S → RTX 6000 Ada → L40 → A6000 → A40 |
| Scaling | 0 always-on workers, max 1, idle timeout 120 s, FlashBoot on |

All model settings are in [`endpoint.env`](endpoint.env). The worker turns each
one into a `vllm serve` flag (`TOOL_CALL_PARSER=qwen3_coder` → `--tool-call-parser qwen3_coder`).

Because the model is uncensored, it never refuses anything by itself. Every
safety rule (age checks, image-prompt blocklist, "are you real?") lives in the
app's code, not in the model.

## Deploy it (for members)

RunPod → **Serverless → New Endpoint → Import from Docker Registry** →

```
ghcr.io/justlinuxnoob/aiempire-chatter-llm:v2.28.0
```

That image is RunPod's stock vLLM worker with every setting below already built in, so
there are **no environment variables to fill in**. Endpoint settings: **48 GB GPU** (L40S,
RTX 6000 Ada, L40, A6000, A40), **active workers 0**, **max workers 1**, **idle timeout 120 s**,
**FlashBoot on**, **container disk 60 GB**, CUDA 13.0 or newer. Copy the endpoint ID into the
chatter's `/setup`.

<details><summary>Same thing by hand (stock image + environment variables)</summary>

Docker image `runpod/worker-v1-vllm:v2.28.0` with:

| Variable | Value |
|---|---|
| `MODEL_NAME` | `shawnw3i/Huihui-Qwen3.6-27B-abliterated-AWQ-MTP` |
| `MAX_MODEL_LEN` | `32768` |
| `GPU_MEMORY_UTILIZATION` | `0.92` |
| `ENABLE_AUTO_TOOL_CHOICE` | `true` |
| `TOOL_CALL_PARSER` | `qwen3_coder` |
| `REASONING_PARSER` | `qwen3` |
| `ENABLE_PREFIX_CACHING` | `true` |
| `MAX_NUM_SEQS` | `16` |
| `OPENAI_SERVED_MODEL_NAME_OVERRIDE` | `chatter` |

</details>

The ready image is published by `.github/workflows/image.yml` (`crane mutate`: the stock
worker + the `ENV` lines of the `Dockerfile`, nothing rebuilt) on every change to the Dockerfile.

New to RunPod? [Sign up here](https://runpod.io?ref=9s65jq8z).

## Listing on RunPod Hub

The repo has what RunPod Hub needs: `Dockerfile` (stock vLLM worker + these settings as
defaults), `handler.py` (placeholder: the stock worker's own handler runs), `.runpod/hub.json`
and `.runpod/tests.json`. The repo must be public, then create a GitHub release: the Hub
builds and lists it, usually within an hour. Members then deploy it with one click; no
settings to fill in.

The three endpoints of a member's chatter:

| Endpoint | Repo | Used for |
|---|---|---|
| Chat brain | this repo | every reply, catalog descriptions |
| SFW images | justlinuxnoob/ai-empire-telegram-bot | free teasers she takes on demand |
| NSFW images | justlinuxnoob/krea2-nsfw-serverless | paid (locked) photos she takes on demand |

The chatter calls the image endpoints directly (no Telegram token in the job, so the photo
comes back as base64).

## Setup (your own account, via the API)

1. Put your RunPod API key in `.env` (RunPod console → Settings → API Keys).
   `.env` is never committed.
2. `python3 scripts/create_endpoint.py`: shows what will be created.
3. `python3 scripts/create_endpoint.py --yes`: creates it and saves the endpoint ID to `.env`.
4. `python3 tests/run_all.py`: runs the tests (this is when it starts costing money).

## Everyday commands

| Command | What it does |
|---|---|
| `python3 scripts/status.py` | Are workers running? Jobs waiting? |
| `python3 tests/run_all.py` | All tests, 3× each, with a summary |
| `python3 tests/test_tools.py` | Just the tool-calling test, once |
| `python3 scripts/create_endpoint.py --update` | Push changes to `endpoint.env` to RunPod |

## Calling it

Background job (what the Cloudflare Worker uses, safe for long cold starts):

```
POST https://api.runpod.ai/v2/<ENDPOINT_ID>/run
{"input": {"openai_route": "/v1/chat/completions",
           "openai_input": {"model": "chatter", "messages": [...], "tools": [...],
                            "chat_template_kwargs": {"enable_thinking": false}}}}
→ {"id": "<job id>"}; then poll GET /v2/<ENDPOINT_ID>/status/<job id>
```

Direct (fine when the endpoint is warm):

```
POST https://api.runpod.ai/v2/<ENDPOINT_ID>/openai/v1/chat/completions
```

Both use `Authorization: Bearer <RUNPOD_API_KEY>`. Always send
`"chat_template_kwargs": {"enable_thinking": false}`, otherwise Qwen "thinks"
before every reply (slower and more expensive).

## Test results (7 Oct 2026, endpoint `anupss918yyguy`)

| Test | Result | Time |
|---|---|---|
| Background job (`/run`) | 3/3 | cold start 305 s, then 3.5–4 s |
| Hello (OpenAI route) | 3/3 | 1.1–1.3 s |
| Tools (profile → catalog → send_ppv) | 3/3, 0 broken tool calls | 6–8 s per full sale |
| Vision (describe a photo) | 3/3 | 1.4–1.7 s |

Ready image `ghcr.io/justlinuxnoob/aiempire-chatter-llm:v2.28.0` with no settings (11 Oct 2026,
fresh endpoint): cold start 274 s, then 12/12 checks passed (hello 1.2–1.3 s, tools 6–8 s, 0 broken
tool calls, vision 1.5–1.7 s).

Notes for the app (step 2):
- In 1 of 9 tool turns she answered in plain text instead of calling a tool.
  The app should send `tool_choice: "required"` (or treat plain text as a reply).
- Unprompted she said "I'm even cuter in real life", so the persona prompt
  must cover the honesty rule; the model won't do it by default.
- Vision works, so step 4 can describe vault images with this same endpoint.

## Switching model

Edit `MODEL_NAME` (and `TOOL_CALL_PARSER` if the family changes) in
`endpoint.env`, run `scripts/create_endpoint.py --update`, then the tests.
Fallbacks from the shortlist: Gemma 4 26B-A4B uncensored (fastest/cheapest),
Mistral Small 3.2 24B abliterated (`TOOL_CALL_PARSER=mistral`, best roleplay prose).

## Upgrading the worker image

Check that the new tag exists on Docker Hub (`runpod/worker-v1-vllm`) before
changing `IMAGE` in `scripts/create_endpoint.py`: GitHub releases sometimes
appear before the image does.

