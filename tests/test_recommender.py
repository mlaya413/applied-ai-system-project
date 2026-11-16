from src.recommender import Song, UserProfile, Recommender

def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


# ---- Locked-in findings from the evaluation (see model_card.md) ----
import pytest
from src.recommender import (
    score_song, recommend_songs, load_songs, MAX_SCORE,
    MOOD_POINTS, GENRE_POINTS, ENERGY_POINTS,
)


def song(**kw):
    base = dict(id=1, title="A", artist="X", genre="pop", mood="happy",
                energy=0.5, tempo_bpm=100, valence=0.5, danceability=0.5, acousticness=0.5)
    base.update(kw)
    return base


PREFS = dict(favorite_genre="pop", favorite_mood="happy", target_energy=0.5,
             target_valence=0.5, likes_acoustic=True)


def test_max_score_is_sum_of_weights_and_never_exceeded():
    score, _ = score_song(PREFS, song(acousticness=0.8))
    assert score == pytest.approx(MAX_SCORE)
    for e in (0.0, 0.3, 1.0):
        assert score_song(PREFS, song(energy=e))[0] <= MAX_SCORE + 1e-9


def test_label_bonuses_can_outweigh_energy_fit():
    # Mood+genre match with the worst energy beats a perfect-energy non-match.
    label_match = song(title="Match", energy=1.0)
    energy_match = song(title="Fit", genre="jazz", mood="sad", energy=0.5)
    assert score_song(PREFS, label_match)[0] > score_song(PREFS, energy_match)[0]


def test_unknown_genre_falls_back_to_other_features():
    prefs = {**PREFS, "favorite_genre": "polka"}
    ranked = recommend_songs(prefs, [song(title="B", mood="sad"), song(title="A")], k=2)
    assert ranked[0][0]["title"] == "A"  # mood/energy still decide
    assert all("genre match" not in r[2] for r in ranked)


def test_ties_break_alphabetically_by_title():
    ranked = recommend_songs(PREFS, [song(title="Zed"), song(title="Alpha")], k=2)
    assert [r[0]["title"] for r in ranked] == ["Alpha", "Zed"]


def test_explanation_uses_max_score_not_hardcoded_ten():
    rec = make_small_recommender()
    user = UserProfile("pop", "happy", 0.8, False, 0.5)
    assert f"/{MAX_SCORE:.0f}" in rec.explain_recommendation(user, rec.songs[0])


# ---- Defensive handling: fail loudly, or say what was assumed ----
def test_missing_pref_is_reported_not_silently_skipped():
    prefs = {k: v for k, v in PREFS.items() if k != "target_energy"}
    _, reasons = score_song(prefs, song())
    assert any("target_energy not given" in r for r in reasons)


def test_empty_or_out_of_range_prefs_raise():
    with pytest.raises(ValueError):
        score_song({}, song())
    with pytest.raises(ValueError):
        score_song({**PREFS, "target_energy": 1.7}, song())
    with pytest.raises(ValueError):
        UserProfile("pop", "happy", -0.1, False)


def test_default_valence_is_flagged_in_explanation():
    rec = make_small_recommender()
    user = UserProfile("pop", "happy", 0.8, False)  # no valence given
    assert user.valence_assumed
    assert "assumed" in rec.explain_recommendation(user, rec.songs[0])


def test_load_songs_fails_loudly(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_songs(str(tmp_path / "nope.csv"))
    header = "id,title,artist,genre,mood,energy,tempo_bpm,valence,danceability,acousticness\n"
    bad = tmp_path / "bad.csv"
    bad.write_text(header + "1,T,A,pop,happy,abc,100,0.5,0.5,0.5\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        load_songs(str(bad))
    rng = tmp_path / "range.csv"
    rng.write_text(header + "1,T,A,pop,happy,1.5,100,0.5,0.5,0.5\n", encoding="utf-8")
    with pytest.raises(ValueError, match="outside"):
        load_songs(str(rng))
    cols = tmp_path / "cols.csv"
    cols.write_text("id,title\n1,T\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        load_songs(str(cols))
    assert len(load_songs("data/songs.csv")) > 0
