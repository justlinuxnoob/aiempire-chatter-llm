# AGENTS.md: guide for AI assistants

This repo is the **chat brain** of [aiempire-chatter](https://github.com/justlinuxnoob/aiempire-chatter)
(read that repo's AGENTS.md for the whole system). It has no application code: it's RunPod's
stock vLLM worker (`runpod/worker-v1-vllm`) configured by environment variables.

- **Model:** `shawnw3i/Huihui-Qwen3.6-27B-abliterated-AWQ-MTP` (Qwen3.6-27B, abliterated, AWQ 4-bit, 19.5 GB, Apache-2.0).
- **Settings:** `endpoint.env` (source of truth for scripts) = the `ENV` block in `Dockerfile`. Keep them in sync.
- **Ready image:** `ghcr.io/justlinuxnoob/aiempire-chatter-llm:{latest,v2.28.0}`, built by `.github/workflows/image.yml` with `crane mutate` (adds the Dockerfile's `ENV` to the stock image's config; no layers rebuilt).
- **Calling it:** RunPod `/run` with `{"input": {"openai_route": "/v1/chat/completions", "openai_input": {...}}}` then `/status`; or `/openai/v1/chat/completions` when warm. Always send `chat_template_kwargs: {"enable_thinking": false}`. Served model name `chatter`. Tool calling: `tool_choice: "required"` works.
- **GPU:** 48 GB; CUDA 13.0+ hosts (vLLM 0.30 image).
- **Scripts:** `scripts/create_endpoint.py` (create/update via RunPod REST, key in `.env`, never printed), `scripts/status.py`, `tests/run_all.py` (hello, tools, background job, vision; 3× each).
- **Upgrading the worker:** check the new `runpod/worker-v1-vllm` tag exists on Docker Hub first (GitHub releases appear earlier), bump `FROM` in the Dockerfile; the workflow republishes the image.
- `.runpod/hub.json` + `tests.json` are for a RunPod Hub listing.
