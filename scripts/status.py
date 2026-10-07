"""Show whether the endpoint has workers running and jobs waiting.

    python3 scripts/status.py
"""

import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import JOB_API, endpoint_id, headers  # noqa: E402

resp = requests.get(f"{JOB_API}/{endpoint_id()}/health", headers=headers(), timeout=60)
print(json.dumps(resp.json(), indent=2))
