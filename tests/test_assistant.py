import pytest
from src.assistant import (InputError, validate_query, retrieve, build_profile,
                           load_knowledge_base, recommend_for_request)

KB = load_knowledge_base()


def test_rejects_bad_input():
    for bad in ("", "  ", None, 5, "x" * 500):
        with pytest.raises(InputError):
            validate_query(bad)


def test_retrieval_whole_word_only():
    ids = [e["doc"]["id"] for e in retrieve("I like running", KB)]
    assert "activity-workout" in ids
    assert "genre-rock" not in ids  # no substring false positives


def test_retrieved_docs_change_profile():
    gym = build_profile(retrieve("gym workout", KB))
    sleep = build_profile(retrieve("help me sleep", KB))
    assert gym["target_energy"] > 0.8 > 0.3 > sleep["target_energy"]


def test_retrieval_changes_recommendations():
    gym = recommend_for_request("gym workout").recommendations[0][0]
    sleep = recommend_for_request("sleep").recommendations[0][0]
    assert gym["id"] != sleep["id"]
    assert gym["energy"] > sleep["energy"]


def test_no_match_falls_back_safely():
    res = recommend_for_request("qwertyuiop")
    assert res.warnings and res.confidence == 0.0 and res.recommendations
