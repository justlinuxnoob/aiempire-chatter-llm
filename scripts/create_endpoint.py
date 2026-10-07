"""Create (or update) the RunPod serverless endpoint for the chatter LLM.

    python3 scripts/create_endpoint.py           # show the plan, change nothing
    python3 scripts/create_endpoint.py --yes     # create template + endpoint
    python3 scripts/create_endpoint.py --update  # push endpoint.env changes

Creating an endpoint costs nothing by itself: it has 0 always-on workers, so
you only pay while a request is being handled (plus the idle timeout).
"""

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import ENDPOINT_ENV_FILE, ENV_FILE, REST_API, fail, headers, read_env_file, set_env_value  # noqa: E402

NAME = "aiempire-chatter-llm"
# v2.29.0 is on GitHub but was not on Docker Hub when this was set up (Oct 2026).
IMAGE = "runpod/worker-v1-vllm:v2.28.0"

TEMPLATE = {
    "name": f"{NAME} ({IMAGE.split(':')[1]})",
    "imageName": IMAGE,
    "isServerless": True,
    # Image ~9 GB + model 19.5 GB + vLLM compile cache.
    "containerDiskInGb": 60,
    "volumeInGb": 0,
    "ports": [],
}

ENDPOINT = {
    "name": NAME,
    "computeType": "GPU",
    # All 48 GB cards, in order of preference.
    "gpuTypeIds": [
        "NVIDIA L40S",
        "NVIDIA RTX 6000 Ada Generation",
        "NVIDIA L40",
        "NVIDIA RTX A6000",
        "NVIDIA A40",
    ],
    "gpuCount": 1,
    "workersMin": 0,  # scale to zero: no always-on worker
    "workersMax": 1,
    "idleTimeout": 120,  # stay warm 2 min after a reply, for the next fan message
    "flashboot": True,
    "executionTimeoutMs": 600_000,
    # The vLLM 0.30 image is built on CUDA 13.0; older host drivers can't run it.
    "minCudaVersion": "13.0",
}


def show_plan(env: dict) -> None:
    print("Template (what the worker runs):")
    print(f"  image:          {IMAGE}")
    print(f"  container disk: {TEMPLATE['containerDiskInGb']} GB")
    print("  settings:")
    for key, value in env.items():
        print(f"    {key}={value}")
    print("\nEndpoint (how it scales):")
    print(f"  GPUs (in order): {', '.join(g.replace('NVIDIA ', '') for g in ENDPOINT['gpuTypeIds'])}")
    print(f"  workers:         min {ENDPOINT['workersMin']} (scale to zero), max {ENDPOINT['workersMax']}")
    print(f"  idle timeout:    {ENDPOINT['idleTimeout']} s")
    print(f"  FlashBoot:       {'on' if ENDPOINT['flashboot'] else 'off'}")
    print(f"  job time limit:  {ENDPOINT['executionTimeoutMs'] // 60000} min")
    print(f"  min CUDA:        {ENDPOINT['minCudaVersion']}")


def check(resp: requests.Response, what: str) -> dict:
    if resp.status_code >= 400:
        fail(f"RunPod refused to {what}: HTTP {resp.status_code} {resp.text[:500]}")
    return resp.json()


def main() -> None:
    env = read_env_file(ENDPOINT_ENV_FILE)
    local = read_env_file(ENV_FILE)
    args = sys.argv[1:]

    if "--update" in args:
        template_id = local.get("RUNPOD_TEMPLATE_ID")
        if not template_id:
            fail("No RUNPOD_TEMPLATE_ID in .env, so there is nothing to update yet.")
        show_plan(env)
        check(
            requests.patch(f"{REST_API}/templates/{template_id}", headers=headers(), json={**TEMPLATE, "env": env}, timeout=60),
            "update the template",
        )
        print("\n✓ Updated. New workers pick up the new settings; a running worker keeps the old ones until it scales down.")
        return

    if local.get("RUNPOD_ENDPOINT_ID"):
        fail(f"An endpoint already exists ({local['RUNPOD_ENDPOINT_ID']}). Use --update to change its settings.")

    show_plan(env)
    if "--yes" not in args:
        print("\nNothing created. Run again with --yes to create it.")
        return

    headers()  # stop early with a clear message if the key is missing
    print("\nCreating template…")
    template = check(
        requests.post(f"{REST_API}/templates", headers=headers(), json={**TEMPLATE, "env": env}, timeout=60),
        "create the template",
    )
    set_env_value("RUNPOD_TEMPLATE_ID", template["id"])
    print(f"  ✓ template {template['id']}")

    print("Creating endpoint…")
    endpoint = check(
        requests.post(f"{REST_API}/endpoints", headers=headers(), json={**ENDPOINT, "templateId": template["id"]}, timeout=60),
        "create the endpoint",
    )
    set_env_value("RUNPOD_ENDPOINT_ID", endpoint["id"])
    print(f"  ✓ endpoint {endpoint['id']} (saved to .env)")
    print(f"\nConsole: https://console.runpod.io/serverless/user/endpoint/{endpoint['id']}")


if __name__ == "__main__":
    main()
