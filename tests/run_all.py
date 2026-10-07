"""Run every test 3 times and print a plain-language summary.

    python3 tests/run_all.py

The background-job test goes first: if the endpoint is asleep, that call
absorbs the cold start (worker boots, downloads the model, loads it), and the
rest run warm. Full results are saved to results/ (not committed).
"""

import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import test_async  # noqa: E402
import test_hello  # noqa: E402
import test_tools  # noqa: E402
import test_vision  # noqa: E402
from common import ROOT  # noqa: E402

TESTS = [
    ("c. background job (/run)", test_async),
    ("a. hello (OpenAI route)", test_hello),
    ("b. tools", test_tools),
    ("d. vision", test_vision),
]
RUNS = 3


def main() -> None:
    all_results = {}
    for label, module in TESTS:
        print(f"\n=== {label} ===")
        all_results[label] = []
        for i in range(1, RUNS + 1):
            print(f"  run {i}/{RUNS}…")
            try:
                result = module.run()
            except Exception as e:  # keep going so we see every test
                result = {"passed": False, "seconds": 0, "crash": f"{type(e).__name__}: {e}"}
                traceback.print_exc()
            all_results[label].append(result)
            mark = "✓" if result["passed"] else "✗"
            extra = ""
            if "queue_s" in result:
                extra = f" (waiting for a worker {result['queue_s']:.0f}s, working {result['run_s']:.1f}s)"
            print(f"  {mark} {result['seconds']:.1f}s{extra}")
            for line in result.get("steps", []):
                print(f"      → {line}")
            if result.get("sample"):
                print(f"      “{result['sample'][:160]}”")
            if result.get("crash"):
                print(f"      crash: {result['crash'][:300]}")

    print("\n================ SUMMARY ================")
    for label, results in all_results.items():
        passed = sum(r["passed"] for r in results)
        speeds = [r["tokens_per_s"] for r in results if r.get("tokens_per_s")]
        speed = f", ~{sum(speeds) / len(speeds):.0f} tokens/s" if speeds else ""
        times = ", ".join(f"{r['seconds']:.1f}s" for r in results)
        print(f"{label:28} {passed}/{len(results)} passed  [{times}]{speed}")
        if label == "b. tools":
            broken = sum(len(r.get("errors", [])) for r in results)
            chatty = sum(r.get("plain_text_turns", 0) for r in results)
            print(f"{'':28} broken tool calls: {broken}, turns without a tool: {chatty}")

    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    path = out / f"run-{time.strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False))
    print(f"\nFull details: {path}")


if __name__ == "__main__":
    main()
