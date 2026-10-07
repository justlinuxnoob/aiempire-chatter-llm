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

## Setup

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

## Switching model

Edit `MODEL_NAME` (and `TOOL_CALL_PARSER` if the family changes) in
`endpoint.env`, run `scripts/create_endpoint.py --update`, then the tests.
Fallbacks from the shortlist: Gemma 4 26B-A4B uncensored (fastest/cheapest),
Mistral Small 3.2 24B abliterated (`TOOL_CALL_PARSER=mistral`, best roleplay prose).

## Upgrading the worker image

Check that the new tag exists on Docker Hub (`runpod/worker-v1-vllm`) before
changing `IMAGE` in `scripts/create_endpoint.py`: GitHub releases sometimes
appear before the image does.

## For Premium members

New to RunPod? Sign up with this referral link: https://runpod.io?ref=9s65jq8z
