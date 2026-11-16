"""
Retrieval-augmented music assistant.

Pipeline (each step changes what the next one does):
  1. validate   - guardrails on the raw text request
  2. retrieve   - rank knowledge-base docs (data/knowledge_base.json) against the request
  3. build      - the retrieved docs' hints BECOME the user profile (genre, mood, energy, ...)
  4. recommend  - the existing scoring engine ranks songs for that profile
  5. self-check - flag weak matches and low-confidence retrievals
Without retrieval the request has no numeric meaning, so there is nothing to score.

Run:  python -m src.assistant "something to study to on a rainy day"
      python -m src.assistant            (interactive)
"""
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

try:
    from src.recommender import load_songs, recommend_songs, MAX_SCORE
except ImportError:
    from recommender import load_songs, recommend_songs, MAX_SCORE

ROOT = Path(__file__).resolve().parent.parent
KB_PATH = ROOT / "data" / "knowledge_base.json"
SONGS_PATH = ROOT / "data" / "songs.csv"
LOG_PATH = ROOT / "logs" / "assistant.log"

MAX_QUERY_CHARS = 300
TOP_DOCS = 3
WEAK_MATCH_RATIO = 0.6   # top song below 60% of max score -> warn
NEUTRAL_PROFILE = {
    "favorite_genre": None, "favorite_mood": None,
    "target_energy": 0.5, "target_valence": 0.5, "likes_acoustic": False,
}

log = logging.getLogger("assistant")


def setup_logging() -> None:
    """Log everything to logs/assistant.log; warnings are also shown in the CLI output."""
    if log.handlers:
        return
    log.setLevel(logging.INFO)
    try:
        LOG_PATH.parent.mkdir(exist_ok=True)
        fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(fh)
    except OSError:  # read-only disk etc.: logging must never break the app
        pass


class InputError(ValueError):
    """The user's request was rejected by a guardrail."""


@dataclass
class Result:
    query: str
    profile: Dict
    evidence: List[Dict] = field(default_factory=list)   # retrieved docs + score
    recommendations: list = field(default_factory=list)  # (song, score, explanation)
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)


# ---------- 1. guardrails ----------
def validate_query(query) -> str:
    if not isinstance(query, str) or not query.strip():
        raise InputError("Please describe what you want to listen to.")
    query = " ".join(query.split())
    if len(query) > MAX_QUERY_CHARS:
        raise InputError(f"Request too long ({len(query)} chars; max {MAX_QUERY_CHARS}).")
    return query


# ---------- 2. retrieval ----------
def load_knowledge_base(path: Path = KB_PATH) -> List[Dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _norm(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9&]+", " ", text.lower()).strip() + " "


def retrieve(query: str, kb: List[Dict], k: int = TOP_DOCS) -> List[Dict]:
    """Rank docs by keyword hits (whole word/phrase; multi-word phrases count more)."""
    q = _norm(query)
    scored = []
    for doc in kb:
        score = 0.0
        for kw in doc["keywords"]:
            nk = _norm(kw)
            if nk in q:
                score += len(nk.split())  # phrase > single word
        if score > 0:
            scored.append({"doc": doc, "score": score})
    scored.sort(key=lambda d: (-d["score"], d["doc"]["id"]))
    return scored[:k]


# ---------- 3. build profile from retrieved evidence ----------
def build_profile(evidence: List[Dict]) -> Dict:
    profile = dict(NEUTRAL_PROFILE)
    if not evidence:
        return profile
    hints = [(e["doc"]["hints"], e["score"]) for e in evidence]
    for key, pkey in (("genre", "favorite_genre"), ("mood", "favorite_mood")):
        for h, _ in hints:  # evidence is ranked, so first hit wins
            if key in h:
                profile[pkey] = h[key]
                break
    for key, pkey in (("energy", "target_energy"), ("valence", "target_valence")):
        vals = [(h[key], w) for h, w in hints if key in h]
        if vals:  # score-weighted mean
            profile[pkey] = sum(v * w for v, w in vals) / sum(w for _, w in vals)
    acoustic = [(h["likes_acoustic"], w) for h, w in hints if "likes_acoustic" in h]
    if acoustic:
        profile["likes_acoustic"] = (
            sum(w for v, w in acoustic if v) >= sum(w for v, w in acoustic if not v)
        )
    for key in ("target_energy", "target_valence"):
        profile[key] = min(1.0, max(0.0, profile[key]))
    return profile


# ---------- main entry ----------
def recommend_for_request(query, songs: Optional[List[Dict]] = None,
                          kb: Optional[List[Dict]] = None, k: int = 5) -> Result:
    setup_logging()
    query = validate_query(query)
    kb = kb if kb is not None else load_knowledge_base()
    songs = songs if songs is not None else load_songs(str(SONGS_PATH))

    evidence = retrieve(query, kb)
    profile = build_profile(evidence)
    res = Result(query=query, profile=profile, evidence=evidence)
    log.info("query=%r retrieved=%s profile=%s", query, [e["doc"]["id"] for e in evidence], profile)

    if not evidence:
        res.warnings.append(
            "No knowledge-base match; using a neutral profile. Try naming a genre, mood or activity."
        )
    res.confidence = min(1.0, sum(e["score"] for e in evidence) / 3.0)

    res.recommendations = recommend_songs(profile, songs, k=k)

    # 5. self-check
    if res.recommendations:
        top = res.recommendations[0][1]
        res.confidence *= top / MAX_SCORE
        if top < WEAK_MATCH_RATIO * MAX_SCORE:
            res.warnings.append(
                f"Best match scored only {top:.1f}/{MAX_SCORE:.0f}; the catalog may not fit this request."
            )
    for w in res.warnings:
        log.warning("query=%r %s", query, w)
    log.info("top=%s confidence=%.2f", [r[0]["title"] for r in res.recommendations], res.confidence)
    return res


def format_result(res: Result) -> str:
    p = res.profile
    lines = [f'\nRequest: "{res.query}"', "Retrieved context:"]
    lines += [f"  - [{e['doc']['id']}] {e['doc']['text']}" for e in res.evidence] or ["  (none)"]
    lines.append(
        f"Profile built from context: genre={p['favorite_genre']}, mood={p['favorite_mood']}, "
        f"energy={p['target_energy']:.2f}, valence={p['target_valence']:.2f}, acoustic={p['likes_acoustic']}"
    )
    lines.append(f"Confidence: {res.confidence:.0%}")
    lines += [f"WARNING: {w}" for w in res.warnings]
    for i, (song, score, why) in enumerate(res.recommendations, 1):
        lines.append(
            f"#{i} {song['title']} - {song['artist']} [{song['genre']}/{song['mood']}] "
            f"{score:.2f}/{MAX_SCORE:.0f}"
        )
        lines.append(f"     {why}")
    return "\n".join(lines)


def main(argv: List[str]) -> int:
    try:
        if argv:
            print(format_result(recommend_for_request(" ".join(argv))))
        else:
            print("Describe what you want to hear (blank line to quit).")
            while (q := input("> ")).strip():
                try:
                    print(format_result(recommend_for_request(q)))
                except InputError as e:
                    print(f"Input rejected: {e}")
    except InputError as e:
        print(f"Input rejected: {e}")
        return 1
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
        log.error("data error: %s", e)
        print(f"Could not load data files: {e}")
        return 2
    except (EOFError, KeyboardInterrupt):
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
