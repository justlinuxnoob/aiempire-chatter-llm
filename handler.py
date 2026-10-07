"""The chat brain has no code of its own.

The Docker image is RunPod's stock vLLM worker (runpod/worker-v1-vllm, see the
Dockerfile), and its own handler serves the jobs: it starts `vllm serve` with the
settings from the environment and proxies OpenAI-style requests to it. This file
only exists because RunPod Hub expects a handler.py in the repo.
"""
