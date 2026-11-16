"""
Reliability harness: runs labelled requests through the full assistant pipeline
and reports pass rate, average confidence, and determinism.

Run:  python -m src.evaluate
Exit code is non-zero if any case fails, so it can gate CI.
"""
import sys

try:
    from src.assistant import recommend_for_request, InputError
except ImportError:
    from assistant import recommend_for_request, InputError

# (request, check, description). A check receives the Result.
CASES = [
    ("I need something to study to", lambda r: r.recommendations[0][0]["mood"] in ("focused", "chill"), "study -> focused/chill on top"),
    ("pump me up for the gym", lambda r: r.recommendations[0][0]["energy"] >= 0.8, "gym -> energy >= 0.8"),
    ("sad rainy day music", lambda r: r.recommendations[0][0]["energy"] <= 0.5, "sad -> low energy"),
    ("late night drive with neon synthwave", lambda r: r.recommendations[0][0]["genre"] == "synthwave", "synthwave named -> synthwave #1"),
    ("help me fall asleep", lambda r: r.recommendations[0][0]["acousticness"] >= 0.7, "sleep -> acoustic"),
    ("let's party and dance", lambda r: r.recommendations[0][0]["energy"] >= 0.8, "party -> high energy"),
    ("gibberish xyzzy", lambda r: r.warnings and r.confidence == 0.0, "unknown -> warning, zero confidence"),
]
REJECTED = ["", "   ", "x" * 1000, None, 42]


def main() -> int:
    passed = 0
    confs = []
    for query, check, desc in CASES:
        try:
            res = recommend_for_request(query)
            ok = bool(check(res))
            # determinism: same input, same ranking
            ok = ok and [s["id"] for s, _, _ in res.recommendations] == \
                [s["id"] for s, _, _ in recommend_for_request(query).recommendations]
            confs.append(res.confidence)
        except Exception as e:  # a crash is a failed case, not a crashed harness
            ok, desc = False, f"{desc} (raised {e!r})"
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {query[:40]!r:44} {desc}")
    for bad in REJECTED:
        try:
            recommend_for_request(bad)
            ok = False
        except InputError:
            ok = True
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] guardrail rejects {str(bad)[:20]!r}")
    total = len(CASES) + len(REJECTED)
    print(f"\n{passed}/{total} passed; mean confidence {sum(confs)/max(len(confs),1):.0%}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
