# The chat brain: RunPod's stock vLLM worker with the chatter's settings baked in as defaults.
# Every value can still be changed in the endpoint's environment variables.
# v2.29.0 was on GitHub but not on Docker Hub when this was set up (Oct 2026); check before bumping.
FROM runpod/worker-v1-vllm:v2.28.0

ENV MODEL_NAME=shawnw3i/Huihui-Qwen3.6-27B-abliterated-AWQ-MTP \
    MAX_MODEL_LEN=32768 \
    GPU_MEMORY_UTILIZATION=0.92 \
    ENABLE_AUTO_TOOL_CHOICE=true \
    TOOL_CALL_PARSER=qwen3_coder \
    REASONING_PARSER=qwen3 \
    ENABLE_PREFIX_CACHING=true \
    MAX_NUM_SEQS=16 \
    OPENAI_SERVED_MODEL_NAME_OVERRIDE=chatter
